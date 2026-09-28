"""Ejecución de FFmpeg/ffprobe con errores legibles."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class ErrorFFmpeg(RuntimeError):
    pass


def ejecutar(args: list[str]) -> None:
    exe = shutil.which("ffmpeg") or "ffmpeg"
    proc = subprocess.run(
        [exe, "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise ErrorFFmpeg(f"ffmpeg falló ({proc.returncode}): {proc.stderr[-1500:]}")


def sondear(ruta: Path) -> dict:
    exe = shutil.which("ffprobe") or "ffprobe"
    proc = subprocess.run(
        [
            exe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(ruta),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise ErrorFFmpeg(f"ffprobe falló: {proc.stderr[-500:]}")
    return json.loads(proc.stdout)


def duracion(ruta: Path) -> float:
    return float(sondear(ruta)["format"]["duration"])
