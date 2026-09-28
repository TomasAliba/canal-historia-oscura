#!/usr/bin/env bash
# Persiste el estado del canal (data/estado/) en la rama `estado` entre ejecuciones de
# GitHub Actions. Uso: scripts/estado.sh restaurar | guardar
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=data/estado
RAMA=estado

existe_remota() { git ls-remote --exit-code --heads origin "$RAMA" >/dev/null 2>&1; }

restaurar() {
  mkdir -p "$DIR"
  if existe_remota; then
    git fetch -q origin "$RAMA"
    git archive "origin/$RAMA" | tar -x -C "$DIR"
    echo "Estado restaurado desde la rama $RAMA."
  else
    echo "Sin rama $RAMA todavía: se empieza con estado vacío."
  fi
}

guardar() {
  mkdir -p "$DIR"
  WT=$(mktemp -d)
  if existe_remota; then
    git fetch -q origin "$RAMA"
    git worktree add -q -B "$RAMA" "$WT" "origin/$RAMA"
  else
    git worktree add -q --detach "$WT"
    git -C "$WT" checkout -q --orphan "$RAMA"
    git -C "$WT" rm -rqf . >/dev/null 2>&1 || true
  fi
  find "$WT" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cp -a "$DIR"/. "$WT"/
  git -C "$WT" add -A
  if git -C "$WT" -c user.name="canal-bot" -c user.email="canal-bot@users.noreply.github.com" \
       commit -qm "estado: $(date -u +%Y-%m-%dT%H:%MZ)" >/dev/null; then
    git -C "$WT" push -q origin "$RAMA"
    echo "Estado guardado en la rama $RAMA."
  else
    echo "Sin cambios de estado."
  fi
  git worktree remove --force "$WT"
}

case "${1:-}" in
  restaurar) restaurar ;;
  guardar) guardar ;;
  *) echo "Uso: $0 restaurar|guardar" >&2; exit 1 ;;
esac
