"""Visuales: una imagen por escena. Primero dominio público (Wikimedia Commons), después IA estilizada
(FLUX.1 schnell en Cloudflare Workers AI). Cada asset queda registrado con origen y licencia."""

from __future__ import annotations

import base64
import io
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Protocol

import requests
from PIL import Image, ImageDraw

from src import almacen
from src.config import Config
from src.db import registrar_uso
from src.registro import log

COMMONS = "https://commons.wikimedia.org/w/api.php"
# Política de Wikimedia: User-Agent identificable con forma de contacto (CANAL_CONTACTO: URL o email).
UA = {
    "User-Agent": "ElEscribanoDeAnimas/0.1 "
    f"({os.environ.get('CANAL_CONTACTO', 'https://github.com/ElEscribanoDeAnimas')}) python-requests"
}
ANCHO_MINIATURA = 1920  # tamaño estándar de miniatura de Commons (los no estándar se limitan con 429)


def _get(url: str, intentos: int = 4, **kw: Any) -> requests.Response:
    """GET con reintentos ante 429/5xx respetando Retry-After."""
    for i in range(intentos):
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code != 429 and r.status_code < 500:
            r.raise_for_status()
            return r
        espera = float(r.headers.get("Retry-After", 0) or 0) or 2.0 * 2**i
        log("visual_reintento", "warning", codigo=r.status_code, espera_s=espera)
        time.sleep(min(espera, 60))
    r.raise_for_status()
    return r


def normalizar_licencia(corta: str) -> str | None:
    """Traduce LicenseShortName de Commons a PD / CC0 / CC-BY / CC-BY-SA. None = no permitida."""
    c = corta.lower().replace("-", " ")
    if re.search(r"\bnc\b|\bnd\b|non.?commercial|fair use|gfdl", c):
        return None
    if "cc0" in c:
        return "CC0"
    if "public domain" in c or c.startswith("pd") or "dominio público" in c:
        return "PD"
    if "cc by sa" in c:
        return "CC-BY-SA"
    if "cc by" in c:
        return "CC-BY"
    return None


class Imagen(dict):
    """{ruta, origen, url, autor, licencia, atribucion}"""


class Proveedor(Protocol):
    def obtener(self, consulta: str, visual: str, destino: Path) -> Imagen | None: ...


class Commons:
    def __init__(self, permitidas: list[str]) -> None:
        self.permitidas = set(permitidas)
        self.usadas: set[str] = set()

    def obtener(self, consulta: str, visual: str, destino: Path) -> Imagen | None:
        if not consulta.strip():
            return None
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrsearch": f"{consulta} filetype:bitmap",
            "gsrlimit": 15,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": ANCHO_MINIATURA,
        }
        r = _get(COMMONS, params=params)
        paginas = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        for p in paginas:
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            lic = normalizar_licencia((meta.get("LicenseShortName") or {}).get("value", ""))
            url = ii.get("thumburl") or ii.get("url")
            if (
                not lic
                or lic not in self.permitidas
                or ii.get("width", 0) < 800
                or url in self.usadas
                or ii.get("mime") not in ("image/jpeg", "image/png")
            ):
                continue
            datos = _get(url)
            time.sleep(1.0)  # ritmo amable con upload.wikimedia.org
            Image.open(io.BytesIO(datos.content)).convert("RGB").save(destino, "JPEG", quality=92)
            self.usadas.add(url)
            autor = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip() or "desconocido"
            return Imagen(
                ruta=str(destino),
                origen="wikimedia",
                url=ii.get("descriptionurl", url),
                autor=autor,
                licencia=lic,
                atribucion=f"{p.get('title', '')} — {autor} ({lic}), Wikimedia Commons",
            )
        return None


class CloudflareFlux:
    def __init__(self, cfg: Config) -> None:
        ia = cfg.visuales.get("ia", {})
        self.modelo = ia.get("modelo", "@cf/black-forest-labs/flux-1-schnell")
        self.estilo = ia.get("estilo", "")
        self.cuenta = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        self.token = os.environ["CLOUDFLARE_API_TOKEN"]

    def obtener(self, consulta: str, visual: str, destino: Path) -> Imagen | None:
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.cuenta}/ai/run/{self.modelo}"
        prompt = f"{visual}. Estilo: {self.estilo}. Sin texto, sin fotorrealismo, sin sangre."
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"prompt": prompt[:2000], "steps": 4},
            timeout=120,
        )
        r.raise_for_status()
        destino.write_bytes(base64.b64decode(r.json()["result"]["image"]))
        return Imagen(
            ruta=str(destino),
            origen="ia-flux",
            url="",
            autor="IA (FLUX.1 schnell)",
            licencia="IA-APACHE-2.0",
            atribucion="Ilustración generada con IA (FLUX.1 schnell)",
        )


class Simulado:
    """Degradado con el número de escena. Para tests y ensayos sin red."""

    def __init__(self) -> None:
        self.n = 0

    def obtener(self, consulta: str, visual: str, destino: Path) -> Imagen | None:
        self.n += 1
        img = Image.new("RGB", (1600, 1000), (40 + self.n * 7 % 120, 30, 25))
        ImageDraw.Draw(img).text((60, 60), f"escena {self.n}: {consulta[:40]}", fill=(220, 210, 190))
        img.save(destino, "JPEG", quality=90)
        return Imagen(
            ruta=str(destino),
            origen="simulado",
            url="",
            autor="pipeline",
            licencia="CC0",
            atribucion="imagen de prueba",
        )


def conseguir(
    slug: str,
    tiempos: dict[str, Any],
    cfg: Config,
    con: sqlite3.Connection,
    video_id: int,
    publicos: Proveedor,
    ia: Proveedor | None,
    max_ia: int,
) -> list[Imagen]:
    carpeta = almacen.media(slug) / "img"
    carpeta.mkdir(parents=True, exist_ok=True)
    con.execute("DELETE FROM assets WHERE video_id = ? AND tipo = 'imagen'", (video_id,))
    imagenes: list[Imagen] = []
    n_ia = 0
    for i, esc in enumerate(tiempos["escenas"]):
        destino = carpeta / f"escena_{i:03}.jpg"
        img = None
        try:
            img = publicos.obtener(esc.get("busqueda", ""), esc.get("visual", ""), destino)
        except requests.RequestException as e:
            log("visual_error_publico", "warning", escena=i, error=str(e)[:200])
        if img is None and ia is not None and n_ia < max_ia and esc.get("visual"):
            try:
                img = ia.obtener(esc.get("busqueda", ""), esc["visual"], destino)
                n_ia += 1
            except (requests.RequestException, KeyError) as e:
                log("visual_error_ia", "warning", escena=i, error=str(e)[:200])
        if img is None:
            if not imagenes:
                raise RuntimeError("No se consiguió ninguna imagen para la primera escena")
            img = Imagen(imagenes[-1])  # se reutiliza la anterior con otro encuadre (Ken Burns)
        imagenes.append(img)
        con.execute(
            "INSERT INTO assets (video_id, escena, tipo, origen, url, ruta, autor, licencia, atribucion, hash) "
            "VALUES (?, ?, 'imagen', ?, ?, ?, ?, ?, ?, ?)",
            (
                video_id,
                i,
                img["origen"],
                img["url"],
                img["ruta"],
                img["autor"],
                img["licencia"],
                img["atribucion"],
                almacen.huella(img["ruta"]),
            ),
        )
    con.commit()
    if n_ia:
        registrar_uso(con, video_id, "visuales", modelo="flux-1-schnell", imagenes_ia=n_ia)
    return imagenes
