# Fase 0 — Informe de investigación

Fecha: 28/09/2026 · Estado: **pendiente de aprobación** · Backlog: `data/estado/backlog.csv`
Datos brutos: `docs/fase0-datos/` (canales, búsquedas de YouTube, visitas de Wikipedia).

## 0. Resumen ejecutivo

1. **El hueco existe.** Los grandes canales en español de "miedo" hacen misterios de internet,
   casos modernos o relatos paranormales de suscriptores (Dross, BreakMan, MundoCreepy,
   Relatos de la Noche). La **historia oscura hispánica documentada y con fuentes, anterior a
   1926**, apenas tiene competencia: el único canal de nicho que encontramos (España Negra) es
   diminuto y se dedica a crímenes recientes.
2. **El formato largo funciona**: la mediana de duración de los referentes es de 25-50 min y
   MundoCreepy (7 casos por país, 45-60 min) roza el millón de vistas por vídeo. 12-20 min es
   un formato conservador; conviene probar 20-30 min más adelante.
3. **Cambio crítico del YPP**: desde el **01/02/2027** un canal nuevo necesita **8.000 horas**
   (antes 4.000) y 1.000 suscriptores. Solo el escenario optimista entra antes de esa fecha.
   En el escenario base entraríamos hacia el **mes 7**; en el pesimista, hacia el **mes 13**.
4. **El presupuesto de `config/canal.yaml` (60 €/mes) no cubre 8 vídeos/mes** con voz
   ElevenLabs de calidad y Claude Code de orquestador: el coste estimado es de 65-150 €/mes
   según las opciones elegidas (§6). **Actualización del 28/09**: la decisión es coste 0 €;
   hay un plan viable en §10.
5. **Bloqueante técnico**: los Environments de GitHub con *required reviewers* o *wait timer*
   **solo funcionan en repositorios públicos** en los planes Free, Pro y Team. **Resuelto**:
   el repositorio será público (§9).

## 1. Metodología y límites

- **Canales**: lectura de la página pública `/videos` de cada canal el 28/09/2026 (sin API).
  Se toman los ~30 últimos vídeos largos. La mediana de vistas **excluye los vídeos con menos
  de 14 días**, porque aún no han madurado. La frecuencia es aproximada: YouTube redondea la
  antigüedad ("hace 1 mes").
  - **Outlier**: un vídeo con más de 3 veces la mediana del canal.
  - Limitación: solo se ven los últimos ~30 vídeos. Los outliers históricos quedan fuera,
    salvo en canales que publican poco.
- **Demanda de temas** (dos señales medidas):
  - Visitas del artículo en es.wikipedia entre sep-2025 y ago-2026 (API de Wikimedia).
  - Búsqueda pública de YouTube (`hl=es`, `gl=ES`): vistas de los 20 primeros resultados.
    Se registran la mediana y el número de vídeos con 100.000 vistas o más, que usamos como
    indicador de **saturación**.
  - Limitación: una biografía general (Carlos II, Juana I) infla las visitas de Wikipedia
    frente al ángulo "oscuro". La búsqueda de YouTube mezcla resultados poco relacionados.
- **Documentación, riesgo publicitario y calendario**: puntuación editorial mía (1-5),
  justificada en la columna `notas` del backlog.
- **No medido** (queda para la Fase 1, con la API de YouTube y las transcripciones):
  - CTR y retención de terceros.
  - Análisis visual de miniaturas.
  - Estructura de ganchos a partir de transcripciones.

  Los patrones de título y de formato que siguen se deducen de títulos y duraciones reales.

## 2. Canales de referencia

Se muestran 16: los 15 pedidos más Mystery World como contraste de formato. Los títulos en
inglés aparecen traducidos automáticamente por YouTube al extraerlos con `hl=es`.

