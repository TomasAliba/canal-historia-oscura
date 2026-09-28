"""Registro de decisiones del veto frente al veredicto automático y propuesta de cambio de modo.

Uso:
  python -m src.decisiones --registrar <slug> --resultado success|failure|cancelled|skipped
  python -m src.decisiones --coincidencia
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from src import db
from src.config import Config, config

# Resultado del job `publicar` → decisión humana.
TRADUCCION = {
    "success": "aprobado",
    "failure": "rechazado",
    "cancelled": "rechazado",
    "skipped": "sin_decision",
}


def registrar(con: sqlite3.Connection, slug: str, resultado: str) -> str:
    v = db.video(con, slug)
    if v is None:
        raise SystemExit(f"Vídeo desconocido: {slug}")
    decision = TRADUCCION.get(resultado, "sin_decision")
    con.execute(
        "INSERT INTO decisiones (video_id, veredicto_auto, decision_humana, fecha) VALUES (?, ?, ?, ?)",
        (v["id"], v["veredicto_auto"] or "aprobado", decision, db.ahora()),
    )
    if decision == "rechazado":
        db.actualizar_video(con, slug, estado="RECHAZADO_VETO")
    con.commit()
    return decision


def coincidencia(cfg: Config, con: sqlite3.Connection) -> dict[str, float | int | bool]:
    filas = con.execute(
        "SELECT veredicto_auto, decision_humana FROM decisiones WHERE decision_humana IN ('aprobado', 'rechazado')"
    ).fetchall()
    n = len(filas)
    iguales = sum(1 for f in filas if f["veredicto_auto"] == f["decision_humana"])
    pct = 100.0 * iguales / n if n else 0.0
    proponer = n >= cfg.veto.minimo_videos_para_cambio and pct > cfg.veto.umbral_cambio_pct
    return {
        "videos": n,
        "coincidencia_pct": round(pct, 1),
        "proponer_pasivo": proponer and cfg.veto.modo == "activo",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--registrar", metavar="SLUG")
    p.add_argument("--resultado", default="skipped")
    p.add_argument("--coincidencia", action="store_true")
    a = p.parse_args(argv)
    con = db.conectar()
    if a.registrar:
        print(registrar(con, a.registrar, a.resultado))
    else:
        print(json.dumps(coincidencia(config(), con), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
