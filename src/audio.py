"""Audio: narración + música con licencia (ducking bajo la voz) + normalización a -14 LUFS."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src import almacen, ffmpeg
from src.config import Config, raiz


def catalogo_musica(cfg: Config) -> list[dict[str, Any]]:
    """assets/musica/licencias.yaml: lista de {archivo, titulo, autor, licencia, atribucion}."""
    carpeta = raiz() / cfg.audio.get("carpeta_musica", "assets/musica")
    manifiesto = carpeta / "licencias.yaml"
    if not manifiesto.exists():
        return []
    pistas = yaml.safe_load(manifiesto.read_text(encoding="utf-8")) or []
    return [p | {"ruta": str(carpeta / p["archivo"])} for p in pistas if (carpeta / p["archivo"]).exists()]


def elegir_pista(slug: str, pistas: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not pistas:
        return None
    return pistas[int(almacen.huella(slug), 16) % len(pistas)]


def filtro(con_musica: bool, volumen_db: float, ducking: bool) -> str:
    norm = "loudnorm=I=-14:TP=-1.5:LRA=11"
    if not con_musica:
        return f"[0:a]{norm}[a]"
    if ducking:
        return (
            f"[0:a]asplit=2[voz][clave];[1:a]volume={volumen_db}dB[mus];"
            "[mus][clave]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[duck];"
            f"[voz][duck]amix=inputs=2:duration=first:normalize=0,{norm}[a]"
        )
    return f"[1:a]volume={volumen_db}dB[mus];[0:a][mus]amix=inputs=2:duration=first:normalize=0,{norm}[a]"


def mezclar(slug: str, cfg: Config, con: sqlite3.Connection, video_id: int) -> Path:
    carpeta = almacen.media(slug)
    salida = carpeta / "audio.m4a"
    pista = elegir_pista(slug, catalogo_musica(cfg))
    args = ["-i", str(carpeta / "narracion.wav")]
    if pista:
        args += ["-stream_loop", "-1", "-i", pista["ruta"]]
    args += [
        "-filter_complex",
        filtro(pista is not None, cfg.audio.get("volumen_musica_db", -22), cfg.audio.get("ducking", True)),
        "-map",
        "[a]",
        "-ar",
        "48000",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(salida),
    ]
    ffmpeg.ejecutar(args)
    con.execute("DELETE FROM assets WHERE video_id = ? AND tipo = 'musica'", (video_id,))
    if pista:
        con.execute(
            "INSERT INTO assets (video_id, escena, tipo, origen, url, ruta, autor, licencia, atribucion, hash) "
            "VALUES (?, NULL, 'musica', ?, ?, ?, ?, ?, ?, ?)",
            (
                video_id,
                pista.get("origen", "biblioteca"),
                pista.get("url", ""),
                pista["ruta"],
                pista.get("autor", ""),
                pista.get("licencia", ""),
                pista.get("atribucion", ""),
                almacen.huella(pista["archivo"]),
            ),
        )
    con.commit()
    return salida
