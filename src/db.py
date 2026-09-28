"""Modelo de datos en SQLite (data/estado/canal.db). Un solo escritor: el pipeline."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import dir_estado

ESQUEMA = """
CREATE TABLE IF NOT EXISTS temas (
  slug TEXT PRIMARY KEY, titulo TEXT, pais TEXT, tipo TEXT, epoca TEXT, antiguedad_anios INTEGER,
  prioridad REAL, calendario TEXT, plantilla TEXT, estado TEXT, motivo_descarte TEXT, notas TEXT
);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, plantilla TEXT, estado TEXT NOT NULL,
  intentos_guion INTEGER DEFAULT 0, intentos_qa INTEGER DEFAULT 0, youtube_id TEXT, publish_at TEXT,
  duracion_s REAL, veredicto_auto TEXT, motivos TEXT, creado TEXT, actualizado TEXT
);
CREATE TABLE IF NOT EXISTS dossiers (
  video_id INTEGER PRIMARY KEY REFERENCES videos(id), ruta TEXT, hash TEXT, n_fuentes INTEGER, lagunas TEXT
);
CREATE TABLE IF NOT EXISTS afirmaciones (
  video_id INTEGER REFERENCES videos(id), id TEXT, texto TEXT, etiqueta TEXT, fuente TEXT,
  PRIMARY KEY (video_id, id)
);
CREATE TABLE IF NOT EXISTS guiones (
  video_id INTEGER REFERENCES videos(id), version INTEGER, ruta TEXT, palabras INTEGER, plantilla TEXT,
  similitud_max REAL, riesgo_tono REAL, verificacion_pct REAL, PRIMARY KEY (video_id, version)
);
CREATE TABLE IF NOT EXISTS trabajos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, video_id INTEGER, inicio TEXT, fin TEXT,
  estado TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS pasos (
  trabajo_id INTEGER REFERENCES trabajos(id), paso TEXT, intento INTEGER, estado TEXT, inicio TEXT,
  fin TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS assets (
  video_id INTEGER REFERENCES videos(id), escena INTEGER, tipo TEXT, origen TEXT, url TEXT, ruta TEXT,
  autor TEXT, licencia TEXT, atribucion TEXT, hash TEXT
);
CREATE TABLE IF NOT EXISTS uso (
  fecha TEXT, video_id INTEGER, paso TEXT, modelo TEXT, llamadas INTEGER DEFAULT 0, turnos INTEGER DEFAULT 0,
  tokens_entrada INTEGER DEFAULT 0, tokens_salida INTEGER DEFAULT 0, caracteres_tts INTEGER DEFAULT 0,
  imagenes_ia INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS metricas (
  video_id INTEGER REFERENCES videos(id), fecha TEXT, vistas INTEGER, retencion_media REAL,
  retencion_curva TEXT, fuentes_trafico TEXT, PRIMARY KEY (video_id, fecha)
);
CREATE TABLE IF NOT EXISTS decisiones (
  video_id INTEGER REFERENCES videos(id), veredicto_auto TEXT, decision_humana TEXT, fecha TEXT
);
"""


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ruta_db() -> Path:
    return dir_estado() / "canal.db"


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = ruta or ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def video(con: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM videos WHERE slug = ?", (slug,)).fetchone()


def crear_video(con: sqlite3.Connection, slug: str, plantilla: str) -> sqlite3.Row:
    t = ahora()
    con.execute(
        "INSERT INTO videos (slug, plantilla, estado, creado, actualizado) VALUES (?, ?, 'PENDIENTE', ?, ?)",
        (slug, plantilla, t, t),
    )
    con.commit()
    fila = video(con, slug)
    assert fila is not None
    return fila


def actualizar_video(con: sqlite3.Connection, slug: str, **campos: Any) -> None:
    if not campos:
        return
    campos["actualizado"] = ahora()
    for k, v in list(campos.items()):
        if isinstance(v, (list, dict)):
            campos[k] = json.dumps(v, ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in campos)
    con.execute(f"UPDATE videos SET {sets} WHERE slug = ?", (*campos.values(), slug))
    con.commit()


def registrar_uso(con: sqlite3.Connection, video_id: int | None, paso: str, **valores: Any) -> None:
    cols = ["fecha", "video_id", "paso", *valores]
    con.execute(
        f"INSERT INTO uso ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        (ahora(), video_id, paso, *valores.values()),
    )
    con.commit()