| Canal | Idioma | Subs | Vídeos/mes | Duración mediana | Vistas medianas | Máx./mediana | Outliers destacados |
|---|---|---|---|---|---|---|---|
| Mr. Nightmare | EN | 7,14 M | ~10 | 26,6 min | 883.000 | 1,9x | — (muy estable) |
| Chilling Scares | EN | 2,86 M | ~3 | 24,9 min | 1.700.000 | 2,3x | "6 momentos más perturbadores captados en TV en directo" 3,9 M |
| Scary Pumpkin | HI/EN | 3,76 M | ~6 | 20,5 min | 1.100.000 | 3,5x | "Maran Kriya" 3,8 M |
| MrBallen | EN | 11,3 M | ~30 | 30,6 min | 1.400.000 | 1,6x | — |
| Lazy Masquerade | EN | 1,9 M | ~2,5 | 36,0 min | 711.000 | 2,0x | "How the Internet Unmasked The Vietnamese Butcher" 1,4 M |
| Nexpo | EN | 3,99 M | ~0,5 | 48,2 min | 3.650.000 | 3,3x | "The Darkest Lost Media" 12 M; "Walten Files" 11 M |
| Barely Sociable | EN | 1,38 M | ~0,4 | 26,8 min | 2.100.000 | 6,2x | "El lado oscuro de Silk Road" 13 M |
| DrossRotzank | ES | 24,2 M | ~30 | 14,9 min | 1.300.000 | 2,1x | "Querido Dross…" 2,7 M |
| BreakMan | ES | 9,75 M | ~7,5 | 25,9 min | 591.000 | 3,0x | "Vídeos de terror extremo…" 1,8 M |
| MundoCreepy | ES | 3,2 M | ~5 | 50,6 min | 461.000 | 2,4x | "7 casos PERTURBADORES ocurridos en MÉXICO" 1,1 M; "7 misterios SIN RESOLVER de ARGENTINA" 969.000 |
| Relatos de la Noche | ES | 2,4 M | ~10 | 32,7 min | 418.000 | 1,8x | "Trabajé para una secta de Guadalajara" 744.000 |
| Canal del Crimen | ES | n/d | ~3,3 | 45,3 min | 335.000 | 2,2x | "Randy Kraft…" 725.000 |
| Pero eso es otra Historia | ES | 2,07 M | ~2,5 | 45,5 min | 141.500 | 7,8x | "LA BIBLIA: resumen épico" 1,1 M |
| Mystery World | ES | 3,04 M | ~0,6 | 65,1 min | 2.100.000 | 2,4x | Exploraciones de lugares (formato distinto) |
| La leyenda negra española | ES | pequeño | ~0,6 | 9,1 min | 16.500 | 13,6x | "La derrota que tapó EEUU en 1898" 225.000 |
| España Negra – Crímenes Reales | ES | pequeño | ~6 | 36,9 min | 382 | 97x | Caso Andic (actualidad, 2024) 37.000 |

### Patrones observados

- **Títulos**: cuatro fórmulas dominan.
  1. Número más superlativo más ámbito: "7 casos PERTURBADORES ocurridos en MÉXICO",
     "3 historias de terror REALES…".
  2. Una sola palabra en MAYÚSCULAS como gancho (PERTURBADORES, REALES, SIN RESOLVER).
  3. Afirmación intrigante sin cerrar ("No le creyeron hasta que vieron la foto",
     "El libro vinculado a 75.000 desapariciones").
  4. Nombre del caso más apodo: "LIZZIE BORDEN – LA ASESINA DEL HACHA".
  - La geografía en el título (país, bandera) rinde bien en español.
- **Frecuencia frente a calidad**:
  - Los canales pequeños con mucho trabajo por vídeo (Nexpo, Barely Sociable) tienen las
    medianas más altas con 0,4-0,5 vídeos/mes.
  - Los de volumen alto (Dross, MrBallen) tienen marca personal y cara o voz reconocible.
  - Para un canal sin cara que empieza, 2 vídeos/semana es razonable; la calidad del guion
    manda.
- **Outliers**: aparecen con temas "madriguera" y un ángulo único (Silk Road, lost media,
  la Biblia resumida). En historia española, el outlier de La leyenda negra española es un
  hecho poco conocido con lectura provocadora ("la derrota que tapó EEUU").
- **Estructura** (a partir de duraciones y títulos, sin transcripciones): compilación de 3 a 7
  casos (MundoCreepy, Mr. Nightmare, Chilling Scares) frente a caso único en profundidad
  (Canal del Crimen, Barely Sociable). Propuesta: alternar el caso único (plantillas del kit)
  con recopilaciones temáticas por país. El kit ya las prevé (`recopilacion_cada_n_videos: 6`).

## 3. Huecos de contenido en español

1. **Historia oscura hispánica pre-1926 con fuentes**: nadie la cubre de forma sistemática.
   Los grandes hacen internet, casos modernos o relatos de suscriptores. Los divulgadores de
   historia (Pero eso es otra Historia) no usan el registro de suspense.
