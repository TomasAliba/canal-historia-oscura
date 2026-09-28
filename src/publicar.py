"""Publicación en YouTube: subida PRIVADA, miniatura, subtítulos y programación (publishAt).

Uso:
  python -m src.publicar --subir-privado <slug>
  python -m src.publicar --programar <slug>      (tras el veto: próximo día de publicación a la hora fijada)
  python -m src.publicar --hacer-publico <slug>  (inmediato; alternativa manual)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src import almacen, db
from src.config import Config, config
from src.registro import log

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
DIAS = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def proxima_publicacion(cfg: Config, ahora: datetime | None = None, margen_h: float = 2.0) -> datetime:
    """Próximo día de publicación a la hora configurada, con al menos `margen_h` horas de margen."""
    tz = ZoneInfo(cfg.produccion.zona_horaria)
    ahora = (ahora or datetime.now(tz)).astimezone(tz)
    h, m = (int(x) for x in cfg.produccion.hora_publicacion.split(":"))
    dias = {DIAS[d.lower()] for d in cfg.produccion.dias_publicacion}
    for i in range(0, 15):
        dia = (ahora + timedelta(days=i)).replace(hour=h, minute=m, second=0, microsecond=0)
        if dia.weekday() in dias and dia - ahora >= timedelta(hours=margen_h):
            return dia
    raise RuntimeError("No hay días de publicación configurados")


def servicio(api: str = "youtube", version: str = "v3") -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    ruta = os.environ.get("YOUTUBE_TOKEN_FILE", "secrets/token.json")
    cred = Credentials.from_authorized_user_file(ruta, SCOPES)
    if not cred.valid:
        cred.refresh(Request())
    return build(api, version, credentials=cred, cache_discovery=False)


def subir_privado(slug: str, yt: Any | None = None) -> str:
    from googleapiclient.http import MediaFileUpload

    yt = yt or servicio()
    carpeta = almacen.media(slug)
    m = almacen.leer_json(carpeta / "metadatos.json")
    cuerpo = {
        "snippet": {
            "title": m["titulo"],
            "description": m["descripcion"],
            "tags": m["etiquetas"],
            "categoryId": "27",
            "defaultLanguage": m.get("idioma", "es"),
            "defaultAudioLanguage": m.get("idioma", "es"),
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(m.get("sintetico_realista", False)),
        },
    }
    media = MediaFileUpload(
        str(carpeta / "final.mp4"), chunksize=16 * 1024 * 1024, resumable=True, mimetype="video/mp4"
    )
    req = yt.videos().insert(part="snippet,status", body=cuerpo, media_body=media)
    respuesta = None
    while respuesta is None:
        _, respuesta = req.next_chunk(num_retries=5)
    video_id = respuesta["id"]
    miniatura = carpeta / "miniaturas" / "miniatura_1.jpg"
    if miniatura.exists():
        try:
            yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(miniatura))).execute()
        except Exception as e:
            log("miniatura_no_subida", "warning", error=str(e)[:200])
    srt = carpeta / "subtitulos.srt"
    if srt.exists():
        yt.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": "es", "name": "Español"}},
            media_body=MediaFileUpload(str(srt)),
        ).execute()
    return video_id


def programar(slug: str, cfg: Config, yt: Any | None = None, ahora: datetime | None = None) -> str:
    yt = yt or servicio()
    con = db.conectar()
    v = db.video(con, slug)
    if v is None or not v["youtube_id"]:
        raise RuntimeError(f"{slug}: no hay youtube_id registrado")
    cuando = proxima_publicacion(cfg, ahora)
    iso = cuando.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    yt.videos().update(
        part="status",
        body={
            "id": v["youtube_id"],
            "status": {"privacyStatus": "private", "publishAt": iso, "selfDeclaredMadeForKids": False},
        },
    ).execute()
    db.actualizar_video(con, slug, estado="PROGRAMADO", publish_at=iso)
    return iso


def hacer_publico(slug: str, yt: Any | None = None) -> None:
    yt = yt or servicio()
    con = db.conectar()
    v = db.video(con, slug)
    if v is None or not v["youtube_id"]:
        raise RuntimeError(f"{slug}: no hay youtube_id registrado")
    yt.videos().update(
        part="status", body={"id": v["youtube_id"], "status": {"privacyStatus": "public"}}
    ).execute()
    db.actualizar_video(con, slug, estado="PUBLICADO")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--subir-privado", metavar="SLUG")
    g.add_argument("--programar", metavar="SLUG")
    g.add_argument("--hacer-publico", metavar="SLUG")
    a = p.parse_args(argv)
    if a.subir_privado:
        vid = subir_privado(a.subir_privado)
        db.actualizar_video(db.conectar(), a.subir_privado, youtube_id=vid, estado="ESPERANDO_PUBLICACION")
        print(vid)
    elif a.programar:
        print(programar(a.programar, config()))
    else:
        hacer_publico(a.hacer_publico)
    return 0


if __name__ == "__main__":
    sys.exit(main())
