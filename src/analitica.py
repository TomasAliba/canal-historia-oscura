"""Analítica semanal (YouTube Analytics API) → tabla metricas y resumen JSON para el analista.

Uso: python -m src.analitica --semana   (imprime JSON; requiere secrets/token.json con yt-analytics.readonly)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Any

from src import db
from src.config import config
from src.decisiones import coincidencia


def metricas_video(yta: Any, youtube_id: str, inicio: date, fin: date) -> dict[str, Any]:
    base = {
        "ids": "channel==MINE",
        "startDate": inicio.isoformat(),
        "endDate": fin.isoformat(),
        "filters": f"video=={youtube_id}",
    }
    tot = (
        yta.reports()
        .query(
            metrics="views,estimatedMinutesWatched,averageViewPercentage,averageViewDuration,subscribersGained",
            **base,
        )
        .execute()
    )
    curva = yta.reports().query(metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio", **base).execute()
    trafico = yta.reports().query(metrics="views", dimensions="insightTrafficSourceType", **base).execute()
    cab = [c["name"] for c in tot.get("columnHeaders", [])]
    fila = dict(zip(cab, (tot.get("rows") or [[0] * len(cab)])[0], strict=False))
    return {**fila, "curva": curva.get("rows", []), "trafico": trafico.get("rows", [])}


def semana(dias: int = 28) -> dict[str, Any]:
    from src.publicar import servicio

    yta = servicio("youtubeAnalytics", "v2")
    con = db.conectar()
    fin = date.today() - timedelta(days=1)
    inicio = fin - timedelta(days=dias)
    videos = []
    for v in con.execute(
        "SELECT * FROM videos WHERE estado IN ('PUBLICADO', 'PROGRAMADO') AND youtube_id IS NOT NULL"
    ):
        m = metricas_video(yta, v["youtube_id"], inicio, fin)
        con.execute(
            "INSERT OR REPLACE INTO metricas (video_id, fecha, vistas, retencion_media, retencion_curva, "
            "fuentes_trafico) VALUES (?, ?, ?, ?, ?, ?)",
            (
                v["id"],
                fin.isoformat(),
                m.get("views", 0),
                m.get("averageViewPercentage", 0),
                json.dumps(m["curva"]),
                json.dumps(m["trafico"]),
            ),
        )
        videos.append({"slug": v["slug"], "plantilla": v["plantilla"], **{k: m[k] for k in m if k != "curva"}})
    con.commit()
    usos = [
        dict(r)
        for r in con.execute(
            "SELECT paso, modelo, SUM(llamadas) llamadas, SUM(turnos) turnos, SUM(caracteres_tts) tts, "
            "SUM(imagenes_ia) imagenes FROM uso GROUP BY paso, modelo"
        )
    ]
    # Nota: la API pública no expone impresiones/CTR de miniatura; se revisan en YouTube Studio.
    return {
        "periodo": [inicio.isoformat(), fin.isoformat()],
        "videos": videos,
        "uso": usos,
        "veto": coincidencia(config(), con),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semana", action="store_true")
    p.add_argument("--dias", type=int, default=28)
    a = p.parse_args(argv)
    print(json.dumps(semana(a.dias), ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
