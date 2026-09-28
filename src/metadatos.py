"""Metadatos: títulos, descripción con fuentes y capítulos, etiquetas y textos de miniatura."""

from __future__ import annotations

import sqlite3
from typing import Any

from src import almacen, claude_cli
from src.config import Config
from src.guion import texto_completo

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "titulos": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "string", "maxLength": 95}},
        "gancho_descripcion": {"type": "string", "description": "2-3 frases para el inicio de la descripción"},
        "etiquetas": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
        "textos_miniatura": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string", "maxLength": 28},
        },
    },
    "required": ["titulos", "gancho_descripcion", "etiquetas", "textos_miniatura"],
}


def marca_tiempo(s: float) -> str:
    s = int(s)
    h, r = divmod(s, 3600)
    m, seg = divmod(r, 60)
    return f"{h}:{m:02}:{seg:02}" if h else f"{m}:{seg:02}"


def capitulos_youtube(capitulos: list[dict[str, Any]], desfase: float = 0.0) -> list[str]:
    """YouTube exige empezar en 0:00, al menos 3 capítulos y 10 s mínimo por capítulo."""
    out: list[tuple[float, str]] = []
    for i, c in enumerate(capitulos):
        t = 0.0 if i == 0 else c["inicio"] + desfase
        if out and t - out[-1][0] < 10:
            continue
        out.append((t, c["titulo"]))
    return [f"{marca_tiempo(t)} {titulo}" for t, titulo in out] if len(out) >= 3 else []


def fuentes_citadas(g: dict[str, Any], dossier: dict[str, Any]) -> list[str]:
    from src.texto import citas

    usadas = set(citas(texto_completo(g)))
    vistas, lineas = set(), []
    for a in dossier["afirmaciones"]:
        f = a["fuente"]
        clave = (f.get("autor"), f.get("obra"))
        if a["id"] in usadas and clave not in vistas:
            vistas.add(clave)
            ref = ", ".join(x for x in (f.get("autor"), f.get("obra"), f.get("anio")) if x)
            lineas.append(f"• {ref}" + (f" — {f['url']}" if f.get("url") else ""))
    return lineas


def componer(
    slug: str,
    g: dict[str, Any],
    dossier: dict[str, Any],
    tiempos: dict[str, Any],
    cfg: Config,
    con: sqlite3.Connection,
    video_id: int,
    desfase: float = 0.0,
    **kw: Any,
) -> dict[str, Any]:
    tarea = (
        f"Canal: {cfg.canal.nombre} (historia oscura y leyendas hispanas, audiencia de España).\n"
        "Propón 3 títulos distintos (≤ 70 caracteres ideal): uno con número o superlativo, uno con pregunta "
        "o afirmación intrigante, uno con nombre del caso + apodo. Sin clickbait engañoso ni términos gráficos.\n"
        "3 textos de miniatura de 2-4 palabras en mayúsculas.\n"
        f"GUION:\n{texto_completo(g)[:12000]}"
    )
    r = claude_cli.llamar(
        "metadatos",
        tarea,
        ESQUEMA,
        modelo=cfg.modelos["metadatos"],
        max_turnos=cfg.max_turnos.get("metadatos", 3),
        con=con,
        video_id=video_id,
        **kw,
    )
    atribuciones = sorted(
        {
            row["atribucion"]
            for row in con.execute(
                "SELECT atribucion FROM assets WHERE video_id = ? "
                "AND licencia NOT IN ('PD', 'CC0', 'IA-APACHE-2.0')",
                (video_id,),
            )
            if row["atribucion"]
        }
    )
    usa_ia = (
        con.execute(
            "SELECT 1 FROM assets WHERE video_id = ? AND origen LIKE 'ia-%' LIMIT 1", (video_id,)
        ).fetchone()
        is not None
    )
    partes = [r["gancho_descripcion"], ""]
    caps = capitulos_youtube(tiempos["capitulos"], desfase)
    if caps:
        partes += ["Capítulos:", *caps, ""]
    partes += ["Fuentes:", *fuentes_citadas(g, dossier), ""]
    partes += ["Distinguimos entre HECHO documentado, LEYENDA y ESPECULACIÓN a lo largo del relato.", ""]
    if atribuciones:
        partes += ["Créditos de imágenes y música:", *[f"• {a}" for a in atribuciones], ""]
    if usa_ia:
        partes.append("Algunas ilustraciones se han generado con IA en estilo grabado (no son imágenes reales).")
    m = {
        "titulo": r["titulos"][0],
        "titulos": r["titulos"],
        "descripcion": "\n".join(partes).strip()[:4900],
        "etiquetas": r["etiquetas"],
        "textos_miniatura": r["textos_miniatura"],
        "sintetico_realista": False,
        "idioma": cfg.canal.idioma,
    }
    almacen.guardar_json(almacen.media(slug) / "metadatos.json", m)
    almacen.guardar_json(almacen.qa(slug, "metadatos"), m)
    return m
