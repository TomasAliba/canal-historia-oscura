"""Tests unitarios de las piezas deterministas del pipeline."""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from src import claude_cli, db, ideacion, metadatos, montaje, publicar, qa, similitud, texto, tono, verificacion
from src.config import config
from tests.conftest import ClaudeFalso, ajustar_config, salida_claude

# ---------- texto ----------


def test_texto_quita_citas_y_pausas():
    t = "En 1852 [F:3] fue juzgado. [pause] Nadie lo olvidó [F:4]."
    assert texto.citas(t) == ["3", "4"]
    assert "[F:" not in texto.para_locucion(t)
    assert "[pause]" in texto.para_locucion(t)
    assert texto.limpio(t) == "En 1852 fue juzgado. Nadie lo olvidó."
    assert texto.palabras(t) == 7


def test_frases_y_slug():
    assert texto.frases("Uno. ¿Dos? ¡Tres! Cuatro") == ["Uno.", "¿Dos?", "¡Tres!", "Cuatro"]
    assert texto.slugificar("Romasanta: el Hombre Lobo de Allariz") == "romasanta-el-hombre-lobo-de-allariz"


# ---------- similitud ----------


def test_similitud_identicos_y_distintos():
    a = "El hombre lobo de Allariz fue juzgado en 1852 por la justicia de Celanova."
    b = "La peste de Sevilla vació las calles en 1649 y la ciudad nunca se recuperó."
    assert similitud.maxima(a, [a]) == pytest.approx(1.0)
    assert similitud.maxima(a, [b]) < 0.2
    assert similitud.maxima(a, []) == 0.0


# ---------- claude_cli ----------


def test_interpretar_structured_output():
    r = claude_cli.interpretar(salida_claude({"x": 1}, turnos=3), 0)
    assert r.datos == {"x": 1}
    assert r.turnos == 3
    assert r.tokens_salida == 500


def test_interpretar_json_en_texto():
    salida = json.dumps({"subtype": "success", "result": 'Aquí está:\n```json\n{"a": 2}\n```'})
    assert claude_cli.interpretar(salida, 0).datos == {"a": 2}


def test_interpretar_cuota_agotada():
    salida = json.dumps(
        {
            "subtype": "error_during_execution",
            "is_error": True,
            "result": "Claude usage limit reached. Your limit will reset at 5pm",
        }
    )
    with pytest.raises(claude_cli.CuotaAgotada):
        claude_cli.interpretar(salida, 1)


def test_llamar_reintenta_y_registra_uso(proyecto):
    con = db.conectar()
    intentos = {"n": 0}

    def ejecutor(cmd, entrada):
        intentos["n"] += 1
        if intentos["n"] == 1:
            return subprocess.CompletedProcess(cmd, 1, stdout="error raro", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=salida_claude({"ok": True}), stderr="")

    r = claude_cli.llamar(
        "verificador",
        "tarea",
        {"type": "object"},
        modelo="sonnet",
        max_turnos=2,
        con=con,
        ejecutor=ejecutor,
        espera_s=0,
    )
    assert r == {"ok": True}
    assert intentos["n"] == 2
    assert tuple(con.execute("SELECT SUM(llamadas), SUM(turnos) FROM uso").fetchone()) == (1, 2)


def test_comando_usa_dontask_schema_y_herramientas(proyecto):
    cmd = claude_cli.comando("investigador", {"type": "object"}, "sonnet", 40, ["WebSearch", "WebFetch"])
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    assert "--json-schema" in cmd
    assert cmd[cmd.index("--allowedTools") + 1] == "WebSearch,WebFetch"
    assert "investigador histórico" in cmd[cmd.index("--append-system-prompt") + 1]


def test_claude_falso_identifica_agentes(proyecto):
    falso = ClaudeFalso({})
    for agente in ("investigador", "guionista", "verificador", "filtro-tono", "metadatos", "qa"):
        assert falso.agente(claude_cli.comando(agente, {}, "haiku", 3, [])) == agente


# ---------- ideación ----------


def test_domingo_de_pascua():
    assert ideacion.domingo_de_pascua(2027) == date(2027, 3, 28)
    assert ideacion.domingo_de_pascua(2026) == date(2026, 4, 5)


def _fila(slug, antiguedad, prioridad, calendario=""):
    return {
        "slug": slug,
        "pais": "ES",
        "antiguedad_anios": str(antiguedad),
        "prioridad": str(prioridad),
        "estado": "PENDIENTE",
        "calendario": calendario,
        "plantilla": "cronologica",
        "notas": "",
    }


def test_elegir_respeta_antiguedad_y_calendario(proyecto):
    cfg = config()
    con = db.conectar()
    ideacion.escribir_backlog(
        [_fila("reciente", 80, 9.9), _fila("normal", 150, 8.0), _fila("difuntos", 160, 7.0, "Día de Difuntos")]
    )
    assert ideacion.elegir(cfg, con, hoy=date(2027, 5, 1))["slug"] == "normal"
    assert ideacion.elegir(cfg, con, hoy=date(2027, 10, 20))["slug"] == "difuntos"


