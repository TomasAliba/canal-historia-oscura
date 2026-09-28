# Opcional (migración futura a VPS): entorno aislado para la ejecución desatendida.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg git ca-certificates nodejs npm fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m canal
USER canal
WORKDIR /home/canal/app
ENV PATH="/home/canal/.local/bin:${PATH}"

COPY --chown=canal:canal requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=canal:canal . .
ENTRYPOINT ["scripts/run_headless.sh"]
CMD []