2. **Temas documentados con poca cobertura en vídeo**. Menos de 2 vídeos con 100.000 vistas
   en la búsqueda, y expediente o hemeroteca disponible:
   - La Recta Provincia (juicio a los brujos de Chiloé, 1880)
   - El naufragio del Príncipe de Asturias (1916)
   - Felicitas Guerrero
   - El lobizón y el padrinazgo presidencial
   - El Palacio de Linares
   - La fiebre amarilla de Buenos Aires (1871)
   - Los agotes
   - El crimen de la calle Fuencarral
   - El crimen del Expreso de Andalucía
3. **Leyendas con demanda enorme pero saturadas** en relato animado o corto: El Silbón (mediana
   de búsqueda de 2,7 M), La Llorona (695.000), La Patasola, el Pombero, el nahual. El hueco
   aquí es el **"origen documentado"** (Cihuacóatl y Sahagún para la Llorona, etnografía para
   el Silbón), no el relato.
4. **España como mercado**: tiene RPM más alto (§5) y menos oferta que México. Las leyendas y
   sucesos peninsulares están poco cubiertos (Santa Compaña, Zugarramurdi, Romasanta).
5. **Formato por país** ("7 misterios sin resolver de Perú", "leyendas de Chiloé"): lo valida
   MundoCreepy. Encaja con las recopilaciones de 1-2 h si llevan narración nueva (§7).

## 4. Backlog (50 temas) → `data/estado/backlog.csv`

Columnas:
- **Señales medidas**: `wiki_es_vistas_12m`, `yt_busqueda_mediana_vistas`,
  `yt_busqueda_top_vistas`, `yt_videos_100k`.
- **Puntuaciones 1-5**: `demanda`, `saturacion`, `documentacion`, `riesgo_publicitario`.
- **Resto**: `calendario`, `plantilla`, `prioridad`, `estado`, `notas`.

La prioridad, sobre 10, se calcula así:
`2 × (0,35·demanda + 0,25·documentación + 0,25·(6−riesgo) + 0,15·(6−saturación) + bonus)`.
- El bonus es de 0,4 para Halloween, Día de Muertos y Día de Difuntos, 0,2 para Semana Santa
  y 0,1 para San Juan.
- La demanda combina Wikipedia y la búsqueda de YouTube. Si no hay artículo en Wikipedia, se
  usa solo YouTube.

**Top 10**: Carlos II el Hechizado · El Monte de las Ánimas · Carlota de México · Juana la Loca ·
Brujas de Zugarramurdi · La Llorona (ángulo de origen) · El nahual · El Silbón ·
La Recta Provincia · El Charro Negro.

**Reparto**: España 20 · México 8 · Colombia 5 · Argentina 5 · Perú 3 · Venezuela 2 ·
Guatemala 2 · Chile 2 · Ecuador, Bolivia, Paraguay y El Salvador/Guatemala, 1 cada uno.

**Corte de 100 años (decisión del 28/09/2026)**. Salen del backlog cinco temas, con su motivo:
- Goyo Cárdenas (1942)
- El incendio del Teatro Novedades (1928)
- La masacre de las bananeras (1928)
- La Casa Matusita (leyenda del s. XX)
- La Planchada (leyenda del s. XX)

Los sustituyen, con datos medidos: el galeón San José (1708), el Charro Negro, la Tatuana,
la Sayona y el crucero Reina Regente (1895).
- Carlota de México se mantiene: sus hechos centrales son de 1866, aunque murió en 1927.
- El Expreso de Andalucía (1924, 102 años) queda justo por encima del corte.

**Excluidos a propósito** (no están en el backlog):
- Casos con **víctimas infantiles**, porque YouTube restringe los anuncios: Enriqueta Martí,
  el Petiso Orejudo, Felícitas Sánchez Aguillón.
- Casos **recientes o con implicados vivos**: Alcàsser, las Poquianchis, la Isla de las
  Muñecas, las caras de Bélmez.
- La Guerra Civil española, por su sensibilidad política y por haber familiares vivos.

## 5. RPM y modelo de ingresos

### RPM estimado (USD por 1.000 vistas, lo que cobra el creador)

- **España**: 2-4 $ en nichos de entretenimiento/historia (fuentes: [Viraland][r1],
  [Monetízate Online][r2]). El 4º trimestre puede doblar el CPM; enero-febrero es el valle.
- **LATAM**:
  - México: ~1,2 $ de CPM → RPM de 0,5-0,7 $.
  - Colombia: RPM ~1 $.
  - Chile: RPM ~1,6 $.
  - Perú: CPM de 0,8-1,8 $.
  (fuentes: [Fluxnote][r3], [YTface][r4])
