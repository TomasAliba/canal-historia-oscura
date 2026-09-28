"""Ideación: elige el siguiente tema del backlog según prioridad, calendario y variedad."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from src.config import Config, dir_estado

ESTADOS_ELEGIBLES = {"PENDIENTE", "PENDIENTE_REINTENTO"}


def ruta_backlog() -> Path:
    return dir_estado() / "backlog.csv"


def leer_backlog(ruta: Path | None = None) -> list[dict[str, str]]:
    with (ruta or ruta_backlog()).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def escribir_backlog(filas: list[dict[str, str]], ruta: Path | None = None) -> None:
    if not filas:
        return
    with (ruta or ruta_backlog()).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def marcar_tema(slug: str, estado: str, motivo: str = "") -> None:
    filas = leer_backlog()
    for f in filas:
        if f["slug"] == slug:
            f["estado"] = estado
            if motivo:
                f["notas"] = f"{motivo} | {f.get('notas', '')}".strip(" |")
    escribir_backlog(filas)


def domingo_de_pascua(anio: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher (calendario gregoriano)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lz = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lz) // 451
    mes = (h + lz - 7 * m + 114) // 31
    dia = (h + lz - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def fecha_evento(nombre: str, cfg: Config, hoy: date) -> date | None:
    valor = cfg.calendario.get(nombre)
    if not valor:
        return None
    for anio in (hoy.year, hoy.year + 1):
        if valor == "movil":
            f = domingo_de_pascua(anio) - timedelta(days=3)  # Jueves Santo
        else:
            mes, dia = (int(x) for x in str(valor).split("-"))
            f = date(anio, mes, dia)
        if f >= hoy:
            return f
    return None


def bonus_calendario(evento: str, cfg: Config, hoy: date) -> float:
    if not evento:
        return 0.0
    f = fecha_evento(evento, cfg, hoy)
    ventana = int(cfg.calendario.get("ventana_dias", 21))
    if f and 0 <= (f - hoy).days <= ventana:
        return 2.0
    return 0.0


def puntuar(fila: dict[str, str], cfg: Config, hoy: date, ultimo_pais: str | None) -> float:
    p = float(fila.get("prioridad") or 0) + bonus_calendario(fila.get("calendario", ""), cfg, hoy)
    if ultimo_pais and fila.get("pais") == ultimo_pais:
        p -= 0.5
    return p


def elegir(cfg: Config, con: sqlite3.Connection, hoy: date | None = None) -> dict[str, str] | None:
    hoy = hoy or date.today()
    usados = {r["slug"] for r in con.execute("SELECT slug FROM videos")}
    ultimo = con.execute("SELECT slug FROM videos ORDER BY id DESC LIMIT 1").fetchone()
    filas = leer_backlog()
    pais_de = {f["slug"]: f.get("pais") for f in filas}
    ultimo_pais = pais_de.get(ultimo["slug"]) if ultimo else None
    minimo = cfg.contenido.antiguedad_minima_anios
    candidatos = [
        f
        for f in filas
        if f.get("estado") in ESTADOS_ELEGIBLES
        and f["slug"] not in usados
        and int(f.get("antiguedad_anios") or 0) >= minimo
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda f: puntuar(f, cfg, hoy, ultimo_pais))


def elegir_plantilla(cfg: Config, con: sqlite3.Connection, sugerida: str = "") -> str:
    n = cfg.formato.rotacion_ultimos_n
    recientes = [
        r["plantilla"] for r in con.execute("SELECT plantilla FROM videos ORDER BY id DESC LIMIT ?", (n,))
    ]
    plantillas = cfg.formato.plantillas
    if sugerida in plantillas and sugerida not in recientes:
        return sugerida
    libres = [p for p in plantillas if p not in recientes]
    if libres:
        return libres[0]
    # Todas usadas recientemente: la que lleve más tiempo sin usarse.
    return max(plantillas, key=lambda p: recientes.index(p) if p in recientes else len(recientes))
