---
description: Produce un vídeo completo con el pipeline de Python (reanuda el que esté a medias).
argument-hint: [slug-opcional]
---
Ejecuta el pipeline determinista; no produzcas el vídeo "a mano".

1. `python -m src.pipeline --tema "$ARGUMENTS"` (si no hay argumento, sin `--tema`: elige el backlog
   o reanuda el vídeo en curso). Añade `--simulado` solo si el usuario pide un ensayo.
2. Lee `data/estado/ultimo_resultado.json` y resume: slug, estado, uso de Claude y motivos.
3. Si el estado es `ERROR`, lee el último fichero de `data/estado/logs/` y explica la causa probable;
   no intentes reparar aquí (eso es /reparar-fallo).

No pidas confirmaciones si estás en modo desatendido.
