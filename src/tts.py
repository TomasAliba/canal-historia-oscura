"""Locución: una petición TTS por frase → tiempos exactos para escenas, capítulos y subtítulos.

Proveedores con interfaz común (config voz.proveedor): google (Chirp 3 HD) y simulado (silencio,
para tests y ensayos sin coste). Se pueden añadir kokoro o elevenlabs sin tocar el pipeline.
"""

from __future__ import annotations

import base64
import io
import os
import sqlite3
import wave
from pathlib import Path
from typing import Any, Protocol

from src import almacen, texto
from src.config import Config
from src.db import registrar_uso

FRECUENCIA = 24000
SILENCIO_FRASE_S = 0.25
SILENCIO_PARRAFO_S = 0.7
SILENCIO_CAPITULO_S = 1.2


class Sintetizador(Protocol):
    def sintetizar(self, frase: str) -> bytes:
        """Devuelve WAV PCM 16 bits mono a FRECUENCIA Hz."""
        ...


def wav_silencio(segundos: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(b"\x00\x00" * int(segundos * FRECUENCIA))
    return buf.getvalue()


class SimuladoTTS:
    """Silencio proporcional al texto (≈ 150 palabras/min). Sin red ni coste."""

    def sintetizar(self, frase: str) -> bytes:
        return wav_silencio(max(0.5, len(frase.split()) * 0.4))


class GoogleTTS:
    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def __init__(self, cfg: Config) -> None:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        ruta = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "secrets/gcp-tts.json")
        cred = service_account.Credentials.from_service_account_file(
            ruta, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.sesion = AuthorizedSession(cred)
        self.voz = cfg.voz

    def sintetizar(self, frase: str) -> bytes:
        cuerpo = {
            "input": {"markup": frase},
            "voice": {"languageCode": self.voz.idioma, "name": self.voz.nombre},
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": FRECUENCIA,
                "speakingRate": self.voz.ritmo,
            },
        }
        r = self.sesion.post(self.URL, json=cuerpo, timeout=120)
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"])


def crear(cfg: Config, simulado: bool = False) -> Sintetizador:
    if simulado:
        return SimuladoTTS()
    if cfg.voz.proveedor == "google":
        return GoogleTTS(cfg)
    raise ValueError(f"Proveedor de voz no soportado todavía: {cfg.voz.proveedor}")


def _pcm(datos: bytes) -> bytes:
    with wave.open(io.BytesIO(datos)) as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, FRECUENCIA):
            raise ValueError("Formato de audio inesperado del TTS (se espera mono 16 bits 24 kHz)")
        return w.readframes(w.getnframes())


def _trozos_subtitulo(frase: str, inicio: float, fin: float, max_palabras: int = 12) -> list[tuple]:
    pal = frase.split()
    grupos = [" ".join(pal[i : i + max_palabras]) for i in range(0, len(pal), max_palabras)] or [frase]
    total = sum(len(g) for g in grupos)
    t, out = inicio, []
    for g in grupos:
        d = (fin - inicio) * len(g) / total
        out.append((g, t, t + d))
        t += d
    return out


def _srt_tiempo(s: float) -> str:
    ms = round(s * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    seg, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{seg:02},{ms:03}"


def locutar(
    slug: str,
    g: dict[str, Any],
    cfg: Config,
    sint: Sintetizador,
    con: sqlite3.Connection | None = None,
    video_id: int | None = None,
) -> dict[str, Any]:
    carpeta = almacen.media(slug) / "tts"
    carpeta.mkdir(parents=True, exist_ok=True)
    pcm = bytearray()
    t = 0.0
    escenas, capitulos, subtitulos = [], [], []
    caracteres = 0

    def silencio(s: float) -> None:
        nonlocal t
        pcm.extend(b"\x00\x00" * int(s * FRECUENCIA))
        t += int(s * FRECUENCIA) / FRECUENCIA

    bloques = [(c["titulo"], c["parrafos"]) for c in g["capitulos"]]
    bloques.append(("Cierre", [{"texto": g["cta"], "visual": "", "busqueda": ""}]))
    for ci, (titulo, parrafos) in enumerate(bloques):
        if ci > 0:
            silencio(SILENCIO_CAPITULO_S)
        capitulos.append({"titulo": titulo, "inicio": round(t, 3)})
        for pi, par in enumerate(parrafos):
            if pi > 0:
                silencio(SILENCIO_PARRAFO_S)
            ini_escena = t
            lista_frases = []
            for fi, frase in enumerate(texto.frases(texto.para_locucion(par["texto"]))):
                if fi > 0:
                    silencio(SILENCIO_FRASE_S)
                cache = carpeta / f"{almacen.huella(frase, cfg.voz.nombre, cfg.voz.ritmo)}.wav"
                if not cache.exists():
                    cache.write_bytes(sint.sintetizar(frase))
                    caracteres += len(frase)
                datos = _pcm(cache.read_bytes())
                ini = t
                pcm.extend(datos)
                t += len(datos) / 2 / FRECUENCIA
                legible = texto.limpio(frase)
                lista_frases.append({"texto": legible, "inicio": round(ini, 3), "fin": round(t, 3)})
                subtitulos += _trozos_subtitulo(legible, ini, t)
            escenas.append(
                {
                    "capitulo": ci,
                    "parrafo": pi,
                    "inicio": round(ini_escena, 3),
                    "fin": round(t, 3),
                    "visual": par.get("visual", ""),
                    "busqueda": par.get("busqueda", ""),
                    "frases": lista_frases,
                }
            )

    destino = almacen.media(slug)
    with wave.open(str(destino / "narracion.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(bytes(pcm))
    srt = "\n".join(
        f"{i}\n{_srt_tiempo(a)} --> {_srt_tiempo(b)}\n{txt}\n" for i, (txt, a, b) in enumerate(subtitulos, 1)
    )
    (destino / "subtitulos.srt").write_text(srt, encoding="utf-8")
    tiempos = {
        "duracion": round(t, 3),
        "escenas": escenas,
        "capitulos": capitulos,
        "subtitulos": [{"texto": x, "inicio": round(a, 3), "fin": round(b, 3)} for x, a, b in subtitulos],
    }
    almacen.guardar_json(destino / "tiempos.json", tiempos)
    if con is not None and caracteres:
        registrar_uso(con, video_id, "tts", modelo=cfg.voz.nombre, caracteres_tts=caracteres)
    return tiempos


def duracion_wav(ruta: Path) -> float:
    with wave.open(str(ruta)) as w:
        return w.getnframes() / w.getframerate()
