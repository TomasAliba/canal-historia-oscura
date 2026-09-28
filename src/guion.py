"""Guion: capítulos → párrafos (una escena por párrafo) con citas [F:id] e indicación visual."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src import almacen, claude_cli, texto
from src.config import Config

PLANTILLAS = {
    "cronologica": "Relato cronológico: del contexto a las consecuencias, con saltos de tensión.",
    "in_media_res": "Empieza en el momento más intenso, retrocede al origen y vuelve al clímax.",
    "investigacion": "Plantea el enigma como un expediente: pistas, hipótesis enfrentadas y veredicto abierto.",
    "testimonio": "Hilo conductor en testimonios de época (cartas, actas, crónicas), citados y contextualizados.",
}

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "titulo_trabajo": {"type": "string"},
        "capitulos": {
            "type": "array",
            "minItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "parrafos": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "texto": {
                                    "type": "string",
                                    "description": "Narración con citas [F:id] tras cada dato "
                                    "factual y pausas [pause]/[pause long] donde proceda",
                                },
                                "visual": {
                                    "type": "string",
                                    "description": "Qué se ve: grabado, mapa, retrato, lugar",
                                },
                                "busqueda": {
                                    "type": "string",
                                    "description": "Consulta corta para Wikimedia Commons",
                                },
                            },
                            "required": ["texto", "visual", "busqueda"],
                        },
                    },
                },
                "required": ["titulo", "parrafos"],
            },
        },
        "cta": {"type": "string"},
    },
    "required": ["titulo_trabajo", "capitulos", "cta"],
}


def tarea(dossier: dict[str, Any], plantilla: str, cfg: Config, motivos: list[str]) -> str:
    f = cfg.formato
    partes = [
        f"Plantilla: {plantilla}. {PLANTILLAS[plantilla]}",
        f"Extensión total: {f.palabras_min}-{f.palabras_max} palabras de narración (sin contar citas).",
        "El primer capítulo es el cold open (gancho en los primeros 15 segundos). Re-enganche cada "
        "60-90 s. El último capítulo cierra con desenlace o misterio abierto; el CTA va aparte y es breve.",
        "Cada dato factual lleva su cita [F:id] del dossier. No afirmes nada que no esté en el dossier.",
        "Distingue en el texto lo documentado de la leyenda y de la especulación.",
        "Nada de detalle gráfico ni morboso: atmósfera, elipsis y sugerencia.",
        "Español de España, registro culto pero cercano. Narrador: el Escribano de Ánimas.",
    ]
    if motivos:
        partes.append("La versión anterior NO superó los controles. Corrige esto: " + "; ".join(motivos))
    partes.append("DOSSIER (JSON):\n" + json.dumps(dossier, ensure_ascii=False))
    return "\n".join(partes)


def texto_completo(g: dict[str, Any]) -> str:
    return "\n\n".join(p["texto"] for c in g["capitulos"] for p in c["parrafos"]) + "\n\n" + g["cta"]


def a_markdown(g: dict[str, Any]) -> str:
    out = [f"# {g['titulo_trabajo']}", ""]
    for c in g["capitulos"]:
        out += [f"## {c['titulo']}", ""]
        for p in c["parrafos"]:
            out += [p["texto"], f"_[VISUAL: {p['visual']}]_", ""]
    out += ["## CTA", g["cta"], ""]
    return "\n".join(out)


def escribir(
    slug: str,
    dossier: dict[str, Any],
    plantilla: str,
    cfg: Config,
    con: sqlite3.Connection,
    video_id: int,
    motivos: list[str] | None = None,
    usar_fallback: bool = False,
    **kw: Any,
) -> dict[str, Any]:
    modelo = cfg.modelos["guionista_fallback" if usar_fallback else "guionista"]
    g = claude_cli.llamar(
        "guionista",
        tarea(dossier, plantilla, cfg, motivos or []),
        ESQUEMA,
        modelo=modelo,
        max_turnos=cfg.max_turnos.get("guionista", 6),
        con=con,
        video_id=video_id,
        **kw,
    )
    g["plantilla"] = plantilla
    n = texto.palabras(texto_completo(g))
    g["palabras"] = n
    version = (
        (
            con.execute(
                "SELECT COALESCE(MAX(version), 0) FROM guiones WHERE video_id = ?", (video_id,)
            ).fetchone()[0]
        )
        + 1
    )
    ruta = almacen.guardar_json(almacen.guion(slug), g)
    ruta.with_suffix(".md").write_text(a_markdown(g), encoding="utf-8")
    con.execute(
        "INSERT INTO guiones (video_id, version, ruta, palabras, plantilla) VALUES (?, ?, ?, ?, ?)",
        (video_id, version, str(ruta), n, plantilla),
    )
    con.commit()
    return g


def control_extension(g: dict[str, Any], cfg: Config) -> list[str]:
    n = g.get("palabras") or texto.palabras(texto_completo(g))
    if n < cfg.formato.palabras_min:
        return [f"el guion tiene {n} palabras; mínimo {cfg.formato.palabras_min}"]
    if n > cfg.formato.palabras_max:
        return [f"el guion tiene {n} palabras; máximo {cfg.formato.palabras_max}"]
    return []