- **Mezcla esperada** (25 % España, 75 % LATAM, con México como mayor mercado):
  **0,8 $ (pesimista) · 1,3 $ (base) · 2,0 $ (optimista)**.

### Supuestos del modelo

- 8 vídeos largos al mes.
- 15 min de duración y 35 % de retención media → **87,5 horas de visualización por cada 1.000
  vistas**.
- Entrada en el YPP con el umbral de 2027 (8.000 horas en 365 días); se asume que los 1.000
  suscriptores llegan a la vez.
- Afiliación (libros y audiolibros) desde el día 1: 0,05 / 0,15 / 0,25 $ por cada 1.000 vistas.
- Membresías: marginales, no se modelan.

### Resultados

| Escenario | Vistas/mes (mes 6 → 12 → 24) | Entrada en YPP | Ingresos/mes en el mes 12 | Ingresos/mes en el mes 24 | Acumulado a 24 meses |
|---|---|---|---|---|---|
| Pesimista | 5.000 → 15.000 → 45.000 | mes 13 | ~1 $ | ~38 $ | ~310 $ |
| Base | 20.000 → 80.000 → 250.000 | mes 7 | ~116 $ | ~362 $ | ~3.400 $ |
| Optimista | 80.000 → 400.000 → 1.000.000 | mes 3-4* | ~900 $ | ~2.250 $ | ~23.500 $ |

\* Solo en el optimista se llega antes del 01/02/2027. Hasta esa fecha basta con 4.000 horas,
así que ese escenario podría entrar un mes antes.

**Lectura**: en 12 meses, la inversión (~800-1.800 €) no se recupera en el escenario base. El
proyecto es viable a 18-24 meses si el formato encaja. La palanca principal no es el coste,
sino conseguir 1 o 2 outliers.

## 6. Costes mensuales de APIs y servicios (USD, sin IVA)

### Precios unitarios

- **Claude**:
  - Opus 5.5: 4 $ / 20 $ por millón de tokens (entrada / salida).
  - Sonnet 5: 2 $ / 10 $.
  - Haiku 4.5: 1 $ / 5 $.
  - La Batch API aplica un −50 %. La caché cobra las lecturas a ~0,1x.
- **ElevenLabs** ([pricing][r5]):
  - Creator: 22 $/mes, 121.000 créditos.
  - Pro: 99 $/mes, 600.000 créditos.
  - Multilingual v2/v3 = 1 crédito por carácter; Flash/Turbo = 0,5 créditos por carácter.
  - Un guion de 3.000 palabras más el short son unos **19.000 caracteres**.
- **Imágenes IA estilizadas**: 0,01-0,055 $ por imagen ([comparativa][r6]). Estimación de
  ~30 imágenes más 3 miniaturas por vídeo, si no hay material de dominio público.
- **Música**: Epidemic Sound Creator, 9,99 $/mes con pago anual ([fuente][r7]).
- **YouTube Data API**: gratis. `videos.insert` tiene cupo propio de 100 llamadas al día
  ([doc oficial][r8]).
- **GitHub Actions**:
  - Repositorio público: gratis.
  - Repositorio privado: 2.000 min/mes gratis y después 0,006 $/min en Linux ([fuente][r9]).

### Estimación de Claude por vídeo

- Investigación (Sonnet): ~0,5 $.
- Guion (Opus) con reintentos: ~1 $.
- Verificación y tono (Sonnet): ~0,3 $.
- **Orquestación con Claude Code en headless** durante 1-2 h: **~1,5-3 $**.
- **Total: ~3,5-5 $/vídeo** usando Claude Code como orquestador. Llamando a la API desde
  Python solo en los pasos creativos: **~2 $/vídeo**.

### Totales

| Vídeos/mes | Opción calidad (v3/Multilingual, Claude Code orquesta) | Opción económica (Flash, Python + API) |
|---|---|---|
| 4 | Claude 18 + TTS Creator 22 + imágenes 6 + música 10 = **~56 $** | 8 + 22 + 3 + 10 = **~43 $** |
| 8 | 36 + **Pro 99** + 11 + 10 = **~156 $** | 16 + 22 (Flash cabe en Creator) + 6 + 10 = **~54 $** |
| 12 | 54 + Pro 99 + 17 + 10 + GH ~2 = **~182 $** | 24 + Pro 99 (o 2× Creator) + 9 + 10 = **~142 $** |