def test_plantilla_rota(proyecto):
    cfg = config()
    con = db.conectar()
    for i, p in enumerate(["cronologica", "in_media_res", "investigacion"]):
        db.crear_video(con, f"v{i}", p)
    assert ideacion.elegir_plantilla(cfg, con, "cronologica") == "testimonio"


# ---------- verificación y tono ----------


def _guion(textos):
    return {
        "titulo_trabajo": "t",
        "cta": "Suscríbete.",
        "capitulos": [
            {"titulo": f"C{i}", "parrafos": [{"texto": t, "visual": "v", "busqueda": "b"}]}
            for i, t in enumerate(textos)
        ],
    }


def test_chequeo_citas():
    dossier = {"afirmaciones": [{"id": "F1"}, {"id": "F2"}]}
    assert verificacion.chequeo_citas(_guion(["Dato [F:F1]."]), dossier) == []
    assert "inexistentes" in verificacion.chequeo_citas(_guion(["Dato [F:F9]."]), dossier)[0]
    assert "ninguna fuente" in verificacion.chequeo_citas(_guion(["Sin citas."]), dossier)[0]


def test_lexico_y_reescritura():
    g = _guion(["Encontraron las vísceras del reo en el camino."])
    parrafo = g["capitulos"][0]["parrafos"][0]
    assert tono.terminos_de_riesgo(parrafo["texto"]) == ["vísceras"]
    cambio = {"original": "las vísceras del reo", "reescrito": "lo que quedaba del reo", "riesgo": 7}
    assert tono.aplicar_reescrituras(g, [cambio]) == 1
    assert tono.terminos_de_riesgo(parrafo["texto"]) == []


# ---------- metadatos, montaje, publicación, QA ----------


def test_capitulos_youtube():
    caps = [
        {"titulo": "Prólogo", "inicio": 0.4},
        {"titulo": "A", "inicio": 5},
        {"titulo": "B", "inicio": 65},
        {"titulo": "C", "inicio": 3700},
    ]
    assert metadatos.capitulos_youtube(caps) == ["0:00 Prólogo", "1:05 B", "1:01:40 C"]
    assert metadatos.capitulos_youtube(caps[:2]) == []


def test_fotogramas_sin_deriva():
    escenas = [{"inicio": 0.0}, {"inicio": 3.337}, {"inicio": 7.01}]
    frames = montaje.fotogramas_por_escena(escenas, 10.0, 30)
    assert sum(frames) == 300
    assert all(f > 0 for f in frames)


def test_metadatos_capitulos_ffmpeg():
    meta = montaje.metadatos_capitulos([{"titulo": "Uno=1", "inicio": 0}, {"titulo": "Dos", "inicio": 2.5}], 5)
    assert meta.startswith(";FFMETADATA1")
    assert "START=2500" in meta
    assert "title=Uno\\=1" in meta


def test_proxima_publicacion(proyecto):
    ajustar_config(proyecto, **{"produccion.dias_publicacion": ["martes", "viernes"]})
    tz = ZoneInfo("Europe/Madrid")
    cfg = config()
    # Martes 6/10/2026 18:30: menos de 2 h de margen → viernes 9/10 a las 19:00.
    esperado = datetime(2026, 10, 9, 19, 0, tzinfo=tz)
    assert publicar.proxima_publicacion(cfg, datetime(2026, 10, 6, 18, 30, tzinfo=tz)) == esperado
    assert publicar.proxima_publicacion(cfg, datetime(2026, 10, 6, 9, 0, tzinfo=tz)).day == 6


def test_desfase_subtitulos():
    tiempos = {
        "escenas": [{"frases": [{"inicio": 0.0, "fin": 2.0}, {"inicio": 2.25, "fin": 4.0}]}],
        "subtitulos": [
            {"inicio": 0.0, "fin": 2.0},
            {"inicio": 2.25, "fin": 3.1},
            {"inicio": 3.1, "fin": 4.0},
        ],
    }
    assert qa.desfase_subtitulos_ms(tiempos) == pytest.approx(0.0)
    tiempos["subtitulos"][-1]["fin"] = 4.5
    assert qa.desfase_subtitulos_ms(tiempos) == pytest.approx(500.0)


# ---------- uso y decisiones ----------


def test_uso_limita_videos_por_semana(proyecto):
    from src import uso

    cfg = config()
    con = db.conectar()
    assert uso.comprobar(cfg, con) == []
    db.crear_video(con, "a", "cronologica")
    db.actualizar_video(con, "a", estado="ESPERANDO_PUBLICACION")
    assert "esta semana" in uso.comprobar(cfg, con)[0]


def test_decisiones_y_coincidencia(proyecto):
    from src import decisiones

    ajustar_config(proyecto, **{"veto.minimo_videos_para_cambio": 2})
    con = db.conectar()
    for s in ("a", "b"):
        db.crear_video(con, s, "cronologica")
        db.actualizar_video(con, s, veredicto_auto="aprobado")
        decisiones.registrar(con, s, "success")
    assert decisiones.coincidencia(config(), con) == {
        "videos": 2,
        "coincidencia_pct": 100.0,
        "proponer_pasivo": True,
    }
    db.crear_video(con, "c", "cronologica")
    assert decisiones.registrar(con, "c", "cancelled") == "rechazado"
    assert db.video(con, "c")["estado"] == "RECHAZADO_VETO"
