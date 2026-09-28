"""Autorización OAuth única (en local) para generar secrets/token.json con refresh token.

Uso: python -m src.auth_youtube  (requiere secrets/client_secret.json, tipo "Desktop app")
Después copia el CONTENIDO de secrets/token.json al secret YOUTUBE_TOKEN_JSON de GitHub.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from src.publicar import SCOPES


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    cliente = Path(os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE", "secrets/client_secret.json"))
    destino = Path(os.environ.get("YOUTUBE_TOKEN_FILE", "secrets/token.json"))
    flujo = InstalledAppFlow.from_client_secrets_file(str(cliente), SCOPES)
    cred = flujo.run_local_server(port=0, access_type="offline", prompt="consent")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(cred.to_json(), encoding="utf-8")
    print(f"Token guardado en {destino}. No lo compartas ni lo subas al repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
