# CLAUDE.md — El Escribano de Ánimas

## Qué es este proyecto
Sistema autónomo que investiga, escribe, locuta, monta y sube vídeos largos (12-20 min) en español de
España sobre historia oscura, sucesos históricos, leyendas hispanas y misterios.
- Plan por fases: `PROMPT_MAESTRO.md`. Investigación y decisiones: `docs/fase0-informe.md` (§9).
- Arquitectura: `docs/arquitectura.md`. Configuración: `config/canal.yaml`.

## Arquitectura en una línea
`python -m src.pipeline` es una máquina de estados en SQLite (`data/estado/canal.db`). Claude solo
interviene en los pasos creativos mediante `claude -p` (`src/claude_cli.py`), con el prompt de
`.claude/agents/<agente>.md` y salida JSON validada. Todo lo demás es código determinista.

## Reglas de contenido (siempre)
- Sin violencia gráfica ni gore: atmósfera y sugerencia, no sangre.
- Toda afirmación factual con fuente `[F:id]` del dossier. Etiquetas HECHO / LEYENDA / ESPECULACION.
- Solo sucesos de **más de 100 años**; nada de personas vivas identificables ni víctimas infantiles
  como eje del relato.
- Solo assets de dominio público o con licencia comercial, registrando origen y licencia.
- Variar la estructura narrativa (plantillas rotatorias) y respetar el umbral de similitud.

## Reglas técnicas
- Python ≥ 3.12, tipado, `ruff` para formato y lint, `pytest` para tests. Código en `src/`, tests en
  `tests/`. Entorno local: `.venv` (`.venv/Scripts/python -m pytest -q`).
- Estado persistente en `data/estado/` (se sincroniza con la rama `estado` mediante
  `scripts/estado.sh`). Vídeo y audio en `data/media/` (efímeros; nunca versionados).
- Secretos solo en `.env`, `secrets/` y *Actions secrets*. Nunca leerlos, imprimirlos ni commitearlos.
- Pasos idempotentes y reanudables. Un error deja el vídeo en su estado; el siguiente run lo reanuda.
- Los servicios externos tienen versión simulada: los tests nunca llaman a Claude, Google, Cloudflare
  ni YouTube de verdad (`ClaudeFalso` en `tests/conftest.py`, `--simulado` en el pipeline).
- Consultar code.claude.com/docs antes de usar flags o configuración de Claude Code.

## Definición de terminado
- Código: `python -m pytest -q` en verde y `ruff check src tests .claude/hooks` sin errores.
- Vídeo: estado `ESPERANDO_PUBLICACION` con todos los controles superados:
  - verificación 100 %, riesgo de tono ≤ 3, similitud ≤ 0,35;
  - duración 720-1200 s, desfase de subtítulos ≤ 200 ms, fotogramas y licencias correctos;
  - metadatos con fuentes y capítulos, fila en la tabla `uso` y `data/estado/ultimo_resultado.json`.
- Si algo no se completa: queda registrado en `data/estado/logs/` y en la tabla `trabajos`, y se avisa
  por Telegram. Nunca trabajo a medias sin estado.

## Trabajo desatendido
- En headless no hay nadie: no pedir confirmaciones; decidir con estas reglas y registrar.
- Reintentos: hasta `calidad.max_reintentos` regeneraciones; después, DESCARTADO con motivo.
- Límites de uso en `config/canal.yaml → uso`. Cuota de Claude agotada = `PAUSADO_CUOTA` (no es error).
- Nunca hacer push a `main`: ramas `fix/*` o `mejoras/*` y PR.