**Conclusión**: con 60 € al mes, 8 vídeos solo caben con la opción económica. Hay que ajustar
`presupuesto` en la configuración o la calidad de voz (pregunta 3).

## 7. Normas vigentes de YouTube (verificadas el 28/09/2026)

| Norma | Fecha | Implicación | Fuente |
|---|---|---|---|
| Contenido no auténtico (antes "repetitivo"): no se monetizan presentaciones de imágenes con narración mínima, historias con plantilla ni contenido de IA producido en masa con plantillas genéricas. Sí se permiten la misma intro/outro y series con historias distintas. | actualizada el 15/07/2025 | Guion original de verdad, estructuras rotatorias y control de similitud (ya en el kit). Evitar "slideshow + TTS". | [YouTube Help 1311392][r10] |
| Contenido reutilizado: requiere aportación sustancial | 15/07/2025 | Las recopilaciones de 1-2 h necesitan narración y transiciones nuevas, no solo empalmes. | [YouTube Help 1311392][r10] |
| Reforma del YPP: 8.000 h en 365 días o 20 M de vistas de Shorts en 90 días. Los Shorts solo reparten ingresos con 10 M de vistas en 90 días. Los partners actuales no se ven afectados. | anunciada el 10/08/2026, efectiva el 01/02/2027 | Modelo de ingresos (§5). Los shorts-tráiler sirven de embudo, no de ingreso. | [Blog de YouTube][r11] |
| Directrices de anuncios: muertes en contexto educativo o documental (aclaración) | agosto de 2026 | Formato documental con contexto: monetizable si no es gráfico. | [YouTube Help 9725604][r12] |
| Eventos sensibles: no monetiza el contenido que se lucra con ellos | enero de 2024 | Evitar tragedias recientes; lo histórico queda fuera de ese riesgo. | [YouTube Help 9725604][r12] |
| Temas controvertidos sin contenido gráfico: monetización completa (maltrato, autolesión…); **se mantiene la restricción en abuso infantil** | enero de 2026 | Excluir casos con víctimas infantiles (hecho en el backlog). | [WSLS/AP 16/01/2026][r13] |
| Contenido "impactante" (que perturba o asquea): anuncios limitados | agosto de 2020 | Filtro de tono del kit, `max_riesgo_tono: 3`. | [YouTube Help 9725604][r12] |
| Contenido alterado o sintético: casilla obligatoria si es **realista** y puede confundirse con algo real. No hace falta para ilustraciones claramente no realistas ni para voz en off de IA sobre imágenes. | vigente, con aplicación reforzada en 2026 | Estilo IA no fotorrealista (ya en el prompt). Marcar la casilla solo en recreaciones realistas. | [Blog de YouTube][r14], [guía 2026][r15] |
| API: los vídeos subidos desde proyectos no auditados quedan bloqueados como privados | vigente (por verificar el formulario de auditoría) | Solicitar la auditoría en cuanto exista el proyecto de Google Cloud. | `docs/configurar-github.md` |

## 8. Incoherencias y riesgos del kit (verificados en code.claude.com/docs el 28/09/2026)

### Claude Code

