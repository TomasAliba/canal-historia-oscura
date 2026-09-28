"""Montaje con FFmpeg: una escena por imagen (Ken Burns, grano, viñeta), capítulos y audio final."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path
from typing import Any

from src import almacen, ffmpeg
from src.config import Config, raiz

MOVIMIENTOS = ("acercar", "alejar", "izquierda", "derecha")


def fotogramas_por_escena(escenas: list[dict[str, Any]], duracion: float, fps: int) -> list[int]:
    """Frames exactos por escena sin deriva acumulada: cada escena dura hasta el inicio de la siguiente."""
    limites = [round(e["inicio"] * fps) for e in escenas] + [round(duracion * fps)]
    limites[0] = 0
    return [max(1, b - a) for a, b in pairwise(limites)]


def filtro_escena(movimiento: str, n: int, ancho: int, alto: int, fps: int, cfg: Config) -> str:
    ef = cfg.visuales.get("efectos", {})
    zw, zh = int(ancho * 1.25) // 2 * 2, int(alto * 1.25) // 2 * 2
    z = {"acercar": f"1+0.12*on/{n}", "alejar": f"1.12-0.12*on/{n}"}.get(movimiento, "1.1")
    x = {"izquierda": f"(iw-iw/zoom)*(1-on/{n})", "derecha": f"(iw-iw/zoom)*on/{n}"}.get(
        movimiento, "iw/2-(iw/zoom/2)"
    )
    partes = [
        f"scale={zw}:{zh}:force_original_aspect_ratio=increase",
        f"crop={zw}:{zh}",
        f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s={ancho}x{alto}:fps={fps}"
        if ef.get("ken_burns", True)
        else f"scale={ancho}:{alto}",
    ]
    if ef.get("grano", True):
        partes.append("noise=alls=9:allf=t")
    if ef.get("vineta", True):
        partes.append("vignette=PI/5")
    partes.append("format=yuv420p")
    return ",".join(partes)


def metadatos_capitulos(capitulos: list[dict[str, Any]], duracion: float) -> str:
    lineas = [";FFMETADATA1"]
    for i, c in enumerate(capitulos):
        fin = capitulos[i + 1]["inicio"] if i + 1 < len(capitulos) else duracion
        titulo = c["titulo"].replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")
        lineas += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={int(c['inicio'] * 1000)}",
            f"END={int(fin * 1000)}",
            f"title={titulo}",
        ]
    return "\n".join(lineas) + "\n"


def montar(slug: str, tiempos: dict[str, Any], imagenes: list[dict[str, Any]], cfg: Config) -> Path:
    carpeta = almacen.media(slug)
    clips = carpeta / "clips"
    clips.mkdir(exist_ok=True)
    ancho, alto = cfg.formato.resolucion
    fps = cfg.formato.fps
    frames = fotogramas_por_escena(tiempos["escenas"], tiempos["duracion"], fps)
    lista = []
    for i, (img, n) in enumerate(zip(imagenes, frames, strict=True)):
        clip = clips / f"clip_{i:03}.mp4"
        clave = almacen.huella(img["ruta"], n, ancho, alto, i)
        marca = clip.with_suffix(".ok")
        if not (clip.exists() and marca.exists() and marca.read_text() == clave):  # idempotente
            ffmpeg.ejecutar(
                [
                    "-loop",
                    "1",
                    "-framerate",
                    str(fps),
                    "-i",
                    img["ruta"],
                    "-vf",
                    filtro_escena(MOVIMIENTOS[i % len(MOVIMIENTOS)], n, ancho, alto, fps, cfg),
                    "-frames:v",
                    str(n),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip),
                ]
            )
            marca.write_text(clave)
        lista.append(f"file '{clip.name}'")
    (clips / "lista.txt").write_text("\n".join(lista) + "\n", encoding="utf-8")
    mudo = carpeta / "video_mudo.mp4"
    ffmpeg.ejecutar(["-f", "concat", "-safe", "0", "-i", str(clips / "lista.txt"), "-c", "copy", str(mudo)])

    meta = carpeta / "capitulos.txt"
    meta.write_text(metadatos_capitulos(tiempos["capitulos"], tiempos["duracion"]), encoding="utf-8")
    cuerpo = carpeta / "cuerpo.mp4"
    ffmpeg.ejecutar(
        [
            "-i",
            str(mudo),
            "-i",
            str(carpeta / "audio.m4a"),
            "-i",
            str(meta),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map_metadata",
            "2",
            "-map_chapters",
            "2",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-shortest",
            "-movflags",
            "+faststart",
            str(cuerpo),
        ]
    )
    return _con_marca(carpeta, cuerpo)


def desfase_intro() -> float:
    """Segundos que desplaza la intro de marca a los capítulos (0 si no hay intro)."""
    intro = raiz() / "assets" / "marca" / "intro.mp4"
    return ffmpeg.duracion(intro) if intro.exists() else 0.0


def _con_marca(carpeta: Path, cuerpo: Path) -> Path:
    """Añade intro/outro de marca si existen en assets/marca/ (misma codificación: 1080p30 H.264 + AAC 48 kHz).
    Los capítulos se conservan desplazados por el concat demuxer."""
    marca = raiz() / "assets" / "marca"
    partes = [p for p in (marca / "intro.mp4", cuerpo, marca / "outro.mp4") if p.exists()]
    final = carpeta / "final.mp4"
    if len(partes) == 1:
        cuerpo.replace(final)
        return final
    lista = carpeta / "final_lista.txt"
    lista.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in partes), encoding="utf-8")
    ffmpeg.ejecutar(
        ["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(final)]
    )
    return final
