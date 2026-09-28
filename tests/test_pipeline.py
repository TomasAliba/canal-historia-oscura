"""Pipeline de extremo a extremo en modo simulado: Claude falso, TTS e imágenes simulados y FFmpeg real
a baja resolución. Comprueba estados, artefactos, reanudación, descarte y pausa por cuota."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from src import almacen, db, ideacion, pipeline
from tests.conftest import ClaudeFalso, ajustar_config

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requiere ffmpeg")

DOSSIER = {
    "descartar": False,
    "motivo_descarte": "",
    "anio_suceso": 1852,
    "resumen": "Manuel Blanco Romasanta fue juzgado en Allariz.",
    "cronologia": [{"fecha": "1852", "hecho": "Juicio en Allariz", "fuente_id": "F1"}],
    "personajes": ["Manuel Blanco Romasanta"],
    "afirmaciones": [
        {
            "id": f"F{i}",
            "texto": f"Hecho documentado número {i}.",
            "etiqueta": "HECHO",
            "fuente": {"autor": "Autor", "obra": f"Causa judicial {i}", "anio": "1853", "url": ""},
        }
        for i in range(1, 11)
    ],
    "lagunas": ["No se conserva el acta completa."],
    "busquedas_imagenes": ["Allariz grabado"],
}

GUION = {
    "titulo_trabajo": "El hombre lobo de Allariz",
    "capitulos": [
        {
            "titulo": t,
            "parrafos": [
                {
                    "texto": f"En mil ochocientos cincuenta y dos pasó algo en {t.lower()} [F:F{i + 1}]. "
                    "[pause] Nadie supo explicarlo entonces.",
                    "visual": "grabado de una aldea gallega",
                    "busqueda": "Allariz grabado",
                }
            ],
        }
        for i, t in enumerate(["El juicio", "La aldea", "El reo", "La sentencia"])
    ],
    "cta": "Si te ha gustado, suscríbete.",
}


def respuestas(dossier=DOSSIER):
    return {
        "investigador": dossier,
        "guionista": GUION,
        "verificador": {"afirmaciones": [{"texto": "Juicio en 1852", "fuente": "F1", "estado": "ok"}]},
        "filtro-tono": {"riesgo_global": 1, "pasajes": [], "riesgo_tras_reescritura": 1},
        "metadatos": {
            "titulos": ["El HOMBRE LOBO de Allariz", "¿Quién era Romasanta?", "Romasanta: el lobo"],
            "gancho_descripcion": "En 1852 un tribunal gallego juzgó a un hombre lobo.",
            "etiquetas": ["Romasanta", "Allariz"],
            "textos_miniatura": ["EL LOBO", "1852", "JUZGADO"],
        },
    }


@pytest.fixture
def entorno(proyecto):
    ajustar_config(
        proyecto,
        **{
            "formato.resolucion": [320, 180],
            "formato.fps": 10,
            "formato.duracion_min_s": 5,
            "formato.duracion_max_s": 600,
            "formato.palabras_min": 20,
            "formato.palabras_max": 5000,
            "formato.short_trailer_s": 8,
            "calidad.fotogramas_qa": 3,
        },
    )
    ideacion.escribir_backlog(
        [
            {
                "slug": "romasanta",
                "titulo_trabajo": "Romasanta",
                "pais": "ES",
                "antiguedad_anios": "173",
                "prioridad": "9",
                "estado": "PENDIENTE",
                "calendario": "",
                "plantilla": "investigacion",
                "notas": "",
            }
        ]
    )
    return proyecto


def test_pipeline_simulado_completo_y_reanudable(entorno):
    falso = ClaudeFalso(respuestas())
    r = pipeline.ejecutar(simulado=True, ejecutor=falso, espera_s=0)
    assert r["estado"] == "QA_OK", r
    carpeta = almacen.media("romasanta")
    for f in ("final.mp4", "short.mp4", "subtitulos.srt", "tiempos.json", "metadatos.json"):
        assert (carpeta / f).exists(), f
    assert len(list((carpeta / "miniaturas").glob("*.jpg"))) == 3
    m = almacen.leer_json(carpeta / "metadatos.json")
    assert "Fuentes:" in m["descripcion"]
    assert "Causa judicial 1" in m["descripcion"]
    assert "0:00 El juicio" in m["descripcion"]
    ultimo = entorno / "data" / "estado" / "ultimo_resultado.json"
    assert json.loads(ultimo.read_text(encoding="utf-8"))["estado"] == "QA_OK"
    assert ideacion.leer_backlog()[0]["estado"] == "EN_CURSO"
    orden = ["investigador", "guionista", "verificador", "filtro-tono", "metadatos"]
    assert [a for a, _ in falso.llamadas] == orden
    con = db.conectar()
    assert db.video(con, "romasanta")["plantilla"] == "investigacion"
    assert con.execute("SELECT SUM(llamadas) FROM uso").fetchone()[0] == 5

    # Reanudación: el vídeo ya está en QA_OK; en simulado no se sube y no se vuelve a llamar a Claude.
    r2 = pipeline.ejecutar(tema="romasanta", simulado=True, ejecutor=falso, espera_s=0)
    assert r2["estado"] == "QA_OK"
    assert len(falso.llamadas) == 5


def test_pipeline_descarta_temas_recientes(entorno):
    dossier = dict(DOSSIER, anio_suceso=1990)
    r = pipeline.ejecutar(simulado=True, ejecutor=ClaudeFalso(respuestas(dossier)), espera_s=0)
    assert r["estado"] == "DESCARTADO"
    assert "posterior al corte" in r["motivos"][0]
    assert ideacion.leer_backlog()[0]["estado"] == "DESCARTADO"


def test_pipeline_pausa_por_cuota_sin_perder_progreso(entorno):
    llamadas = {"n": 0}
    base = ClaudeFalso(respuestas())

    def ejecutor(cmd, entrada):
        llamadas["n"] += 1
        if base.agente(cmd) == "guionista":
            salida = json.dumps(
                {"subtype": "error_during_execution", "is_error": True, "result": "Claude usage limit reached"}
            )
            return subprocess.CompletedProcess(cmd, 1, stdout=salida, stderr="")
        return base(cmd, entrada)

    r = pipeline.ejecutar(simulado=True, ejecutor=ejecutor, espera_s=0)
    assert r["estado"] == "PAUSADO_CUOTA"
    assert db.video(db.conectar(), "romasanta")["estado"] == "INVESTIGADO"
    # El siguiente run reanuda desde el guion (no repite la investigación).
    falso = ClaudeFalso(respuestas())
    assert pipeline.ejecutar(simulado=True, ejecutor=falso, espera_s=0)["estado"] == "QA_OK"
    assert falso.llamadas[0][0] == "guionista"


def test_pipeline_regenera_guion_si_la_verificacion_falla(entorno):
    resp = respuestas()
    veredictos = iter(
        [
            {"afirmaciones": [{"texto": "Dato inventado", "fuente": None, "estado": "sin_fuente"}]},
            resp["verificador"],
        ]
    )
    resp["verificador"] = lambda _entrada: next(veredictos)
    falso = ClaudeFalso(resp)
    r = pipeline.ejecutar(simulado=True, ejecutor=falso, espera_s=0, hasta="TONO_OK")
    assert db.video(db.conectar(), "romasanta")["estado"] == "TONO_OK", r
    guion_2 = [e for a, e in falso.llamadas if a == "guionista"][1]
    assert "NO superó los controles" in guion_2
    assert "Dato inventado" in guion_2
