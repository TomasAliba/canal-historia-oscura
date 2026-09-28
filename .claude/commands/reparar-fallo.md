---
description: Diagnostica y repara el último trabajo fallido del pipeline mediante un PR.
argument-hint: [slug-opcional]
---
1. Localiza el fallo: "$ARGUMENTS" o el último trabajo con estado `ERROR` en la tabla `trabajos` de
   `data/estado/canal.db` (`python -c` con sqlite3). Si no hay ninguno (p. ej., el run falló por un
   rechazo del veto o por cuota), termina sin hacer nada.
2. Lee el error de la tabla y los logs de `data/estado/logs/`. Reproduce el fallo con un test en
   `tests/` que lo capture (usa los simulados: `--simulado`, ejecutor falso de Claude).
3. Crea la rama `fix/<fecha>-<slug>`, corrige la causa en `src/`, ejecuta `python -m pytest -q` y
   `ruff check src tests`.
4. Abre un PR (`gh pr create`) con el diagnóstico. No hagas push a main.
5. Si el arreglo requiere reintentar, deja el vídeo en su estado (el pipeline reanuda solo) y notifica
   con `python -m src.notificar --texto "..."` incluyendo el enlace al PR.
6. Si no puedes repararlo, marca el vídeo como `BLOQUEADO` en `videos` y notifica el diagnóstico.