| # | Punto | Estado | Acción propuesta (Fase 1) |
|---|---|---|---|
| 1 | `--permission-mode auto` | ✅ Existe. ⚠️ Solo con Opus/Sonnet 4.6+ (Haiku no es compatible). En `-p`, si el clasificador bloquea 3 veces seguidas o 20 en total, **deniega la acción y sigue sin parar**: puede saltarse pasos en silencio. | En CI, usar `--permission-mode dontAsk` con una lista explícita de permitidos (determinista). Validar `ultimo_resultado.json` siempre. |
| 2 | `--permission-prompts none` | ✅ Existe, pero **requiere v2.1.259 o superior**. **Tu claude local es la 2.1.220**: `scripts/run_headless.sh` fallará. | `claude update` antes de la Fase 2. |
| 3 | `anthropics/claude-code-action@v1` con `prompt` y `claude_args` | ✅ Correcto. Los comandos `/x` funcionan como `prompt`. Hace falta `id-token: write` (ya está) y la GitHub App de Claude instalada (o `github_token`). | Añadir la instalación de la App a `docs/configurar-github.md`. Fijar `--model` y `--max-turns` en `claude_args`. |
| 4 | `.claude/commands/*.md` | ✅ Siguen funcionando (fusionados con skills). | Mantener. Opcional: migrar a `.claude/skills/`. |
| 5 | Hooks: semántica de exit 2, `stop_hook_active`, `$CLAUDE_PROJECT_DIR`, matcher `Bash\|Read\|Edit\|Write` | ✅ Correctos. | — |
| 6 | Hooks invocan `python3` | ❌ En este Windows `python3` es el alias de la Microsoft Store: el hook falla con un código distinto de 2, que **no bloquea**. El bloqueo de `.env` **no funcionaría en local**. | Usar `python` o `uv run` y probar el hook en Windows. |
| 7 | La regex `env\s*$` del hook | ❌ Falso positivo: bloquea `python -m venv .venv`. | Corregir y añadir un test. |
| 8 | El hook no cubre `Grep` ni `Glob` | ⚠️ Grep podría leer `.env`. | Añadirlos al matcher y comprobar si `Read(./.env)` en deny cubre Grep. |
| 9 | Reglas `Bash(git push origin mejoras/*:*)` | ⚠️ Válidas, pero mezclan comodines. | Simplificar a `Bash(git push origin mejoras/*)`. |
| 10 | Arquitectura | ⚠️ Tensión: el prompt dice "Python determinista y Claude API solo en pasos creativos", pero `/nuevo-video` delega todo en subagentes de Claude Code. Eso duplica o triplica el coste (§6). | **Decisión tuya** (pregunta 5). |

### GitHub Actions y operación

| # | Riesgo | Detalle |
|---|---|---|
| 11 | **Veto con Environments** | *Required reviewers* y *wait timer* **solo en repositorios públicos** con Free, Pro y Team ([doc de GitHub][r16]). Con un repositorio privado, el job `publicar` no esperaría. |
| 12 | Concurrencia | El grupo `produccion` está a nivel de workflow y lo comparten los tres workflows. Un run que espera aprobación (hasta 30 días) o 24 h de wait timer **bloquea** el siguiente `producir` y el informe. GitHub solo guarda un run pendiente por grupo y **cancela el anterior**, así que se perderían crons. Moverlo al job `producir`. |
| 13 | Rechazo = fallo | Rechazar el Environment deja el run en *failure* y dispara `reparar-fallo`, gastando un run de Claude. Filtrar por el job que falló. |
| 14 | `hora_publicacion: 19:00` sin usar | Hoy se publica cuando apruebas. Propuesta: `publicar` programa `publishAt` a las 19:00 (Europe/Madrid) en lugar de hacerlo público al momento. |
| 15 | PR con `github.token` | Los PR que crea `GITHUB_TOKEN` no disparan CI. Además, hay que activar "Allow GitHub Actions to create pull requests". |
| 16 | Crons en repositorio público | GitHub desactiva los schedules tras 60 días sin actividad. Hay que verificar si cuentan los commits a la rama `estado`. |
| 17 | Entrada `tema` interpolada en el prompt | Riesgo bajo (solo quien tiene permiso de escritura), pero conviene sanearla. |
| 18 | Python | El kit fija 3.12 y aquí hay 3.14.5. No están instalados `ruff`, `gh` ni `python3`. El directorio **no es un repositorio git** todavía. |
| 19 | `data/estado/` está en `.gitignore` | Es intencionado (vive en la rama `estado`). El `backlog.csv` de esta fase solo llegará a GitHub con `scripts/estado.sh guardar`. |
| 20 | Referencias en inglés | Mr. Nightmare y Chilling Scares hacen relatos de suscriptores o internet, no historia oscura. Barely Sociable y Nexpo sirven más como modelo de "madriguera" documental. |

## 9. Decisiones tomadas (28/09/2026)

