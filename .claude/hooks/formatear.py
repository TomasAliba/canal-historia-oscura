#!/usr/bin/env python
"""PostToolUse (Edit|Write): formatea y corrige con ruff el fichero Python editado. Nunca bloquea."""

from __future__ import annotations

import json
import subprocess
import sys

from _entorno import RAIZ, python_proyecto


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    ruta = str((datos.get("tool_input") or {}).get("file_path", ""))
    if not ruta.endswith(".py"):
        return 0
    py = python_proyecto()
    for args in (["format", ruta], ["check", "--fix", "--quiet", ruta]):
        subprocess.run([py, "-m", "ruff", *args], cwd=RAIZ, capture_output=True, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
