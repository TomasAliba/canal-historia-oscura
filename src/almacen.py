"""Rutas y lectura/escritura de artefactos (JSON y Markdown) de cada vídeo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.config import dir_estado, dir_media


def dossier(slug: str) -> Path:
    return dir_estado() / "dossiers" / f"{slug}.json"


def guion(slug: str) -> Path:
    return dir_estado() / "guiones" / f"{slug}.json"


def qa(slug: str, tipo: str) -> Path:
    return dir_estado() / "qa" / f"{slug}-{tipo}.json"


def media(slug: str) -> Path:
    p = dir_media() / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


def guardar_json(ruta: Path, datos: Any) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta)  # escritura atómica: un fallo no deja artefactos a medias
    return ruta


def leer_json(ruta: Path) -> Any:
    return json.loads(ruta.read_text(encoding="utf-8"))


def huella(*partes: Any) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, ensure_ascii=False, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]