| Decisión | Valor | Consecuencia |
|---|---|---|
| Repositorio | **Público** | El veto con Environments funciona y GitHub Actions es gratis. El código, el backlog, los dossiers y los guiones de la rama `estado` serán públicos. Los secretos siguen seguros en *Actions secrets*. Hay que vigilar la desactivación de los crons tras 60 días sin actividad (§8.16). |
| Antigüedad mínima | **100 años** (sucesos anteriores a 1926) | Backlog recalculado (§4). En la Fase 1 se añadirá `contenido.antiguedad_minima_anios: 100` a la configuración y el investigador descartará lo que no cumpla. |
| Presupuesto | **0 € de gasto adicional** | Plan en §10. |
| Nombre | **El Escribano de Ánimas** (@ElEscribanoDeAnimas) | Elegido por Claude a petición del usuario: sin coincidencias encontradas en YouTube, podcasts ni libros; handle libre el 28/09/2026. Narrador con personaje: «el Escribano». |
| Cadencia | **1 vídeo por semana** (produce el martes, publica el viernes a las 19:00) | Se pasará a 2 cuando se mida la cuota de Claude Pro. |
| Claude | **Plan Pro** con `CLAUDE_CODE_OAUTH_TOKEN` (generado con `claude setup-token`) | El token dura **1 año**: hay que anotar la fecha de renovación. No funciona con `--bare`. Pro tiene un límite semanal único para todos los modelos (Opus incluido) y otro por ventanas de 5 h, **compartido con tu uso personal**. El control de "presupuesto" pasa de euros a **uso**: turnos por vídeo, Sonnet por defecto y Opus solo para el guion si el uso lo permite. |
| Voz | **Google Cloud TTS**, una voz fija de Chirp 3 HD | Sin clonación. En la Fase 1 se eligen la voz y los ajustes y se fijan en la configuración. |
| Orquestación | **Python** (determinista) | El pipeline de `src/` ejecuta todos los pasos. Solo los pasos creativos (dossier, guion, verificación, tono y metadatos) llaman a `claude -p` con salida JSON, `--max-turns` y herramientas mínimas; los subagentes de `.claude/agents/` definen los prompts. Claude Code en GitHub Actions queda solo para `/reparar-fallo` y `/informe-semanal`. |

## 10. Modo "coste 0" y Google Flow

### ¿Se puede producir con Google Flow?

No como base del sistema. Como mucho, sirve de complemento manual.

| Criterio | Google Flow | Fuente |
|---|---|---|
| API oficial | **No existe**: es solo una aplicación web. Hay APIs de terceros que automatizan tu cuenta (p. ej., useapi.net), pero no son oficiales y arriesgan la suspensión de la cuenta. No se pueden usar en un pipeline desatendido de GitHub Actions. | [therundown][f1], [useapi][f2] |
| Plan gratis | 50 créditos al día, **con marca de agua y solo para uso no comercial**. Incompatible con un canal monetizado. | [diyai][f3] |
| Plan comercial | Google AI Pro, 19,99 $/mes: 1.000 créditos ≈ 50 clips Veo Fast de 8 s ≈ **7 min de vídeo al mes**. Un solo vídeo de 15 min ya no cabe. | [diyai][f3] |
| Estilo | Veo tiende al fotorrealismo. El prompt pide IA **no fotorrealista** y obliga a marcar "contenido alterado/sintético" cuando es realista. | §7 |
| Política | Un vídeo hecho de clips de IA empalmados es el caso de libro del "contenido no auténtico" si no hay aportación original fuerte. | §7 |

**Recomendación**: la base visual serán grabados, pinturas, mapas y fotografías de archivo de
dominio público, animados con Ken Burns, parallax y grano. El paso 7 del pipeline del prompt ya
lo prevé y es lo que mejor encaja con la "historia oscura documentada".
- Si más adelante tienes Google AI Pro, Flow puede servir para 2-4 planos manuales por vídeo
  (cold open, intro de marca). Se generan a mano y se dejan en `assets/` con su licencia
  registrada.
- Si lo que interesa es la **generación de imágenes** de Flow (Nano Banana), el sustituto
  automatizable y gratuito es FLUX.1 schnell en Cloudflare Workers AI (abajo).

### Pila de coste 0 propuesta

