"""Miniaturas: 3 variantes 1280x720 (composición, tipografía y color) para test A/B."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from src import almacen

TAM = (1280, 720)
FUENTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
ESTILOS = [
    {"texto": (240, 230, 210), "borde": (0, 0, 0), "acento": (160, 20, 20), "lado": "izquierda"},
    {"texto": (255, 215, 90), "borde": (20, 10, 0), "acento": (0, 0, 0), "lado": "derecha"},
    {"texto": (255, 255, 255), "borde": (120, 0, 0), "acento": (120, 0, 0), "lado": "abajo"},
]


def fuente(tam: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for f in FUENTES:
        if Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default(size=tam)


def _envolver(texto: str, max_car: int = 14) -> list[str]:
    lineas, actual = [], ""
    for p in texto.split():
        if actual and len(actual) + 1 + len(p) > max_car:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    return [*lineas, actual] if actual else lineas


def variante(base: Path, texto: str, estilo: dict, destino: Path) -> Path:
    img = ImageOps.fit(Image.open(base).convert("RGB"), TAM)
    img = ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(0.7)).enhance(1.3)
    capa = Image.new("L", TAM, 0)
    d = ImageDraw.Draw(capa)
    if estilo["lado"] == "izquierda":
        d.rectangle([0, 0, TAM[0] // 2, TAM[1]], fill=170)
    elif estilo["lado"] == "derecha":
        d.rectangle([TAM[0] // 2, 0, TAM[0], TAM[1]], fill=170)
    else:
        d.rectangle([0, TAM[1] * 3 // 5, TAM[0], TAM[1]], fill=180)
    img.paste(Image.new("RGB", TAM, (0, 0, 0)), mask=capa.filter(ImageFilter.GaussianBlur(60)))
    dib = ImageDraw.Draw(img)
    lineas = _envolver(texto.upper())
    tam = 120 if len(lineas) <= 2 else 92
    f = fuente(tam)
    x = {"izquierda": 60, "derecha": TAM[0] // 2 + 30, "abajo": 60}[estilo["lado"]]
    y = TAM[1] - (tam + 14) * len(lineas) - 50 if estilo["lado"] == "abajo" else 90
    for i, linea in enumerate(lineas):
        dib.text(
            (x, y + i * (tam + 14)),
            linea,
            font=f,
            fill=estilo["texto"],
            stroke_width=6,
            stroke_fill=estilo["borde"],
        )
    dib.rectangle([x, y - 26, x + 180, y - 12], fill=estilo["acento"])
    img.save(destino, "JPEG", quality=90, optimize=True)
    if destino.stat().st_size > 2_000_000:  # límite de YouTube: 2 MB
        img.save(destino, "JPEG", quality=75, optimize=True)
    return destino


def generar(slug: str, bases: list[Path], textos: list[str]) -> list[Path]:
    carpeta = almacen.media(slug) / "miniaturas"
    carpeta.mkdir(exist_ok=True)
    salida = []
    for i, (estilo, texto) in enumerate(zip(ESTILOS, textos, strict=False)):
        base = bases[i % len(bases)]
        salida.append(variante(base, texto, estilo, carpeta / f"miniatura_{i + 1}.jpg"))
    return salida


if __name__ == "__main__":  # prueba manual: python -m src.miniaturas imagen.jpg "TEXTO"
    print(variante(Path(sys.argv[1]), sys.argv[2], ESTILOS[0], Path("miniatura_prueba.jpg")))
