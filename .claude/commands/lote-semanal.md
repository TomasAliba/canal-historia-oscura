---
description: Produce el lote semanal respetando los límites de uso de config/canal.yaml.
---
1. Lee `produccion.videos_por_semana` y `uso.max_videos_semana` de `config/canal.yaml`.
2. Repite `python -m src.pipeline` hasta ese número de vídeos, uno tras otro. Detente si
   `ultimo_resultado.json` devuelve `OMITIDO`, `PAUSADO_CUOTA`, `SIN_TEMAS` o `ERROR`.
3. Termina con un resumen JSON del lote: [{slug, estado, uso, motivos}].