| Pieza | Opción gratuita | Límite o condición | Fuente |
|---|---|---|---|
| Guion, investigación y verificación (Claude) | **Suscripción de Claude** que ya tengas (Pro o Max) con `claude_code_oauth_token` en `claude-code-action` y `claude setup-token` en local. Es la vía documentada; no hay facturación por API. | Límites de uso del plan (ventanas de 5 h y semanales). Con Pro, 2 vídeos por semana puede ir justo: habrá que medirlo en la Fase 2. | [docs de Claude Code][f4] |
| Voz | **Google Cloud TTS**: 1 M de caracteres al mes gratis en Chirp 3 HD o Neural2, y 4 M en Standard o WaveNet. 8 vídeos ≈ 150.000 caracteres, **muy por debajo del límite**. | Hay que activar la facturación, aunque el uso sea 0 € (poner alerta de presupuesto en 1 €). **Sin voz clonada**: la voz de marca será una voz fija de Chirp 3 HD en es-ES o es-US. El soporte de SSML de Chirp 3 HD es limitado (verificar en la Fase 1). | [precios de Google Cloud TTS][f5] |
| Voz de respaldo | Kokoro-82M o Piper, en local dentro del runner (licencias Apache/MIT). | Calidad inferior; solo como plan B. | — |
| Voz descartada | Gemini API TTS gratis: **no disponible en el EEE**. Edge TTS: no oficial, términos de uso dudosos. | — | [regiones de Gemini][f6] |
| Imágenes de archivo | Wikimedia Commons, Biblioteca Digital Hispánica (BNE), Europeana, Library of Congress, Met/Rijksmuseum Open Access. | Registrar la licencia de cada imagen (PD o CC0; con CC-BY, atribuir en la descripción). | — |
| Imágenes IA estilizadas | **Cloudflare Workers AI**: 10.000 *neurons* al día gratis ≈ 200 imágenes FLUX.1 schnell al día. Licencia Apache 2.0, uso comercial permitido. | Estilo grabado o ilustración, nunca fotorrealista. | [Cloudflare][f7] |
| Música | YouTube Audio Library (uso libre en YouTube) y Kevin MacLeod / Incompetech (CC-BY, con atribución). | Evitar bibliotecas que generan reclamaciones de Content ID. | — |
| Orquestación y render | GitHub Actions en repositorio público: minutos gratis e ilimitados en runners estándar. FFmpeg en el runner. | Timeout de 6 h por job; el kit usa 5 h. | [GitHub][r9] |
| Publicación y avisos | YouTube Data API y Telegram Bot API. | Gratis; subidas limitadas a 100 al día. | [r8] |

**Coste mensual estimado: 0 €**, suponiendo una suscripción de Claude ya existente y dentro
de los límites gratuitos anteriores. Riesgos de este modo:
1. **Límites de la suscripción de Claude**: si se agotan, el run falla. Mitigación: pipeline
   en Python con solo 3-4 llamadas creativas a Claude por vídeo; ensayar la cadencia real en
   la Fase 2.
2. **Voz no clonada**: menos "marca" que ElevenLabs. Mitigación: la misma voz y los mismos
   ajustes siempre, más intro y outro sonoros propios.
3. **Dependencia de programas gratuitos** que pueden cambiar. Mitigación: un módulo TTS con
   interfaz común (Google, Kokoro o ElevenLabs intercambiables por configuración).

[f1]: https://www.therundown.ai/tools/flow
[f2]: https://github.com/useapi/google-flow-api
[f3]: https://diyai.io/ai-tools/video-generation/google-veo-pricing/
[f4]: https://code.claude.com/docs/en/github-actions
[f5]: https://cloud.google.com/text-to-speech/pricing
[f6]: https://ai.google.dev/gemini-api/docs/available-regions
[f7]: https://developers.cloudflare.com/workers-ai/platform/pricing/

## 11. Preguntas abiertas

Resueltas el 28/09/2026:
- **Fase 0 aprobada.**
- Mercado prioritario **España** (voz es-ES).
- **Sin carrera por Halloween 2026.**
- Nombre del canal: El Escribano de Ánimas.
- **Fase 1 (arquitectura) aprobada**; implementada en `src/`, `tests/`, `.claude/` y `.github/`.

[r1]: https://viraland.es/cuanto-paga-youtube-de-verdad-en-2026-el-rpm-real-por-nicho-y-pais-sin-humo/
[r2]: https://monetizateonline.es/cuanto-paga-youtube-espana/
[r3]: https://fluxnote.io/guides/youtube-cpm-latin-america-by-country
[r4]: https://www.ytface.com/cpm-rates-by-country
[r5]: https://elevenlabs.io/pricing
[r6]: https://www.teamday.ai/blog/ai-api-pricing-comparison-2026
[r7]: https://www.epidemicsound.com/pricing/
[r8]: https://developers.google.com/youtube/v3/determine_quota_cost
[r9]: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions
[r10]: https://support.google.com/youtube/answer/1311392?hl=es
[r11]: https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/
[r12]: https://support.google.com/youtube/answer/9725604?hl=es
[r13]: https://www.wsls.com/business/2026/01/16/youtube-relaxes-monetization-policy-on-videos-with-controversial-content/
[r14]: https://blog.youtube/news-and-events/disclosing-ai-generated-content/
[r15]: https://minimatters.com/youtube-altered-or-synthetic-content-disclosure/
[r16]: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
