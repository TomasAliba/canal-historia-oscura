#!/usr/bin/env bash
# Ejecución desatendida en local.
#   scripts/run_headless.sh                 → produce un vídeo con el pipeline de Python
#   scripts/run_headless.sh --simulado      → ensayo sin TTS/IA reales ni subida
#   scripts/run_headless.sh "/informe-semanal"   → comando de Claude Code en headless
# Requiere Claude Code >= 2.1.259 (--permission-prompts). Flags: code.claude.com/docs/en/headless
set -euo pipefail
cd "$(dirname "$0")/.."
PY=python
[[ -x .venv/Scripts/python.exe ]] && PY=.venv/Scripts/python.exe
[[ -x .venv/bin/python ]] && PY=.venv/bin/python
mkdir -p data/estado/logs
TAREA="${1:-}"
if [[ "$TAREA" == /* ]]; then
  LOG="data/estado/logs/$(date +%Y%m%d-%H%M%S)-$(echo "$TAREA" | tr -dc 'a-z-').json"
  claude -p "$TAREA" --permission-mode dontAsk --permission-prompts none --output-format json \
    > "$LOG" 2>&1 || ESTADO=$?
else
  "$PY" -m src.pipeline "$@" || ESTADO=$?
fi
ESTADO=${ESTADO:-0}
if [[ $ESTADO -ne 0 ]]; then
  "$PY" -m src.notificar --error "Tarea ${TAREA:-pipeline} falló (código $ESTADO)" || true
fi
exit $ESTADO
