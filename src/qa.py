"""QA final automático: duración, sincronía, fotogramas, licencias, metadatos y uso."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from src import almacen, claude_cli, ffmpeg
from src.config import Config

ESQUEMA_VISUAL: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problemas": {"type": "array", "items": {"type": "string"}},
        "aprobado": {"type": "boolean"},
    },
    "required": ["problemas", "aprobado"],
}


class FalloQA(Exception):
    def __init__(self, motivos: list[str], repetir: str) -> None:
        super().__init__("; ".join(motivos))
        self.motivos = motivos
        self.repetir = repetir  # estado al que se retrocede; el pipeline rehace el paso siguiente


def desfase_subtitulos_ms(tiempos: dict[str, Any]) -> float:
    """Desfase máximo entre el fin de cada frase del TTS y el fin del último subtítulo que la cubre."""
    subs = tiempos["subtitulos"]
    peor = 0.0
    for esc in tiempos["escenas"]:
        for f in esc["frases"]:
            cubren = [s for s in subs if f["inicio"] - 1e-3 <= s["inicio"] < f["fin"] + 1e-3]
            if not cubren:
                return float("inf")
            peor = max(
                peor, abs(cubren[-1]["fin"] - f["fin"]) * 1000, abs(cubren[0]["inicio"] - f["inicio"]) * 1000
            )
    return peor


def muestrear_fotogramas(video: Path, n: int, duracion: float, destino: Path) -> list[Path]:
    destino.mkdir(exist_ok=True)
    rutas = []
    for i in range(n):
        t = duracion * (i + 0.5) / n
        r = destino / f"qa_{i:02}.jpg"
        ffmpeg.ejecutar(["-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(r)])
        rutas.append(r)
    return rutas


def chequeo_fotogramas(rutas: list[Path], resolucion: tuple[int, int]) -> list[str]:
    motivos = []
    for r in rutas:
        img = Image.open(r)
        if img.size != tuple(resolucion):
            motivos.append(f"{r.name}: resolución {img.size} ≠ {tuple(resolucion)}")
        if ImageStat.Stat(img.convert("L")).mean[0] < 6:
            motivos.append(f"{r.name}: fotograma en negro")
    return motivos


def revisar(
    slug: str,
    tiempos: dict[str, Any],
    final: Path,
    metadatos: dict[str, Any],
    cfg: Config,
    con: sqlite3.Connection,
    video_id: int,
    revision_visual: bool = True,
    **kw: Any,
) -> dict[str, Any]:
    cal, fmt = cfg.calidad, cfg.formato
    motivos: list[str] = []
    repetir = "AUDIO_OK"  # rehacer montaje
    info = ffmpeg.sondear(final)
    dur = float(info["format"]["duration"])
    if not fmt.duracion_min_s <= dur <= fmt.duracion_max_s:
        motivos.append(f"duración {dur:.0f} s fuera de [{fmt.duracion_min_s}, {fmt.duracion_max_s}]")
        repetir = "INVESTIGADO"  # rehacer guion
    if not any(s.get("codec_type") == "audio" for s in info["streams"]):
        motivos.append("el vídeo final no tiene audio")
    desfase = desfase_subtitulos_ms(tiempos)
    if desfase > cal.max_desfase_subtitulos_ms:
        motivos.append(f"desfase de subtítulos {desfase:.0f} ms > {cal.max_desfase_subtitulos_ms}")
        repetir = "TONO_OK"  # rehacer voz
    fotos = muestrear_fotogramas(final, cal.fotogramas_qa, dur, almacen.media(slug) / "qa")
    motivos += chequeo_fotogramas(fotos, fmt.resolucion)
    permitidas = set(cfg.visuales.get("licencias_permitidas", [])) | {"IA-APACHE-2.0"}
    sin_licencia = [
        r["escena"]
        for r in con.execute("SELECT escena, licencia FROM assets WHERE video_id = ?", (video_id,))
        if r["licencia"] not in permitidas
    ]
    if sin_licencia:
        motivos.append(f"assets sin licencia permitida en escenas {sin_licencia}")
        repetir = "VOZ_OK"  # rehacer visuales
    for campo in ("titulo", "descripcion", "etiquetas"):
        if not metadatos.get(campo):
            motivos.append(f"metadatos incompletos: falta {campo}")
    if "Fuentes:" not in metadatos.get("descripcion", ""):
        motivos.append("la descripción no incluye las fuentes")
    uso = con.execute(
        "SELECT COALESCE(SUM(llamadas),0) AS l, COALESCE(SUM(turnos),0) AS t FROM uso WHERE video_id = ?",
        (video_id,),
    ).fetchone()
    if uso["l"] > cfg.uso.max_llamadas_claude_por_video or uso["t"] > cfg.uso.max_turnos_claude_por_video:
        motivos.append(f"uso de Claude por encima del límite ({uso['l']} llamadas, {uso['t']} turnos)")
    if revision_visual and not motivos:
        rutas = "\n".join(str(p.resolve()) for p in fotos)
        r = claude_cli.llamar(
            "qa",
            "Revisa estos fotogramas (léelos con Read). Marca problemas: fotorrealismo que pueda "
            "confundirse con material real, texto ilegible o marcas de agua, contenido gráfico o gore, "
            f"imágenes anacrónicas evidentes.\n{rutas}",
            ESQUEMA_VISUAL,
            modelo=cfg.modelos["qa"],
            max_turnos=cfg.max_turnos.get("qa", 4) + len(fotos),
            herramientas=("Read",),
            con=con,
            video_id=video_id,
            **kw,
        )
        if not r["aprobado"]:
            motivos += [f"revisión visual: {p}" for p in r["problemas"]] or ["revisión visual no aprobada"]
            repetir = "VOZ_OK"
    resultado = {
        "aprobado": not motivos,
        "motivos": motivos,
        "duracion_s": round(dur, 1),
        "desfase_subtitulos_ms": round(desfase, 1),
        "repetir_desde": None if not motivos else repetir,
    }
    almacen.guardar_json(almacen.qa(slug, "final"), resultado)
    if motivos:
        raise FalloQA(motivos, repetir)
    return resultado
