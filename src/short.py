"""Short-tráiler vertical (9:16) con el cold open: embudo hacia el vídeo largo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src import almacen, ffmpeg
from src.config import Config


def duracion_trailer(tiempos: dict[str, Any], cfg: Config) -> float:
    """Hasta el final de la última frase que cabe en el límite, para no cortar a media frase."""
    limite = cfg.formato.short_trailer_s
    fines = [f["fin"] for esc in tiempos["escenas"] for f in esc["frases"] if f["fin"] <= limite]
    return round(max(fines, default=min(limite, tiempos["duracion"])), 2)


def generar(slug: str, tiempos: dict[str, Any], cfg: Config, final: Path, desfase: float = 0.0) -> Path:
    salida = almacen.media(slug) / "short.mp4"
    dur = duracion_trailer(tiempos, cfg)
    filtro = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[fondo];"
        "[0:v]scale=1080:-2[frente];[fondo][frente]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v];"
        f"[0:a]afade=t=out:st={max(0.0, dur - 1.0)}:d=1[a]"
    )
    ffmpeg.ejecutar(
        [
            "-ss",
            str(desfase),
            "-t",
            str(dur),
            "-i",
            str(final),
            "-filter_complex",
            filtro,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(salida),
        ]
    )
    return salida
