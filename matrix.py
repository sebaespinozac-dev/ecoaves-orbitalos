#!/usr/bin/env python3
"""
Lluvia estilo Matrix (Pygame).

Por defecto: 1280x720, caracteres verdes cayendo en columnas.
Con --report: los glifos y la grilla 8x6 salen del JSON DARKSKY (números citados).

    pip install pygame
    python3 matrix.py
    python3 matrix.py --fullscreen
    python3 matrix.py --report var/reports/DEMO.darksky.json
    MATRIX_SECONDS=4 python3 matrix.py

Teclas: ESC / Q sale · F pantalla completa.

pygame es opcional: el resto de OrbitalOS no lo importa. Este script sí.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None  # type: ignore[assignment]

ANCHO_VENTANA = 1280
ALTO_VENTANA = 720
FPS = 60
TAM_FUENTE = 20
KATAKANA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
ASCII = "0123456789ABCDEF"
COLOR_CUERPO = (0, 180, 40)
COLOR_PUNTA = (180, 255, 180)
FONDO = (0, 0, 0)
HUD_INTERVALO_S = 0.45


def _require_pygame():
    if pygame is None:
        raise SystemExit(
            "pygame no está instalado. Instálalo con: pip install pygame"
        )
    return pygame


class Columna:
    """Una columna que cae a su propia velocidad y vuelve a nacer abajo."""

    def __init__(self, x: int, alto: int, fuente: Any, alfabeto: str) -> None:
        self.x = x
        self.alto = alto
        self.fuente = fuente
        self.alfabeto = alfabeto
        self._reiniciar(arriba=True)

    def _glifo(self) -> str:
        return random.choice(self.alfabeto)

    def _reiniciar(self, *, arriba: bool) -> None:
        self.largo = random.randint(8, 22)
        self.velocidad = random.uniform(4.0, 14.0)
        self.simbolos = [self._glifo() for _ in range(self.largo)]
        tope = -self.largo * TAM_FUENTE
        self.y = tope if arriba else random.uniform(tope, 0)

    def actualizar(self, dt: float) -> None:
        self.y += self.velocidad * dt * 60.0
        if random.random() < 0.15:
            self.simbolos[random.randrange(self.largo)] = self._glifo()
        cola = self.y - self.largo * TAM_FUENTE
        if cola > self.alto:
            self._reiniciar(arriba=True)

    def dibujar(self, superficie: Any) -> None:
        for i, simbolo in enumerate(self.simbolos):
            py = int(self.y - i * TAM_FUENTE)
            if py < -TAM_FUENTE or py > self.alto:
                continue
            if i == 0:
                color = COLOR_PUNTA
            elif i < 3:
                color = COLOR_CUERPO
            else:
                fade = max(20, 140 - i * 8)
                color = (0, fade, 20)
            superficie.blit(self.fuente.render(simbolo, True, color), (self.x, py))


def cargar_fuente(tamano: int) -> Any:
    """Fuente con katakana si existe, para no dibujar recuadros vacíos."""
    pg = _require_pygame()
    for ruta in (
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ):
        if os.path.isfile(ruta):
            return pg.font.Font(ruta, tamano)
    return pg.font.SysFont("dejavusansmono,consolas,monospace", tamano, bold=True)


def cargar_fuente_hud(tamano: int) -> Any:
    """HUD: dígitos ASCII nítidos (no CJK) para blue_proxy / flagged_pct citados."""
    pg = _require_pygame()
    return pg.font.SysFont("dejavusansmono,consolas,monospace", tamano, bold=True)


def crear_ventana(fullscreen: bool) -> Any:
    pg = _require_pygame()
    flags = pg.FULLSCREEN if fullscreen else 0
    size = (0, 0) if fullscreen else (ANCHO_VENTANA, ALTO_VENTANA)
    pantalla = pg.display.set_mode(size, flags)
    pg.display.set_caption("Matrix — ECOAVES OrbitalOS")
    return pantalla


def armar_columnas(ancho: int, alto: int, fuente: Any, alfabeto: str) -> list[Columna]:
    columnas = []
    for x in range(0, ancho, TAM_FUENTE):
        col = Columna(x, alto, fuente, alfabeto)
        col.y = random.uniform(-alto, alto)
        columnas.append(col)
    return columnas


def alfabeto_para(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ASCII + KATAKANA
    from apps.darksky.matrix import glyphs_from_report

    datos = glyphs_from_report(payload)
    return (datos or ASCII) + KATAKANA


def captura_hud(payload: dict[str, Any], tiempo: float) -> dict[str, Any] | None:
    """Captura real del lote según el tiempo. No interpola ni inventa valores."""
    captures = (payload.get("cubesat_ua") or {}).get("captures") or []
    if not captures:
        return None
    idx = int(tiempo / HUD_INTERVALO_S) % len(captures)
    captura = captures[idx]
    return {"index": idx, "total": len(captures), "captura": captura}


def celdas_por_posicion(captura: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    return {(int(c["row"]), int(c["col"])): c for c in captura.get("cells") or []}


def dibujar_hud(
    superficie: Any,
    fuente: Any,
    fuente_ui: Any,
    payload: dict[str, Any],
    tiempo: float,
) -> None:
    """Grilla 8x6 del lote: recorre capturas reales (no inventa valores)."""
    pg = _require_pygame()
    frame = captura_hud(payload, tiempo)
    if frame is None:
        return
    idx = frame["index"]
    captura = frame["captura"]
    cols = int(captura.get("grid_cols") or 8)
    rows = int(captura.get("grid_rows") or 6)
    margen = 24
    celda = 48
    panel_w = max(cols * celda + 24, 640)
    panel_h = rows * celda + 78
    panel = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
    panel.fill((0, 24, 0, 210))
    pg.draw.rect(panel, COLOR_CUERPO, panel.get_rect(), 1)

    pct = captura.get("flagged_pct", {}).get("value")
    level = captura.get("level", {}).get("value")
    granulo = (captura.get("flagged_pct") or {}).get("provenance", {}).get("granule_id", "")
    ua = payload.get("cubesat_ua") or {}
    lineas = [
        f"LOTE {payload.get('batch_id')}  {idx + 1}/{frame['total']}  {granulo}",
        f"level={level}  flagged_pct={pct}  tendencia={ua.get('trend')}  scene_relative",
    ]
    y = 6
    for texto in lineas:
        panel.blit(fuente_ui.render(texto, True, COLOR_PUNTA), (10, y))
        y += 16

    celdas = celdas_por_posicion(captura)
    origin_y = 42
    for row in range(rows):
        for col in range(cols):
            cell = celdas.get((row, col))
            rx = 12 + col * celda
            ry = origin_y + row * celda
            flagged = bool(cell.get("flagged")) if cell else False
            color = COLOR_PUNTA if flagged else COLOR_CUERPO
            pg.draw.rect(panel, (0, 40, 0) if flagged else (0, 18, 0), (rx, ry, celda - 4, celda - 4))
            pg.draw.rect(panel, color, (rx, ry, celda - 4, celda - 4), 1)
            if cell is None:
                valor = "—"
            else:
                valor = f"{float(cell['blue_proxy']):.2f}"
            panel.blit(fuente.render(valor, True, color), (rx + 4, ry + 10))

    superficie.blit(panel, (margen, superficie.get_height() - panel_h - margen))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pantalla Matrix con Pygame")
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--report", help="JSON DARKSKY (números reales del lote)")
    args = parser.parse_args(argv)

    payload = None
    if args.report:
        payload = json.loads(Path(args.report).read_text(encoding="utf-8"))

    pg = _require_pygame()
    limite = float(os.environ.get("MATRIX_SECONDS", "0") or 0)
    pg.init()
    pg.mouse.set_visible(False)
    pantalla = crear_ventana(args.fullscreen)
    reloj = pg.time.Clock()
    fuente = cargar_fuente(TAM_FUENTE)
    fuente_hud = cargar_fuente_hud(13)
    fuente_ui = cargar_fuente_hud(14)
    alfabeto = alfabeto_para(payload)
    ancho, alto = pantalla.get_size()
    columnas = armar_columnas(ancho, alto, fuente, alfabeto)
    fullscreen = args.fullscreen
    transcurrido = 0.0
    corriendo = True

    while corriendo:
        dt = reloj.tick(FPS) / 1000.0
        transcurrido += dt
        for evento in pg.event.get():
            if evento.type == pg.QUIT:
                corriendo = False
            elif evento.type == pg.KEYDOWN:
                if evento.key in (pg.K_ESCAPE, pg.K_q):
                    corriendo = False
                elif evento.key == pg.K_f:
                    fullscreen = not fullscreen
                    pantalla = crear_ventana(fullscreen)
                    ancho, alto = pantalla.get_size()
                    columnas = armar_columnas(ancho, alto, fuente, alfabeto)

        if limite and transcurrido >= limite:
            corriendo = False

        velo = pg.Surface(pantalla.get_size())
        velo.set_alpha(40)
        velo.fill(FONDO)
        pantalla.blit(velo, (0, 0))
        for col in columnas:
            col.actualizar(dt)
            col.dibujar(pantalla)
        if payload:
            dibujar_hud(pantalla, fuente_hud, fuente_ui, payload, transcurrido)
        pg.display.flip()

    pg.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
