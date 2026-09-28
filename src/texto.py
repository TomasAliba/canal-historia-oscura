"""Utilidades de texto del guion: citas [F:n], marcas de pausa, frases y recuento de palabras."""

from __future__ import annotations

import re
import unicodedata

CITA = re.compile(r"\[F:([\w-]+)\]")
PAUSA = re.compile(r"\[pause(?: short| long)?\]")
VISUAL = re.compile(r"\[VISUAL:[^\]]*\]")
_FRASE = re.compile(r"(?<=[.!?…])\s+(?=[¿¡\"«A-ZÁÉÍÓÚÑ0-9])")


def citas(texto: str) -> list[str]:
    return CITA.findall(texto)


def para_locucion(texto: str) -> str:
    """Texto que se envía al TTS: sin citas ni indicaciones visuales, conservando las pausas."""
    t = VISUAL.sub("", CITA.sub("", texto))
    return re.sub(r"\s+", " ", t).replace(" .", ".").replace(" ,", ",").strip()


def limpio(texto: str) -> str:
    """Texto legible (subtítulos, similitud): sin citas, pausas ni indicaciones visuales."""
    return re.sub(r"\s+", " ", PAUSA.sub("", para_locucion(texto))).strip()


def frases(texto: str) -> list[str]:
    return [f.strip() for f in _FRASE.split(texto.strip()) if f.strip()]


def palabras(texto: str) -> int:
    return len(re.findall(r"\b\w+\b", limpio(texto)))


def slugificar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]
