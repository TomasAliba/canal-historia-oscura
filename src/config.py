"""Carga y valida config/canal.yaml y define las rutas del proyecto."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


def raiz() -> Path:
    """Raíz del proyecto. CANAL_RAIZ permite aislar los tests en un directorio temporal."""
    return Path(os.environ.get("CANAL_RAIZ", Path(__file__).resolve().parents[1]))


def dir_estado() -> Path:
    return raiz() / "data" / "estado"


def dir_media() -> Path:
    return raiz() / "data" / "media"


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class Canal(_Base):
    nombre: str
    idioma: str = "es"
    mercado_principal: str = "ES"


class Contenido(_Base):
    antiguedad_minima_anios: int = 100


class Formato(_Base):
    duracion_min_s: int
    duracion_max_s: int
    palabras_min: int
    palabras_max: int
    plantillas: list[str]
    rotacion_ultimos_n: int = 5
    short_trailer_s: int = 45
    resolucion: tuple[int, int] = (1920, 1080)
    fps: int = 30


class Produccion(_Base):
    videos_por_semana: int = 1
    dias_publicacion: list[str]
    hora_publicacion: str = "19:00"
    zona_horaria: str = "Europe/Madrid"


class Calidad(_Base):
    fuentes_minimas_pct: float = 100
    max_riesgo_tono: float = 3
    max_similitud: float = 0.35
    max_desfase_subtitulos_ms: int = 200
    max_reintentos: int = 2
    fotogramas_qa: int = 8


class Uso(_Base):
    max_llamadas_claude_por_video: int = 20
    max_turnos_claude_por_video: int = 150
    max_videos_semana: int = 1
    max_caracteres_tts_mes: int = 900_000
    max_imagenes_ia_dia: int = 150


class Voz(_Base):
    proveedor: str = "google"
    idioma: str = "es-ES"
    nombre: str
    ritmo: float = 1.0
    pausa_parrafo: str = "[pause long]"


class Veto(_Base):
    modo: str = "activo"
    umbral_cambio_pct: float = 90
    minimo_videos_para_cambio: int = 10


class Config(_Base):
    canal: Canal
    contenido: Contenido = Field(default_factory=Contenido)
    formato: Formato
    produccion: Produccion
    calidad: Calidad
    modelos: dict[str, str]
    max_turnos: dict[str, int] = Field(default_factory=dict)
    uso: Uso = Field(default_factory=Uso)
    voz: Voz
    visuales: dict[str, Any] = Field(default_factory=dict)
    audio: dict[str, Any] = Field(default_factory=dict)
    veto: Veto = Field(default_factory=Veto)
    calendario: dict[str, Any] = Field(default_factory=dict)


def cargar(ruta: Path | None = None) -> Config:
    ruta = ruta or raiz() / "config" / "canal.yaml"
    with ruta.open(encoding="utf-8") as f:
        return Config.model_validate(yaml.safe_load(f))


@lru_cache(maxsize=1)
def config() -> Config:
    return cargar()
