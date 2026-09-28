"""Control de uso (el "presupuesto" en modo coste 0). `python -m src.uso --check` sale con 1 si se supera."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime, timedelta

from src import db
from src.config import Config, config

ESTADOS_PRODUCIDOS = ("ESPERANDO_PUBLICACION", "PROGRAMADO", "PUBLICADO", "RECHAZADO_VETO")


def comprobar(cfg: Config, con: sqlite3.Connection, ahora: datetime | None = None) -> list[str]:
    ahora = ahora or datetime.now(UTC)
    lunes = (ahora - timedelta(days=ahora.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    marcas = ",".join("?" * len(ESTADOS_PRODUCIDOS))
    semana = con.execute(
        f"SELECT COUNT(*) FROM videos WHERE estado IN ({marcas}) AND actualizado >= ?",
        (*ESTADOS_PRODUCIDOS, lunes.isoformat()),
    ).fetchone()[0]
    tts = con.execute(
        "SELECT COALESCE(SUM(caracteres_tts),0) FROM uso WHERE fecha >= ?", (mes.isoformat(),)
    ).fetchone()[0]
    ia_hoy = con.execute(
        "SELECT COALESCE(SUM(imagenes_ia),0) FROM uso WHERE fecha >= ?",
        (ahora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),),
    ).fetchone()[0]
    motivos = []
    if semana >= cfg.uso.max_videos_semana:
        motivos.append(f"ya se produjeron {semana} vídeo(s) esta semana (máx. {cfg.uso.max_videos_semana})")
    if tts >= cfg.uso.max_caracteres_tts_mes:
        motivos.append(f"TTS del mes: {tts} caracteres (máx. {cfg.uso.max_caracteres_tts_mes})")
    if ia_hoy >= cfg.uso.max_imagenes_ia_dia:
        motivos.append(f"imágenes IA hoy: {ia_hoy} (máx. {cfg.uso.max_imagenes_ia_dia})")
    return motivos


def imagenes_ia_restantes(cfg: Config, con: sqlite3.Connection) -> int:
    hoy = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    usadas = con.execute("SELECT COALESCE(SUM(imagenes_ia),0) FROM uso WHERE fecha >= ?", (hoy,)).fetchone()[0]
    return max(0, cfg.uso.max_imagenes_ia_dia - usadas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.parse_args(argv)
    motivos = comprobar(config(), db.conectar())
    for m in motivos:
        print(m)
    return 1 if motivos else 0


if __name__ == "__main__":
    sys.exit(main())
