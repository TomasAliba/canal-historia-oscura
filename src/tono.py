"""Filtro de tono publicitario: léxico determinista + puntuación y reescritura del subagente."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from src import almacen, claude_cli
from src.config import Config
from src.guion import texto_completo

# Términos que casi siempre implican detalle gráfico. Mencionar una muerte no es riesgo;
# describirla con este vocabulario sí.
LEXICO_RIESGO = [
    r"v[ií]sceras",
    r"desmembr\w*",
    r"descuartiz\w*",
    r"degoll\w*",
    r"decapit\w*",
    r"destrip\w*",
    r"sangre a borbotones",
    r"charco de sangre",
    r"sesos",
    r"cr[aá]neo (?:abierto|destrozado)",
    r"entra[ñn]as",
    r"mutilad\w*",
    r"putrefac\w*",
    r"gusanos",
    r"agon[ií]a lenta",
]
_LEXICO = re.compile(r"\b(" + "|".join(LEXICO_RIESGO) + r")\b", re.IGNORECASE)

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "riesgo_global": {"type": "number", "minimum": 0, "maximum": 10},
        "pasajes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string", "description": "Fragmento literal del guion"},
                    "reescrito": {"type": "string"},
                    "riesgo": {"type": "number"},
                },
                "required": ["original", "reescrito", "riesgo"],
            },
        },
        "riesgo_tras_reescritura": {"type": "number", "minimum": 0, "maximum": 10},
    },
    "required": ["riesgo_global", "pasajes", "riesgo_tras_reescritura"],
}


def terminos_de_riesgo(t: str) -> list[str]:
    return sorted({m.group(0).lower() for m in _LEXICO.finditer(t)})


def aplicar_reescrituras(g: dict[str, Any], pasajes: list[dict[str, Any]]) -> int:
    n = 0
    for p in pasajes:
        for c in g["capitulos"]:
            for par in c["parrafos"]:
                if p["original"] and p["original"] in par["texto"]:
                    par["texto"] = par["texto"].replace(p["original"], p["reescrito"])
                    n += 1
    return n


def filtrar(
    slug: str, g: dict[str, Any], cfg: Config, con: sqlite3.Connection, video_id: int, **kw: Any
) -> tuple[bool, list[str], dict[str, Any]]:
    umbral = cfg.calidad.max_riesgo_tono
    tarea = (
        "Puntúa de 0 a 10 el riesgo del guion según las directrices de contenido apto para anunciantes de "
        "YouTube (violencia gráfica, gore, detalle morboso, lenguaje explícito, contenido impactante, "
        f"sensacionalismo sobre tragedias). Reescribe cada pasaje con riesgo > {umbral} usando elipsis y "
        "sugerencia, manteniendo la tensión y las citas [F:id]. 'original' debe ser un fragmento literal.\n"
        f"GUION:\n{texto_completo(g)}"
    )
    r = claude_cli.llamar(
        "filtro-tono",
        tarea,
        ESQUEMA,
        modelo=cfg.modelos["filtro_tono"],
        max_turnos=cfg.max_turnos.get("filtro_tono", 6),
        con=con,
        video_id=video_id,
        **kw,
    )
    n = aplicar_reescrituras(g, r["pasajes"])
    residuales = terminos_de_riesgo(texto_completo(g))
    riesgo = float(r["riesgo_tras_reescritura"])
    motivos = []
    if riesgo > umbral:
        motivos.append(f"riesgo de tono {riesgo} > {umbral}")
    if residuales:
        motivos.append(f"términos gráficos tras la reescritura: {residuales}")
    aprobado = not motivos
    almacen.guardar_json(almacen.guion(slug), g)
    almacen.guardar_json(
        almacen.qa(slug, "tono"),
        {
            "riesgo_global": r["riesgo_global"],
            "riesgo_final": riesgo,
            "pasajes_reescritos": n,
            "aprobado": aprobado,
            "motivos": motivos,
        },
    )
    con.execute(
        "UPDATE guiones SET riesgo_tono = ? WHERE video_id = ? AND version = "
        "(SELECT MAX(version) FROM guiones WHERE video_id = ?)",
        (riesgo, video_id, video_id),
    )
    con.commit()
    return aprobado, motivos, g
