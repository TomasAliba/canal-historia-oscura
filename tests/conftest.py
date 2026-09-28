"""Fixtures: cada test trabaja en un proyecto temporal (CANAL_RAIZ) con config, agentes y backlog."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from src import config as config_mod

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def proyecto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(RAIZ / "config" / "canal.yaml", tmp_path / "config" / "canal.yaml")
    shutil.copytree(RAIZ / ".claude" / "agents", tmp_path / ".claude" / "agents")
    estado = tmp_path / "data" / "estado"
    estado.mkdir(parents=True)
    backlog = RAIZ / "data" / "estado" / "backlog.csv"
    if backlog.exists():
        shutil.copy(backlog, estado / "backlog.csv")
    monkeypatch.setenv("CANAL_RAIZ", str(tmp_path))
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "CLOUDFLARE_API_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    config_mod.config.cache_clear()
    yield tmp_path
    config_mod.config.cache_clear()


def ajustar_config(raiz: Path, **cambios: Any) -> None:
    """Modifica config/canal.yaml del proyecto temporal. Claves con punto: 'formato.fps'."""
    ruta = raiz / "config" / "canal.yaml"
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    for clave, valor in cambios.items():
        nodo = datos
        partes = clave.split(".")
        for p in partes[:-1]:
            nodo = nodo.setdefault(p, {})
        nodo[partes[-1]] = valor
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    config_mod.config.cache_clear()


def salida_claude(datos: dict[str, Any], turnos: int = 2) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "",
            "structured_output": datos,
            "num_turns": turnos,
            "usage": {"input_tokens": 1000, "output_tokens": 500},
        }
    )


class ClaudeFalso:
    """Sustituye a `claude -p`: responde según el agente (leído del system prompt añadido)."""

    def __init__(self, respuestas: dict[str, Any]) -> None:
        self.respuestas = respuestas
        self.llamadas: list[tuple[str, str]] = []

    def agente(self, cmd: list[str]) -> str:
        prompt = cmd[cmd.index("--append-system-prompt") + 1]
        for nombre, marca in [
            ("investigador", "investigador histórico"),
            ("guionista", "guionista"),
            ("verificador", "verificador de hechos"),
            ("filtro-tono", "apto para anunciantes"),
            ("metadatos", "empaquetado"),
            ("qa", "fotogramas"),
        ]:
            if marca in prompt:
                return nombre
        raise AssertionError("agente desconocido")

    def __call__(self, cmd: list[str], entrada: str) -> subprocess.CompletedProcess[str]:
        nombre = self.agente(cmd)
        self.llamadas.append((nombre, entrada))
        r = self.respuestas[nombre]
        datos = r(entrada) if callable(r) else r
        return subprocess.CompletedProcess(cmd, 0, stdout=salida_claude(datos), stderr="")
