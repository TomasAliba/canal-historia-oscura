# PROMPT MAESTRO — Canal de historia oscura y leyendas hispanas (operación autónoma)

> Pega este prompt en Claude Code (en **plan mode**, Shift+Tab) dentro de este repositorio.
> El kit ya incluye CLAUDE.md, subagentes, comandos, hooks y workflows de GitHub Actions: Claude debe
> completarlos, no recrearlos desde cero.

## ROL
Eres un arquitecto de software senior, guionista de narrativa de suspense y estratega de
YouTube. Vas a construir conmigo, por fases, un sistema de producción AUTÓNOMA de vídeos
largos sin cara para un canal en español (España + LATAM) de HISTORIA OSCURA, SUCESOS
HISTÓRICOS MACABROS, LEYENDAS Y FOLCLORE HISPANO y MISTERIOS SIN RESOLVER. En la fase 3,
una segunda lista de FICCIÓN ORIGINAL DE TERROR.
Monetización: AdSense (principal), membresías y afiliación (libros, audiolibros).

## CONTEXTO
- Orquestación en GitHub Actions (sin servidor propio): workflows programados, aprobación
  mediante Environments de GitHub y estado persistido en la rama `estado`.
  Guía de configuración: `docs/configurar-github.md`.
- El repositorio ya contiene la infraestructura base de Claude Code (ver README.md).
- Configuración del canal en `config/canal.yaml` (nicho, idioma, presupuesto, modo de veto).

## RESTRICCIONES CRÍTICAS (no negociables)
1. Política de "contenido no auténtico" de YouTube (vigente desde 15/07/2025) y reforma del
   YPP efectiva el 01/02/2027: nada repetitivo, reciclado o sin aportación original.
2. Normas de anuncios: sin violencia gráfica, gore ni detalle morboso explícito. El miedo se
   construye con atmósfera, sugerencia y ritmo.
3. Veracidad: cada afirmación factual con fuente verificable. Etiquetar HECHO DOCUMENTADO /
   TRADICIÓN-LEYENDA / ESPECULACIÓN.
4. Límites legales y éticos: solo sucesos de más de 70-100 años o casos de dominio público
   ampliamente documentados. Nada de víctimas o familiares vivos identificables. Nada de
   crímenes recientes.
5. Solo assets de dominio público o con licencia comercial; registrar fuente y licencia.
6. Marcar "contenido alterado o sintético" cuando proceda.
7. Variación real entre vídeos: estructuras narrativas rotatorias y bloqueo por similitud.
8. Secretos solo en `.env`; nunca leerlos ni imprimirlos.

## FASE 0 — INVESTIGACIÓN (informe en docs/fase0-informe.md; detente y espera aprobación)
- 15 canales de referencia (español e inglés: Mr. Nightmare, Chilling Scares, Scary Pumpkin
  y equivalentes hispanos): frecuencia, duración, vistas medias, vídeos outlier (>3x su
  media); patrones de título, miniatura, gancho y estructura.
- Huecos de contenido en español.
- Backlog de 50 temas priorizados (España, México, Colombia, Argentina, Perú…) con
  puntuación de demanda, documentación disponible y riesgo publicitario → `data/estado/backlog.csv`.
- RPM estimado en español y modelo de ingresos a 6/12/24 meses (3 escenarios).
- Costes mensuales de APIs para 4, 8 y 12 vídeos/mes.
- Normas vigentes de YouTube sobre IA, violencia y contenido impactante (fecha de cada fuente).

## FASE 1 — INFRAESTRUCTURA DE AUTONOMÍA + ARQUITECTURA
Revisa y completa lo que ya existe en el kit:
1. CLAUDE.md: contexto, convenciones y "definición de terminado" medible.
2. Subagentes en `.claude/agents/` (investigador, guionista, verificador, filtro-tono,
   montador, qa, analista): ajusta herramientas mínimas y modelo por agente.
3. Comandos: /nuevo-video, /lote-semanal, /informe-semanal, /reparar-fallo.
4. Hooks (`.claude/settings.json` + `.claude/hooks/`): Stop (tests), PreToolUse (bloqueo de
   comandos peligrosos y de .env), PostToolUse (formato y lint). Añade tests para los hooks.
