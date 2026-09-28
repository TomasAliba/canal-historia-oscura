---
description: Analiza métricas, repriorizar backlog y propone mejoras en un PR.
---
1. Ejecuta `python -m src.analitica --semana` y delega el análisis en el subagente analista, que
   escribe `docs/informes/<fecha>.md`.
2. Si los datos lo justifican (≥ 4 vídeos publicados), ajusta prioridades en `data/estado/backlog.csv`
   (solo columnas `prioridad` y `notas`).
3. Si hay cambios de plantillas o prompts justificados por datos: crea la rama `mejoras/<fecha>`,
   aplica los cambios, ejecuta `python -m pytest -q` y `ruff check src tests`, y abre un PR
   (`gh pr create`) con el informe. Nunca hagas push a main.
4. Evalúa el modo de veto con `python -m src.decisiones --coincidencia`: si `proponer_pasivo` es true,
   propón el cambio en el informe y por Telegram (no lo apliques).
5. Envía el resumen: `python -m src.notificar --informe docs/informes/<fecha>.md`.
