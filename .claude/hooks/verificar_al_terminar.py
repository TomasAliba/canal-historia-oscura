#!/usr/bin/env python
"""Stop: impide dar la tarea por terminada si fallan pytest o ruff.

Código 2 = bloquear el cierre; Claude recibe stderr y sigue trabajando. Si el hook ya bloqueó una vez
en este ciclo (stop_hook_active), deja terminar para evitar bucles.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from _entorno import RAIZ, python_proyecto


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        datos = {}
    # En las llamadas `claude -p` del pipeline no se valida el repositorio (solo generan JSON).
    if datos.get("stop_hook_active") or os.environ.get("CANAL_PIPELINE") == "1":
        return 0
    py = python_proyecto()
    if any((RAIZ / "tests").glob("test_*.py")):
        r = subprocess.run(
            [py, "-m", "pytest", "-q", "-x"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            print("Tests fallando; corrígelos antes de terminar:", file=sys.stderr)
            print("\n".join(r.stdout.splitlines()[-30:]), file=sys.stderr)
            return 2
    r = subprocess.run([py, "-m", "ruff", "check", "src", "tests", "-q"], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode not in (0, 1) or (r.returncode == 1 and r.stdout.strip()):
        print("ruff check con errores; corrígelos antes de terminar:", file=sys.stderr)
        print(r.stdout[-2000:], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
