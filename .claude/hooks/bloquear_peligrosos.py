#!/usr/bin/env python
"""PreToolUse: bloquea comandos destructivos y el acceso a secretos (.env, secrets/).

Código de salida 2 = denegar (el mensaje de stderr llega a Claude). Cualquier otro error del hook
NO bloquea, así que este script no debe fallar: ante una entrada rara, deja pasar y lo registra.
"""

from __future__ import annotations

import json
import re
import sys

# Rutas de secretos: .env y .env.<algo> salvo .env.example; cualquier cosa bajo secrets/.
RUTA_SECRETA = re.compile(r"(^|[/\\])(\.env(\.(?!example\b)[\w.-]+)?|secrets[/\\].*)$", re.IGNORECASE)
# En comandos: el token .env (o .env.local…) como palabra, pero no .env.example ni .venv.
ENV_EN_COMANDO = re.compile(r"(^|[\s/\\'\"=<>])\.env(\.(?!example\b)[\w-]+)?(?=$|[\s'\";|&>)])", re.IGNORECASE)

PATRONES_BASH = [
    (r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r|\brm\s+--recursive", "rm recursivo forzado no permitido"),
    (r"git\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)", "push forzado no permitido"),
    (r"git\s+push\b.*\b(origin\s+)?(main|master)\b", "push directo a main no permitido: usa una rama y un PR"),
    (r"git\s+reset\s+--hard", "git reset --hard no permitido"),
    (r"\b(curl|wget)\b[^|]*\|\s*(ba|z)?sh\b", "ejecutar scripts remotos no permitido"),
    (r"\bmkfs\b|\bdd\s+if=|:\(\)\s*\{", "comando destructivo no permitido"),
    (
        r"\bprintenv\b|(^|[;&|]\s*)(env|set)\s*($|[;&|])|\bGet-ChildItem\s+env:",
        "exponer variables de entorno no permitido",
    ),
    (r"echo\s+[\"']?\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)", "exponer secretos no permitido"),
    (r"(^|\s)secrets[/\\]", "acceso a secrets/ no permitido"),
]


def motivo_bloqueo(tool: str, entrada: dict) -> str | None:
    if tool in {"Read", "Edit", "Write", "NotebookEdit"}:
        ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        if RUTA_SECRETA.search(ruta.strip()):
            return "acceso a secretos (.env o secrets/) no permitido"
        return None
    if tool in {"Grep", "Glob"}:
        texto = f"{entrada.get('path', '')} {entrada.get('glob', '')} {entrada.get('pattern', '')}"
        if ENV_EN_COMANDO.search(texto) or re.search(r"(^|[\s/\\])secrets([/\\]|\s|$)", texto):
            return "búsqueda en secretos (.env o secrets/) no permitida"
        return None
    if tool == "Bash":
        comando = str(entrada.get("command", ""))
        if ENV_EN_COMANDO.search(comando):
            return "acceso a .env no permitido"
        for patron, motivo in PATRONES_BASH:
            if re.search(patron, comando, re.IGNORECASE):
                return motivo
    return None


def main() -> int:
    try:
        datos = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    motivo = motivo_bloqueo(str(datos.get("tool_name", "")), datos.get("tool_input") or {})
    if motivo:
        print(f"BLOQUEADO por hook: {motivo}. Busca otra forma.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