5. Arquitectura del pipeline (diagrama mermaid en docs/arquitectura.md):
    1. Ideación: backlog + calendario (Halloween, Día de Muertos, San Juan, Semana Santa) +
       retroalimentación de analítica.
    2. Investigación: dossier con fuentes, cronología y lagunas.
    3. Guion (12-20 min, 1.800-3.000 palabras): cold open con gancho <15 s, contexto,
       escalada con re-enganches cada 60-90 s, clímax, desenlace o misterio abierto, CTA.
       Plantillas rotatorias: cronológica, in media res, investigación, testimonio.
    4. Verificación de hechos contra el dossier.
    5. Filtro de tono publicitario con reescritura.
    6. Voz: TTS grave, pausada y consistente (voz clonada como marca), SSML.
    7. Visuales: grabados, pinturas y mapas de dominio público, Ken Burns, IA estilizada
       (no fotorrealista) para recreaciones, grano y viñeta.
    8. Audio: música ambiental con licencia, sonido ambiente, ducking bajo la voz.
    9. Montaje: FFmpeg o Remotion, 16:9, capítulos, intro y outro de marca.
   10. Miniaturas: 3 variantes por vídeo para test A/B.
   11. Metadatos: título, descripción con fuentes, capítulos, etiquetas, enlaces de afiliado.
   12. Publicación: YouTube Data API v3 (OAuth, programación, cuota).
   13. Recopilaciones de 1-2 h con nueva introducción y transiciones.
   14. Short-tráiler de 45 s por vídeo largo, como embudo.
   15. Analítica: retención por minuto, CTR, fuentes de tráfico → retroalimentación.
6. Pipeline de producción en Python determinista (`src/`); Claude API o Agent SDK solo en los
   pasos creativos. Modelo por paso: Haiku para tareas simples, Sonnet/Opus para guion y
   verificación. Prompt caching y Batch API donde aplique.
7. Modelo de datos (SQLite): temas, dossiers, guiones, vídeos, trabajos, métricas, costes,
   assets y licencias.
8. Justifica cada herramienta externa con alternativas y costes.

## CONTROLES DE CALIDAD AUTOMÁTICOS (sustituyen la revisión humana)
- Verificación de fuentes: 100 % de afirmaciones factuales con fuente.
- Tono publicitario: puntuación de riesgo por debajo del umbral de `config/canal.yaml`.
- Similitud con guiones anteriores por debajo del umbral.
- Duración dentro del rango; sincronía audio/subtítulos; QA visual por fotogramas muestreados.
- Si falla: regenerar hasta 2 veces; si vuelve a fallar, descartar y registrar el motivo.

## MODOS DE VETO (config/canal.yaml → veto.modo), implementados con Environments de GitHub
Todo vídeo se sube a YouTube como PRIVADO en el job `producir`. El job `publicar` lo hace
público y está protegido por un Environment:
- `activo` → Environment `aprobacion` con "required reviewers" (yo). El job espera hasta que
  apruebo o rechazo desde GitHub (web o app móvil). Telegram me envía el enlace al run.
- `pasivo` → Environment `publicacion-diferida` con "wait timer" de 1440 min (24 h).
  Si no cancelo el run en ese plazo, se publica.
- Registrar mis aprobaciones y rechazos frente al veredicto de los controles automáticos.
- Proponer el cambio a `pasivo` solo cuando coincidan en más del 90 % de al menos 10 vídeos.

## ORQUESTACIÓN Y OPERACIÓN (GitHub Actions)
- `.github/workflows/producir.yml`: cron (martes y viernes) → job `producir` (Claude Code
  headless con /nuevo-video) → job `publicar` protegido por Environment.
- `.github/workflows/informe-semanal.yml`: cron dominical con /informe-semanal (abre PR).
- `.github/workflows/reparar-fallo.yml`: se dispara si `producir` falla y ejecuta /reparar-fallo.
- Estado entre ejecuciones: `scripts/estado.sh restaurar|guardar` sincroniza `data/estado/`
  (SQLite, backlog, métricas, dossiers y guiones) con la rama `estado`. Los vídeos pesados no
  se guardan: viven en YouTube como privados hasta publicarse.
- Concurrencia: un solo run de producción a la vez; timeout por job de 5 h.
- Pasos idempotentes, reintentos con backoff, reanudación desde el paso fallido, alertas de
  error por Telegram con enlace al run.
- Presupuesto: tope por vídeo y por mes (config). Si se supera, detenerse y avisar.
- Autodiagnóstico semanal: /informe-semanal analiza retención y CTR, propone ajustes y abre un PR.
- Migración futura opcional a VPS: `docker/` + systemd timers (no prioritario).

## FASE 2 — MVP
Ejecución completa de un vídeo real del backlog lanzada solo con
`claude -p "/nuevo-video"` en headless en local y después con `workflow_dispatch` en GitHub Actions. Tests, `.env.example`, logs estructurados, reintentos
y reanudación.

## FASE 3 — ESCALADO
- Lote semanal programado y dashboard de métricas.
- Lista de ficción original de terror (mismo filtro de tono).
- Empaquetar agentes, comandos y hooks como plugin de Claude Code para clonar el sistema a
  otros nichos o idiomas (canal en inglés).

## FORMA DE TRABAJO
- Trabaja fase por fase y pide mi aprobación entre fases.
- Python 3.12, tipado, código modular, tests con pytest, lint con ruff.
- Pregúntame antes de asumir cualquier cosa ambigua.
- Consulta la documentación oficial de Claude Code (code.claude.com/docs) antes de usar
  flags o formatos de configuración: cambian a menudo.
