"""Logs estructurados (JSON por línea) en data/estado/logs/, con enmascarado de secretos."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

from src.config import dir_estado

_SECRETOS = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS|SA_JSON)", re.IGNORECASE)


def _valores_secretos() -> list[str]:
    return [v for k, v in os.environ.items() if _SECRETOS.search(k) and v and len(v) >= 8]


def enmascarar(texto: str) -> str:
    for v in _valores_secretos():
        texto = texto.replace(v, "***")
    return texto


def log(evento: str, nivel: str = "info", **datos: Any) -> None:
    registro = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "nivel": nivel,
        "evento": evento,
        **datos,
    }
    linea = enmascarar(json.dumps(registro, ensure_ascii=False, default=str))
    carpeta = dir_estado() / "logs"
    carpeta.mkdir(parents=True, exist_ok=True)
    with (carpeta / f"{datetime.now(UTC):%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
        f.write(linea + "\n")
    print(linea, file=sys.stderr)
