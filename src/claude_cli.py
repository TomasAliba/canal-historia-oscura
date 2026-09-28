"""Llamadas a Claude mediante `claude -p` (suscripción Pro vía CLAUDE_CODE_OAUTH_TOKEN).

Cada paso creativo es una llamada con: prompt del subagente (.claude/agents/<agente>.md) como
system prompt añadido, tarea por stdin, salida JSON validada con --json-schema, herramientas
mínimas y --permission-mode dontAsk (todo lo no permitido se deniega sin preguntar).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from src.config import raiz
from src.db import registrar_uso
from src.registro import log

_CUOTA = re.compile(r"usage limit|limit reached|rate.?limit|quota|weekly limit|5-hour limit", re.IGNORECASE)


class ErrorClaude(RuntimeError):
    """Fallo de la llamada (salida inválida, error del modelo, límite de turnos)."""


class CuotaAgotada(ErrorClaude):
    """Se agotó la cuota de la suscripción: el pipeline pausa y reanuda en el siguiente run."""


@dataclass
class Resultado:
    datos: dict[str, Any]
    turnos: int
    tokens_entrada: int
    tokens_salida: int


Ejecutor = Callable[[list[str], str], subprocess.CompletedProcess[str]]


def _ejecutar(cmd: list[str], entrada: str) -> subprocess.CompletedProcess[str]:
    # CANAL_PIPELINE=1 desactiva el hook Stop (pytest/ruff), pensado para sesiones de desarrollo.
    return subprocess.run(
        cmd,
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=3600,
        cwd=raiz(),
        env={**os.environ, "CANAL_PIPELINE": "1"},
    )


def prompt_agente(agente: str) -> str:
    """Cuerpo del subagente sin el frontmatter YAML."""
    texto = (raiz() / ".claude" / "agents" / f"{agente}.md").read_text(encoding="utf-8")
    if texto.startswith("---"):
        texto = texto.split("---", 2)[2]
    return texto.strip()


def comando(
    agente: str, esquema: dict[str, Any], modelo: str, max_turnos: int, herramientas: Sequence[str]
) -> list[str]:
    exe = shutil.which("claude") or "claude"
    cmd = [
        exe,
        "-p",
        "--output-format",
        "json",
        "--model",
        modelo,
        "--max-turns",
        str(max_turnos),
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
        "--append-system-prompt",
        prompt_agente(agente),
        "--json-schema",
        json.dumps(esquema, ensure_ascii=False),
    ]
    if herramientas:
        cmd += ["--allowedTools", ",".join(herramientas)]
    return cmd


def _extraer_json(texto: str) -> dict[str, Any]:
    texto = texto.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.S)
    if m:
        texto = m.group(1)
    elif not texto.startswith("{"):
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio < 0 or fin < 0:
            raise ErrorClaude("La respuesta no contiene JSON")
        texto = texto[inicio : fin + 1]
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise ErrorClaude(f"JSON inválido en la respuesta: {e}") from e


def interpretar(salida: str, codigo: int) -> Resultado:
    try:
        d = json.loads(salida)
    except json.JSONDecodeError as e:
        if _CUOTA.search(salida):
            raise CuotaAgotada(salida[:300]) from e
        raise ErrorClaude(f"Salida no JSON (código {codigo}): {salida[:300]}") from e
    mensaje = str(d.get("result", ""))
    if d.get("is_error") or d.get("subtype", "success") != "success":
        if _CUOTA.search(mensaje):
            raise CuotaAgotada(mensaje[:300])
        raise ErrorClaude(f"{d.get('subtype')}: {mensaje[:300]}")
    datos = d.get("structured_output")
    if not isinstance(datos, dict):
        datos = _extraer_json(mensaje)
    uso = d.get("usage") or {}
    entrada = sum(
        int(uso.get(k, 0) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    )
    return Resultado(datos, int(d.get("num_turns", 0) or 0), entrada, int(uso.get("output_tokens", 0) or 0))


def llamar(
    agente: str,
    tarea: str,
    esquema: dict[str, Any],
    *,
    modelo: str,
    max_turnos: int,
    herramientas: Sequence[str] = (),
    con: sqlite3.Connection | None = None,
    video_id: int | None = None,
    ejecutor: Ejecutor | None = None,
    reintentos: int = 3,
    espera_s: float = 30,
) -> dict[str, Any]:
    ejecutar = ejecutor or _ejecutar
    cmd = comando(agente, esquema, modelo, max_turnos, herramientas)
    ultimo: Exception | None = None
    for intento in range(reintentos):
        try:
            proc = ejecutar(cmd, tarea)
            res = interpretar(proc.stdout or proc.stderr or "", proc.returncode)
        except CuotaAgotada:
            raise
        except (ErrorClaude, subprocess.TimeoutExpired) as e:
            ultimo = e
            log("claude_reintento", "warning", agente=agente, intento=intento + 1, error=str(e)[:300])
            if intento + 1 < reintentos:
                time.sleep(espera_s * 2**intento)
            continue
        if con is not None:
            registrar_uso(
                con,
                video_id,
                agente,
                modelo=modelo,
                llamadas=1,
                turnos=res.turnos,
                tokens_entrada=res.tokens_entrada,
                tokens_salida=res.tokens_salida,
            )
        log("claude_ok", agente=agente, modelo=modelo, turnos=res.turnos)
        return res.datos
    raise ErrorClaude(f"{agente}: agotados {reintentos} intentos. Último error: {ultimo}")
