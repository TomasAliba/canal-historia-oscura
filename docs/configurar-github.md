# Puesta en marcha (una sola vez)

Orden recomendado. Nada de esto cuesta dinero si respetas los límites gratuitos.

## 0. En tu PC

```bash
claude update                      # hace falta Claude Code >= 2.1.259
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # en Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest -q                         # debe salir todo en verde
```

## 1. Repositorio en GitHub (público)

1. Crea un repositorio **público** vacío (p. ej. `canal-historia-oscura`) y sube el proyecto:
   ```bash
   git remote add origin https://github.com/<usuario>/canal-historia-oscura.git
   git add -A && git commit -m "Kit inicial" && git push -u origin main
   ```
2. Siembra la rama `estado` con el backlog de la Fase 0: `scripts/estado.sh guardar`.
3. **Settings → Actions → General**: "Read and write permissions" y marca
   "Allow GitHub Actions to create and approve pull requests".
4. **Settings → Branches**: protege `main` (los arreglos automáticos llegan por PR).
5. Instala la **Claude GitHub App** (https://github.com/apps/claude) en el repositorio: la usan
   `reparar-fallo.yml` e `informe-semanal.yml`.

> Repositorio público: el código, el backlog, los dossiers y los guiones (rama `estado`) son visibles.
> Los secretos NO: viven en *Actions secrets*. Nunca subas `.env` ni `secrets/`.

## 2. Claude (suscripción Pro)

1. `claude setup-token` → copia el token (dura 1 año; apunta la fecha para renovarlo).
2. Secret `CLAUDE_CODE_OAUTH_TOKEN` con ese valor.
3. El uso cuenta contra tus límites de Pro (compartidos con tu uso personal). Por eso el canal
   empieza con 1 vídeo por semana.

## 3. Google Cloud: voz (Text-to-Speech) y YouTube

1. Crea un proyecto en https://console.cloud.google.com.
2. **Facturación**: actívala (Google la exige incluso dentro de la capa gratuita) y crea una
   **alerta de presupuesto de 1 €** (Facturación → Presupuestos y alertas).
3. Habilita las APIs: *Cloud Text-to-Speech*, *YouTube Data API v3* y *YouTube Analytics API*.
4. **Voz**: IAM → Cuentas de servicio → crea una cuenta con el rol mínimo necesario para TTS →
   Claves → JSON. Pega el contenido completo en el secret `GCP_TTS_SA_JSON`. En local, guárdalo en
   `secrets/gcp-tts.json`.
5. **YouTube OAuth**:
   - Pantalla de consentimiento OAuth → publícala en **producción** (en modo *Testing* el refresh
     token caduca a los 7 días).
   - Credenciales → ID de cliente OAuth tipo *Desktop app* → descarga `secrets/client_secret.json`.
   - En local: `.venv/Scripts/python -m src.auth_youtube` → genera `secrets/token.json`. Pega su
     contenido en el secret `YOUTUBE_TOKEN_JSON`.
6. **Auditoría de la API**: solicítala en el formulario de *YouTube API Services*. Hasta que la
   aprueben, los vídeos subidos por la API quedan bloqueados como privados: publícalos a mano desde
   YouTube Studio tras aprobarlos.
7. La subida usa su propio cupo (100 subidas al día por proyecto): de sobra.

## 4. Cloudflare Workers AI (ilustraciones de respaldo)

1. Cuenta gratuita en https://dash.cloudflare.com.
2. Secret `CLOUDFLARE_ACCOUNT_ID` (panel → Workers AI) y un API token con permiso *Workers AI*
   en `CLOUDFLARE_API_TOKEN`.
3. Capa gratuita: 10.000 neurons al día (≈ 200 imágenes FLUX schnell). El pipeline se limita a 150.
   Sin estos secrets, el pipeline usa solo imágenes de dominio público.

## 5. Canal de YouTube

1. Crea el canal **El Escribano de Ánimas** con el handle `@ElEscribanoDeAnimas`.
2. **Verifica el canal por teléfono** (necesario para miniaturas personalizadas y vídeos > 15 min).
3. Idioma del canal: español (España).

## 6. Telegram

1. Habla con @BotFather → `/newbot` → token en `TELEGRAM_BOT_TOKEN`.
2. Escribe a tu bot y obtén tu chat id (p. ej. con @userinfobot) → `TELEGRAM_CHAT_ID`.

## 7. Environments (veto)

**Settings → Environments** (disponible porque el repositorio es público):
- **`aprobacion`** (veto activo, el de partida): *Required reviewers* → tú. Limita
  *Deployment branches* a `main`.
- **`publicacion-diferida`** (veto pasivo, para más adelante): *Wait timer* = 1440 minutos. Para
  vetar un vídeo, cancela el run antes de que pase el plazo.
- Activa las notificaciones de la app móvil de GitHub para aprobar desde el móvil.

## 8. Música

Descarga pistas de la YouTube Audio Library o de incompetech (Kevin MacLeod, CC-BY) en
`assets/musica/` y regístralas en `assets/musica/licencias.yaml`. Sin pistas, el vídeo sale solo
con la voz.

## 9. Primera prueba

1. Actions → *Producir vídeo* → *Run workflow* con **simulado = true**: comprueba el circuito sin
   gastar TTS ni subir nada (sí usa Claude).
2. Después, *Run workflow* normal. Revisa el vídeo privado en YouTube Studio, aprueba el job
   `aprobar` y comprueba que llega el aviso de Telegram y que el vídeo queda programado para el
   viernes a las 19:00.

## Resumen de secrets

| Secret | Para qué |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Pro (`claude setup-token`) |
| `GCP_TTS_SA_JSON` | Voz (Google Cloud TTS) |
| `YOUTUBE_TOKEN_JSON` | Subida, programación y analítica |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Ilustraciones IA de respaldo (opcional) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Avisos |
