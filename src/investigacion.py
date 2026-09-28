"""Investigación: dossier con afirmaciones etiquetadas y con fuente (subagente investigador)."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from src import almacen, claude_cli
from src.config import Config

_FUENTE = {
    "type": "object",
    "properties": {
        "autor": {"type": "string"},
        "obra": {"type": "string"},
        "anio": {"type": "string"},
        "url": {"type": "string"},
    },
    "required": ["autor", "obra", "anio", "url"],
}

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "descartar": {"type": "boolean"},
        "motivo_descarte": {"type": "string"},
        "anio_suceso": {
            "type": "integer",
            "description": "Año del suceso central (o de la primera documentación de la leyenda)",
        },
        "resumen": {"type": "string"},
        "cronologia": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string"},
                    "hecho": {"type": "string"},
                    "fuente_id": {"type": "string"},
                },
                "required": ["fecha", "hecho", "fuente_id"],
            },
        },
        "personajes": {"type": "array", "items": {"type": "string"}},
        "afirmaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "F1, F2, ..."},
                    "texto": {"type": "string"},
                    "etiqueta": {"enum": ["HECHO", "LEYENDA", "ESPECULACION"]},
                    "fuente": _FUENTE,
                },
                "required": ["id", "texto", "etiqueta", "fuente"],
            },
        },
        "lagunas": {"type": "array", "items": {"type": "string"}},
        "busquedas_imagenes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Consultas para Wikimedia Commons (grabados, mapas, retratos)",
        },
    },
    "required": [
        "descartar",
        "motivo_descarte",
        "anio_suceso",
        "resumen",
        "cronologia",
        "personajes",
        "afirmaciones",
        "lagunas",
        "busquedas_imagenes",
    ],
}


class Descartado(Exception):
    """El tema no cumple las reglas (antigüedad, personas vivas, víctimas infantiles, fuentes)."""


def tarea(tema: dict[str, str], cfg: Config) -> str:
    limite = date.today().year - cfg.contenido.antiguedad_minima_anios
    return (
        f"Tema: {tema.get('titulo_trabajo') or tema['slug']} (país: {tema.get('pais')}, "
        f"época: {tema.get('epoca')}). Notas editoriales: {tema.get('notas', '')}\n\n"
        f"Investiga con WebSearch y WebFetch y devuelve el dossier en el formato JSON pedido.\n"
        f"- Descarta (descartar=true) si el suceso central es posterior a {limite}, si hay víctimas "
        f"infantiles como eje del relato o si aparecen personas vivas identificables.\n"
        f"- Mínimo 12 afirmaciones; cada HECHO con fuente verificable (obra y año; URL si existe).\n"
        f"- Las LEYENDAS llevan como fuente su primera recopilación conocida.\n"
        f"- En busquedas_imagenes, 8-15 consultas en español o inglés para material de dominio público."
    )


def validar(d: dict[str, Any], cfg: Config) -> None:
    limite = date.today().year - cfg.contenido.antiguedad_minima_anios
    if d.get("descartar"):
        raise Descartado(d.get("motivo_descarte") or "descartado por el investigador")
    if int(d.get("anio_suceso") or 0) > limite:
        raise Descartado(f"suceso de {d.get('anio_suceso')}: posterior al corte de {limite}")
    afs = d.get("afirmaciones") or []
    if len(afs) < 8:
        raise Descartado(f"documentación insuficiente: {len(afs)} afirmaciones")
    ids = [a["id"] for a in afs]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de afirmación duplicados en el dossier")
    sin_fuente = [a["id"] for a in afs if a["etiqueta"] == "HECHO" and not a["fuente"].get("obra", "").strip()]
    if sin_fuente:
        raise ValueError(f"hechos sin fuente en el dossier: {sin_fuente}")


def a_markdown(tema: dict[str, str], d: dict[str, Any]) -> str:
    lineas = [
        f"# Dossier: {tema.get('titulo_trabajo') or tema['slug']}",
        "",
        "## Resumen",
        d["resumen"],
        "",
        "## Cronología",
    ]
    lineas += [f"- **{c['fecha']}** — {c['hecho']} [{c['fuente_id']}]" for c in d["cronologia"]]
    lineas += ["", "## Afirmaciones"]
    for a in d["afirmaciones"]:
        f = a["fuente"]
        ref = ", ".join(x for x in (f.get("autor"), f.get("obra"), f.get("anio"), f.get("url")) if x)
        lineas.append(f"- **{a['id']}** ({a['etiqueta']}) {a['texto']} — _{ref}_")
    lineas += ["", "## Lagunas y versiones contradictorias", *[f"- {x}" for x in d["lagunas"]]]
    return "\n".join(lineas) + "\n"


def investigar(
    tema: dict[str, str], cfg: Config, con: sqlite3.Connection, video_id: int, **kw: Any
) -> dict[str, Any]:
    d = claude_cli.llamar(
        "investigador",
        tarea(tema, cfg),
        ESQUEMA,
        modelo=cfg.modelos["investigador"],
        max_turnos=cfg.max_turnos.get("investigador", 40),
        herramientas=("WebSearch", "WebFetch"),
        con=con,
        video_id=video_id,
        **kw,
    )
    validar(d, cfg)
    slug = tema["slug"]
    almacen.guardar_json(almacen.dossier(slug), d)
    almacen.dossier(slug).with_suffix(".md").write_text(a_markdown(tema, d), encoding="utf-8")
    con.execute("DELETE FROM afirmaciones WHERE video_id = ?", (video_id,))
    con.executemany(
        "INSERT INTO afirmaciones (video_id, id, texto, etiqueta, fuente) VALUES (?, ?, ?, ?, ?)",
        [(video_id, a["id"], a["texto"], a["etiqueta"], str(a["fuente"])) for a in d["afirmaciones"]],
    )
    con.execute(
        "INSERT OR REPLACE INTO dossiers (video_id, ruta, hash, n_fuentes, lagunas) VALUES (?, ?, ?, ?, ?)",
        (
            video_id,
            str(almacen.dossier(slug)),
            almacen.huella(d),
            len(d["afirmaciones"]),
            "\n".join(d["lagunas"]),
        ),
    )
    con.commit()
    return d
