# El Escribano de Ánimas — canal autónomo de historia oscura

Pipeline que investiga, escribe, locuta, monta y sube a YouTube vídeos largos sobre historia oscura
y leyendas hispanas, con coste 0 € (Claude Pro, Google TTS en capa gratuita, dominio público,
GitHub Actions en repositorio público).

## Estructura
```
PROMPT_MAESTRO.md          Plan por fases
CLAUDE.md                  Reglas permanentes y definición de terminado
config/canal.yaml          Canal, formato, calidad, modelos, uso, voz, visuales, veto
src/                       Pipeline (máquina de estados en SQLite; Claude solo en pasos creativos)
tests/                     pytest (incluye un pipeline completo simulado con FFmpeg real)
.claude/agents/            Prompts de investigador, guionista, verificador, filtro-tono, metadatos, qa, analista
.claude/commands/          /nuevo-video, /lote-semanal, /informe-semanal, /reparar-fallo
.claude/hooks/             Bloqueo de comandos peligrosos y secretos, formato, tests al terminar
.github/workflows/         producir.yml (+ veto), informe-semanal.yml, reparar-fallo.yml, tests.yml
scripts/estado.sh          Persistencia de data/estado/ en la rama `estado`
scripts/run_headless.sh    Ejecución desatendida en local
assets/                    Música con licencia y marca (intro/outro)
docs/                      Informe de la Fase 0, arquitectura y guía de configuración
docker/                    Opcional: migración futura a VPS
```

## Uso
```bash
python -m src.pipeline                  # siguiente tema del backlog (o reanuda el vídeo a medias)
python -m src.pipeline --simulado       # ensayo: voz e imágenes simuladas, sin subir
python -m src.pipeline --tema romasanta-hombre-lobo-allariz --hasta TONO_OK
python -m src.uso --check               # ¿quedan cupos esta semana?
python -m src.publicar --programar <slug>
python -m pytest -q && ruff check src tests .claude/hooks
```

## Puesta en marcha
Sigue `docs/configurar-github.md` (repositorio público, secrets, Google Cloud, Cloudflare, Telegram
y Environments).

## Veto
- `activo`: el job `aprobar` espera tu aprobación en GitHub (web o app móvil); al aprobar, el vídeo
  se programa para el próximo día de publicación a las 19:00 (Europe/Madrid).
- `pasivo`: se programa solo a las 24 h salvo que canceles el run.

El informe semanal propone el cambio a `pasivo` cuando los controles coinciden contigo en más del
90 % de al menos 10 vídeos.
