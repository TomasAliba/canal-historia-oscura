"""Tests de los hooks (se ejecutan también en el hook Stop). Se invocan con el Python actual,
igual que en Windows y en Linux."""

import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).parents[1] / ".claude" / "hooks"


def ejecutar(tool: str, entrada: dict, hook: str = "bloquear_peligrosos.py") -> int:
    datos = json.dumps({"tool_name": tool, "tool_input": entrada})
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)], input=datos, text=True, capture_output=True
    ).returncode


def test_bloquea_rm_rf():
    assert ejecutar("Bash", {"command": "rm -rf data"}) == 2
    assert ejecutar("Bash", {"command": "rm -fr /"}) == 2


def test_bloquea_leer_env():
    assert ejecutar("Read", {"file_path": "/app/.env"}) == 2
    assert ejecutar("Read", {"file_path": r"C:\proyecto\.env.local"}) == 2
    assert ejecutar("Bash", {"command": "cat .env"}) == 2
    assert ejecutar("Bash", {"command": "source .env && echo hola"}) == 2


def test_bloquea_secrets():
    assert ejecutar("Read", {"file_path": "secrets/token.json"}) == 2
    assert ejecutar("Bash", {"command": "cat secrets/token.json"}) == 2
    assert ejecutar("Grep", {"pattern": "refresh", "path": "secrets"}) == 2
    assert ejecutar("Grep", {"pattern": "KEY", "path": ".env"}) == 2


def test_bloquea_push_forzado_y_a_main():
    assert ejecutar("Bash", {"command": "git push --force origin fix/x"}) == 2
    assert ejecutar("Bash", {"command": "git push -f origin fix/x"}) == 2
    assert ejecutar("Bash", {"command": "git push origin main"}) == 2


def test_bloquea_exponer_entorno():
    assert ejecutar("Bash", {"command": "printenv"}) == 2
    assert ejecutar("Bash", {"command": "env"}) == 2
    assert ejecutar("Bash", {"command": "echo $ANTHROPIC_API_KEY"}) == 2


def test_permite_env_example_venv_y_pipeline():
    assert ejecutar("Bash", {"command": "cp .env.example .env.example.bak"}) == 0
    assert ejecutar("Read", {"file_path": ".env.example"}) == 0
    assert ejecutar("Bash", {"command": "python -m venv .venv"}) == 0
    assert ejecutar("Bash", {"command": "source .venv/bin/activate"}) == 0
    assert ejecutar("Bash", {"command": "python -m src.pipeline --simulado"}) == 0
    assert ejecutar("Bash", {"command": "git push -u origin fix/2026-10-01-tts"}) == 0
    assert ejecutar("Bash", {"command": "set -euo pipefail; ls"}) == 0


def test_permite_codigo_que_menciona_env():
    assert ejecutar("Write", {"file_path": "src/config.py", "content": 'load_dotenv(".env")'}) == 0
    assert ejecutar("Grep", {"pattern": "environ", "path": "src"}) == 0


def test_entrada_invalida_no_bloquea():
    r = subprocess.run(
        [sys.executable, str(HOOKS / "bloquear_peligrosos.py")], input="no es json", text=True, capture_output=True
    )
    assert r.returncode == 0


def test_formatear_ignora_no_python():
    assert ejecutar("Write", {"file_path": "docs/a.md"}, hook="formatear.py") == 0


def test_stop_no_bloquea_si_ya_estaba_activo():
    datos = json.dumps({"stop_hook_active": True})
    r = subprocess.run(
        [sys.executable, str(HOOKS / "verificar_al_terminar.py")], input=datos, text=True, capture_output=True
    )
    assert r.returncode == 0
