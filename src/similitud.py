"""Similitud entre guiones: coseno TF-IDF (unigramas + bigramas), determinista y sin dependencias."""

from __future__ import annotations

import math
import re
from collections import Counter
from itertools import pairwise
from pathlib import Path

from src import almacen, texto
from src.config import dir_estado
from src.guion import texto_completo

_VACIAS = set(
    "el la los las un una unos unas de del al a y o u e ni que en con por para como su sus se lo le les "
    "no si mas más pero es fue era son han ha había sobre entre sin tras desde hasta este esta estos estas "
    "ese esa eso aquel aquella muy ya también cuando donde quien cual".split()
)


def terminos(t: str) -> list[str]:
    palabras = [p for p in re.findall(r"[a-záéíóúñü]+", texto.limpio(t).lower()) if p not in _VACIAS]
    return palabras + [f"{a}_{b}" for a, b in pairwise(palabras)]


def _tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df = Counter(t for d in docs for t in set(d))
    vecs = []
    for d in docs:
        tf = Counter(d)
        v = {t: (c / len(d)) * (math.log((1 + n) / (1 + df[t])) + 1) for t, c in tf.items()} if d else {}
        vecs.append(v)
    return vecs


def coseno(a: dict[str, float], b: dict[str, float]) -> float:
    num = sum(v * b.get(t, 0.0) for t, v in a.items())
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def maxima(nuevo: str, anteriores: list[str]) -> float:
    if not anteriores:
        return 0.0
    vecs = _tfidf([terminos(nuevo), *(terminos(t) for t in anteriores)])
    return max(coseno(vecs[0], v) for v in vecs[1:])


def guiones_anteriores(excluir_slug: str) -> list[str]:
    carpeta: Path = dir_estado() / "guiones"
    if not carpeta.exists():
        return []
    return [texto_completo(almacen.leer_json(p)) for p in sorted(carpeta.glob("*.json")) if p.stem != excluir_slug]
