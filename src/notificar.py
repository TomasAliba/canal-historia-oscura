"""Avisos por Telegram. Sin TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID no envía nada (solo registra).

Uso:
  python -m src.notificar --aprobacion <slug> --modo activo --url <run>
  python -m src.notificar --error "mensaje"
  python -m src.notificar --informe docs/informes/2026-10-04.md
  python -m src.notificar --texto "mensaje libre"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

from src.registro import enmascarar, log


def enviar(texto: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    texto = enmascarar(texto)[:4000]
    if not token or not chat:
        log("telegram_sin_configurar", "warning", texto=texto[:200])
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": texto, "disable_web_page_preview": True},
            timeout=20,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log("telegram_error", "warning", error=enmascarar(str(e))[:200])
        return False


def mensaje_aprobacion(slug: str, modo: str, url: str) -> str:
    if modo == "pasivo":
        return (
            f"🕯️ Vídeo listo: {slug}\nSe programará automáticamente en 24 h.\nPara vetarlo, cancela el run: {url}"
        )
    return f"🕯️ Vídeo listo para revisar: {slug}\nEstá subido como PRIVADO. Aprueba o rechaza aquí: {url}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aprobacion", metavar="SLUG")
    p.add_argument("--modo", default="activo")
    p.add_argument("--url", default="")
    p.add_argument("--error")
    p.add_argument("--informe", type=Path)
    p.add_argument("--texto")
    a = p.parse_args(argv)
    if a.aprobacion:
        enviar(mensaje_aprobacion(a.aprobacion, a.modo, a.url))
    elif a.error:
        enviar(f"⚠️ Error en el canal: {a.error}")
    elif a.informe:
        enviar(f"📊 Informe semanal\n\n{a.informe.read_text(encoding='utf-8')[:3500]}")
    elif a.texto:
        enviar(a.texto)
    else:
        p.error("indica --aprobacion, --error, --informe o --texto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
