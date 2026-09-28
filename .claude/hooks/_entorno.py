"""Localiza el Python del proyecto (.venv si existe) para ejecutar ruff y pytest desde los hooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def python_proyecto() -> str:
    for candidato in (RAIZ / ".venv" / "Scripts" / "python.exe", RAIZ / ".venv" / "bin" / "python"):
        if candidato.exists():
            return str(candidato)
    return sys.executable
