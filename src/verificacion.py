"""Verificación de hechos: chequeo determinista de citas + veredicto del subagente verificador."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src import almacen, claude_cli, texto
from src.config import Config
from src.guion import texto_completo

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "afirmaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "fuente": {"type": ["string", "null"]},
                    "estado": {"enum": ["ok", "sin_fuente", "contradice"]},
                },
                "required": ["texto", "fuente", "estado"],
            },
        },
    },
    "required": ["afirmaciones"],
}


def chequeo_citas(g: dict[str, Any], dossier: dict[str, Any]) -> list[str]:
    """Toda cita del guion debe existir en el dossier."""
    ids = {a["id"] for a in dossier["afirmaciones"]}
    usadas = texto.citas(texto_completo(g))
    inexistentes = sorted(set(usadas) - ids)
    motivos = [f"citas inexistentes en el dossier: {inexistentes}"] if inexistentes else []
    if not usadas:
        motivos.append("el guion no cita ninguna fuente [F:id]")
    return motivos


def verificar(
    slug: str,
    g: dict[str, Any],
    dossier: dict[str, Any],
    cfg: Config,
    con: sqlite3.Connection,
    video_id: int,
    **kw: Any,
) -> tuple[bool, list[str]]:
    motivos = chequeo_citas(g, dossier)
    tarea = (
        "Enumera TODAS las afirmaciones factuales del guion (fechas, nombres, cifras, hechos). Para cada una, "
        "indica la cita [F:id] que la respalda y si el dossier la confirma (ok), no la respalda (sin_fuente) o "
        "la contradice (contradice). Las leyendas presentadas como leyenda cuentan como ok si citan su origen.\n"
        f"GUION:\n{texto_completo(g)}\n\nDOSSIER:\n{json.dumps(dossier, ensure_ascii=False)}"
    )
    r = claude_cli.llamar(
        "verificador",
        tarea,
        ESQUEMA,
        modelo=cfg.modelos["verificador"],
        max_turnos=cfg.max_turnos.get("verificador", 8),
        con=con,
        video_id=video_id,
        **kw,
    )
    afs = r["afirmaciones"]
    ok = sum(1 for a in afs if a["estado"] == "ok")
    pct = 100.0 * ok / len(afs) if afs else 0.0
    malas = [a for a in afs if a["estado"] != "ok"]
    if pct < cfg.calidad.fuentes_minimas_pct:
        motivos.append(
            f"verificación {pct:.0f} % (<{cfg.calidad.fuentes_minimas_pct:.0f} %): "
            + "; ".join(f"«{a['texto'][:80]}» {a['estado']}" for a in malas[:8])
        )
    aprobado = not motivos
    almacen.guardar_json(
        almacen.qa(slug, "verificacion"),
        {"afirmaciones": afs, "porcentaje_ok": round(pct, 1), "aprobado": aprobado, "motivos": motivos},
    )
    con.execute(
        "UPDATE guiones SET verificacion_pct = ? WHERE video_id = ? AND version = "
        "(SELECT MAX(version) FROM guiones WHERE video_id = ?)",
        (pct, video_id, video_id),
    )
    con.commit()
    return aprobado, motivos
