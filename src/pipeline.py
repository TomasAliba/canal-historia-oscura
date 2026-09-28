"""Orquestador determinista: máquina de estados por vídeo, reanudable y con reintentos.

Uso:
  python -m src.pipeline                   siguiente tema del backlog (o reanuda el vídeo en curso)
  python -m src.pipeline --tema <slug>     tema concreto
  python -m src.pipeline --simulado        voz e imágenes simuladas, sin subir (ensayo sin coste de TTS/IA)
  python -m src.pipeline --hasta MONTADO   se detiene tras ese estado (pruebas locales)
  python -m src.pipeline --sin-subir       produce pero no sube a YouTube

Escribe data/estado/ultimo_resultado.json con {slug, video_id, estado, uso, motivos} (lo lee el workflow).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from src import (
    almacen,
    audio,
    claude_cli,
    db,
    guion,
    ideacion,
    investigacion,
    metadatos,
    miniaturas,
    montaje,
    qa,
    short,
    similitud,
    tono,
    tts,
    uso,
    verificacion,
    visuales,
)
from src.config import Config, config, dir_estado
from src.guion import texto_completo
from src.notificar import enviar
from src.registro import log

ORDEN = [
    "PENDIENTE",
    "INVESTIGADO",
    "TONO_OK",
    "VOZ_OK",
    "VISUALES_OK",
    "AUDIO_OK",
    "MONTADO",
    "METADATOS_OK",
    "MINIATURAS_OK",
    "SHORT_OK",
    "QA_OK",
    "ESPERANDO_PUBLICACION",
]
TERMINALES = {"ESPERANDO_PUBLICACION", "PROGRAMADO", "PUBLICADO", "DESCARTADO", "RECHAZADO_VETO", "BLOQUEADO"}
MAX_ERRORES_SEGUIDOS = 3


class Contexto:
    def __init__(
        self,
        cfg: Config,
        con: sqlite3.Connection,
        fila: sqlite3.Row,
        tema: dict[str, str],
        simulado: bool,
        kw: dict[str, Any],
    ) -> None:
        self.cfg, self.con, self.tema, self.simulado, self.kw = cfg, con, tema, simulado, kw
        self.slug: str = fila["slug"]
        self.id: int = fila["id"]
        self.plantilla: str = fila["plantilla"]

    @property
    def estado(self) -> str:
        return db.video(self.con, self.slug)["estado"]

    def avanzar(self, estado: str, **campos: Any) -> None:
        db.actualizar_video(self.con, self.slug, estado=estado, **campos)
        log("estado", slug=self.slug, estado=estado)

    def paso_hecho(self, estado: str) -> bool:
        actual = self.estado
        return actual in ORDEN and ORDEN.index(actual) >= ORDEN.index(estado)

    def tiempos(self) -> dict[str, Any]:
        return almacen.leer_json(almacen.media(self.slug) / "tiempos.json")


class Descartar(Exception):
    pass


# ---------- pasos ----------


def paso_investigar(c: Contexto) -> None:
    try:
        investigacion.investigar(c.tema, c.cfg, c.con, c.id, **c.kw)
    except investigacion.Descartado as e:
        raise Descartar(str(e)) from e
    c.avanzar("INVESTIGADO")


def paso_guion(c: Contexto) -> None:
    """Guion → extensión → similitud → verificación → tono, con hasta max_reintentos regeneraciones."""
    dossier = almacen.leer_json(almacen.dossier(c.slug))
    motivos: list[str] = []
    for intento in range(c.cfg.calidad.max_reintentos + 1):
        db.actualizar_video(c.con, c.slug, intentos_guion=intento + 1)
        g = guion.escribir(
            c.slug,
            dossier,
            c.plantilla,
            c.cfg,
            c.con,
            c.id,
            motivos=motivos,
            usar_fallback=intento > 0 and _uso_alto(c),
            **c.kw,
        )
        motivos = guion.control_extension(g, c.cfg)
        sim = similitud.maxima(texto_completo(g), similitud.guiones_anteriores(c.slug))
        c.con.execute(
            "UPDATE guiones SET similitud_max = ? WHERE video_id = ? AND version = "
            "(SELECT MAX(version) FROM guiones WHERE video_id = ?)",
            (sim, c.id, c.id),
        )
        if sim > c.cfg.calidad.max_similitud:
            motivos.append(
                f"similitud {sim:.2f} con guiones anteriores (> {c.cfg.calidad.max_similitud}): "
                "cambia estructura, gancho y enfoque"
            )
        if motivos:
            log("guion_rechazado", "warning", slug=c.slug, intento=intento + 1, motivos=motivos)
            continue
        ok, motivos = verificacion.verificar(c.slug, g, dossier, c.cfg, c.con, c.id, **c.kw)
        if not ok:
            log("verificacion_rechazada", "warning", slug=c.slug, intento=intento + 1, motivos=motivos)
            continue
        ok, motivos, g = tono.filtrar(c.slug, g, c.cfg, c.con, c.id, **c.kw)
        if ok:
            c.avanzar("TONO_OK")
            return
        log("tono_rechazado", "warning", slug=c.slug, intento=intento + 1, motivos=motivos)
    raise Descartar("guion no aprobado tras reintentos: " + "; ".join(motivos))


def _uso_alto(c: Contexto) -> bool:
    fila = c.con.execute("SELECT COALESCE(SUM(turnos),0) FROM uso WHERE video_id = ?", (c.id,)).fetchone()
    return fila[0] > c.cfg.uso.max_turnos_claude_por_video * 0.6


def paso_voz(c: Contexto) -> None:
    g = almacen.leer_json(almacen.guion(c.slug))
    tts.locutar(c.slug, g, c.cfg, tts.crear(c.cfg, c.simulado), c.con, c.id)
    c.avanzar("VOZ_OK")


def paso_visuales(c: Contexto) -> None:
    permitidas = c.cfg.visuales.get("licencias_permitidas", ["PD", "CC0"])
    if c.simulado:
        publicos, ia = visuales.Simulado(), None
    else:
        publicos = visuales.Commons(permitidas)
        ia = visuales.CloudflareFlux(c.cfg) if os.environ.get("CLOUDFLARE_API_TOKEN") else None
    imgs = visuales.conseguir(
        c.slug, c.tiempos(), c.cfg, c.con, c.id, publicos, ia, uso.imagenes_ia_restantes(c.cfg, c.con)
    )
    almacen.guardar_json(almacen.media(c.slug) / "imagenes.json", imgs)
    c.avanzar("VISUALES_OK")


def paso_audio(c: Contexto) -> None:
    audio.mezclar(c.slug, c.cfg, c.con, c.id)
    c.avanzar("AUDIO_OK")


def paso_montaje(c: Contexto) -> None:
    imgs = almacen.leer_json(almacen.media(c.slug) / "imagenes.json")
    montaje.montar(c.slug, c.tiempos(), imgs, c.cfg)
    c.avanzar("MONTADO")


def paso_metadatos(c: Contexto) -> None:
    g = almacen.leer_json(almacen.guion(c.slug))
    dossier = almacen.leer_json(almacen.dossier(c.slug))
    metadatos.componer(
        c.slug, g, dossier, c.tiempos(), c.cfg, c.con, c.id, desfase=montaje.desfase_intro(), **c.kw
    )
    c.avanzar("METADATOS_OK")


def paso_miniaturas(c: Contexto) -> None:
    m = almacen.leer_json(almacen.media(c.slug) / "metadatos.json")
    imgs = [Path(i["ruta"]) for i in almacen.leer_json(almacen.media(c.slug) / "imagenes.json")]
    bases = list(dict.fromkeys([imgs[0], imgs[len(imgs) // 2], imgs[-1]]))
    miniaturas.generar(c.slug, bases, m["textos_miniatura"])
    c.avanzar("MINIATURAS_OK")


def paso_short(c: Contexto) -> None:
    short.generar(c.slug, c.tiempos(), c.cfg, almacen.media(c.slug) / "final.mp4", montaje.desfase_intro())
    c.avanzar("SHORT_OK")


def paso_qa(c: Contexto) -> None:
    m = almacen.leer_json(almacen.media(c.slug) / "metadatos.json")
    try:
        qa.revisar(
            c.slug,
            c.tiempos(),
            almacen.media(c.slug) / "final.mp4",
            m,
            c.cfg,
            c.con,
            c.id,
            revision_visual=not c.simulado,
            **c.kw,
        )
    except qa.FalloQA as e:
        intentos = db.video(c.con, c.slug)["intentos_qa"] + 1
        db.actualizar_video(c.con, c.slug, intentos_qa=intentos, motivos=e.motivos)
        if intentos > c.cfg.calidad.max_reintentos:
            raise Descartar("QA no aprobado tras reintentos: " + "; ".join(e.motivos)) from e
        destino = e.repetir
        log("qa_rechazado", "warning", slug=c.slug, intento=intentos, repetir_desde=destino, motivos=e.motivos)
        c.avanzar(destino)
        return
    c.avanzar("QA_OK", veredicto_auto="aprobado")


def paso_subir(c: Contexto) -> None:
    from src import publicar

    vid = publicar.subir_privado(c.slug)
    c.avanzar("ESPERANDO_PUBLICACION", youtube_id=vid)


PASOS = {
    "PENDIENTE": paso_investigar,
    "INVESTIGADO": paso_guion,
    "TONO_OK": paso_voz,
    "VOZ_OK": paso_visuales,
    "VISUALES_OK": paso_audio,
    "AUDIO_OK": paso_montaje,
    "MONTADO": paso_metadatos,
    "METADATOS_OK": paso_miniaturas,
    "MINIATURAS_OK": paso_short,
    "SHORT_OK": paso_qa,
    "QA_OK": paso_subir,
}


# ---------- ejecución ----------


def _en_curso(con: sqlite3.Connection) -> sqlite3.Row | None:
    marcas = ",".join("?" * len(TERMINALES))
    return con.execute(
        f"SELECT * FROM videos WHERE estado NOT IN ({marcas}) ORDER BY id LIMIT 1", tuple(TERMINALES)
    ).fetchone()


def _tema(slug: str) -> dict[str, str]:
    for f in ideacion.leer_backlog():
        if f["slug"] == slug:
            return f
    return {"slug": slug, "titulo_trabajo": slug.replace("-", " ")}


def _resultado(
    slug: str | None, estado: str, con: sqlite3.Connection, motivos: list[str], video_id: int | None = None
) -> dict[str, Any]:
    fila = db.video(con, slug) if slug else None
    usos = con.execute(
        "SELECT COALESCE(SUM(llamadas),0) l, COALESCE(SUM(turnos),0) t, "
        "COALESCE(SUM(caracteres_tts),0) c FROM uso WHERE video_id = ?",
        (video_id,),
    ).fetchone()
    r = {
        "slug": slug or "",
        "video_id": fila["youtube_id"] if fila else None,
        "estado": estado,
        "uso": {"llamadas_claude": usos["l"], "turnos_claude": usos["t"], "caracteres_tts": usos["c"]},
        "motivos": motivos,
        "coste": 0,
    }
    almacen.guardar_json(dir_estado() / "ultimo_resultado.json", r)
    return r


def ejecutar(
    tema: str | None = None,
    simulado: bool = False,
    hasta: str | None = None,
    subir: bool = True,
    run_id: str = "",
    **kw: Any,
) -> dict[str, Any]:
    cfg = config()
    con = db.conectar()
    fila = db.video(con, tema) if tema else _en_curso(con)
    if fila is None:
        motivos = [] if (tema or simulado) else uso.comprobar(cfg, con)
        if motivos:
            log("omitido_por_uso", motivos=motivos)
            return _resultado(None, "OMITIDO", con, motivos)
        elegido = _tema(tema) if tema else ideacion.elegir(cfg, con)
        if elegido is None:
            enviar("⚠️ El backlog no tiene temas pendientes.")
            return _resultado(None, "SIN_TEMAS", con, ["backlog sin temas pendientes"])
        fila = db.crear_video(
            con, elegido["slug"], ideacion.elegir_plantilla(cfg, con, elegido.get("plantilla", ""))
        )
        if ideacion.ruta_backlog().exists():
            ideacion.marcar_tema(elegido["slug"], "EN_CURSO")
    c = Contexto(cfg, con, fila, _tema(fila["slug"]), simulado, kw)
    trabajo = con.execute(
        "INSERT INTO trabajos (run_id, video_id, inicio, estado) VALUES (?, ?, ?, 'EN_CURSO')",
        (run_id or os.environ.get("GITHUB_RUN_ID", "local"), c.id, db.ahora()),
    ).lastrowid
    con.commit()
    log("inicio", slug=c.slug, estado=c.estado, simulado=simulado)
    try:
        while c.estado in PASOS:
            estado = c.estado
            if estado == "QA_OK" and (simulado or not subir):
                break
            inicio = db.ahora()
            PASOS[estado](c)
            con.execute(
                "INSERT INTO pasos (trabajo_id, paso, intento, estado, inicio, fin) VALUES (?, ?, 1, 'OK', ?, ?)",
                (trabajo, estado, inicio, db.ahora()),
            )
            con.commit()
            if hasta and c.paso_hecho(hasta):
                break
    except Descartar as e:
        c.avanzar("DESCARTADO", motivos=[str(e)])
        if ideacion.ruta_backlog().exists():
            ideacion.marcar_tema(c.slug, "DESCARTADO", str(e)[:200])
        _cerrar(con, trabajo, "DESCARTADO", str(e))
        enviar(f"🗑️ Descartado {c.slug}: {e}")
        return _resultado(c.slug, "DESCARTADO", con, [str(e)], c.id)
    except claude_cli.CuotaAgotada as e:
        _cerrar(con, trabajo, "PAUSADO_CUOTA", str(e))
        enviar(f"⏸️ Cuota de Claude agotada en {c.slug} ({c.estado}); se reanuda en el siguiente run.")
        return _resultado(c.slug, "PAUSADO_CUOTA", con, [str(e)], c.id)
    except Exception as e:
        _cerrar(con, trabajo, "ERROR", f"{type(e).__name__}: {e}")
        errores = con.execute(
            "SELECT estado FROM trabajos WHERE video_id = ? ORDER BY id DESC LIMIT ?", (c.id, MAX_ERRORES_SEGUIDOS)
        ).fetchall()
        if len(errores) == MAX_ERRORES_SEGUIDOS and all(r["estado"] == "ERROR" for r in errores):
            c.avanzar("BLOQUEADO", motivos=[str(e)[:500]])
        log("error", "error", slug=c.slug, estado=c.estado, error=f"{type(e).__name__}: {e}")
        _resultado(c.slug, "ERROR", con, [f"{type(e).__name__}: {e}"[:500]], c.id)
        raise
    _cerrar(con, trabajo, "OK", None)
    estado = c.estado
    if estado == "ESPERANDO_PUBLICACION" and ideacion.ruta_backlog().exists():
        ideacion.marcar_tema(c.slug, "PRODUCIDO")
    return _resultado(c.slug, estado, con, [], c.id)


def _cerrar(con: sqlite3.Connection, trabajo: int, estado: str, error: str | None) -> None:
    con.execute(
        "UPDATE trabajos SET fin = ?, estado = ?, error = ? WHERE id = ?",
        (db.ahora(), estado, error, trabajo),
    )
    con.commit()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tema", default="")
    p.add_argument("--simulado", action="store_true")
    p.add_argument("--hasta", choices=ORDEN)
    p.add_argument("--sin-subir", action="store_true")
    a = p.parse_args(argv)
    try:
        r = ejecutar(a.tema.strip() or None, a.simulado, a.hasta, not a.sin_subir)
    except Exception as e:
        enviar(f"⚠️ Fallo del pipeline: {type(e).__name__}: {str(e)[:300]}")
        return 1
    print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
