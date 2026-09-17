"""Lluvia Matrix al 100% de densidad con los números reales del reporte DARKSKY."""

from __future__ import annotations

import json
from html import escape
from typing import Any, Iterable, Iterator

GREEN = "\033[32m"
BRIGHT = "\033[92m"
DIM = "\033[2;32m"
RESET = "\033[0m"


def glyphs_from_report(payload: dict[str, Any]) -> str:
    """Solo dígitos y símbolos que salen de datos citados, no un alfabeto inventado."""
    chars: list[str] = []
    for capture in payload.get("cubesat_ua", {}).get("captures") or ():
        pct = capture.get("flagged_pct", {}).get("value")
        chars.extend(_digits(pct))
        for cell in capture.get("cells") or ():
            chars.extend(_digits(cell.get("blue_proxy")))
            chars.extend(_digits(cell.get("row")))
            chars.extend(_digits(cell.get("col")))
    for granule in payload.get("nasa_earthdata", {}).get("granules") or ():
        chars.extend(_digits(granule.get("product_id", {}).get("value")))
    raw = "".join(ch for ch in chars if ch.isdigit() or ch in ".-")
    return raw or "01001100"


def latest_grid(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    captures = payload.get("cubesat_ua", {}).get("captures") or ()
    if not captures:
        return []
    last = captures[-1]
    cols = int(last.get("grid_cols") or 8)
    rows = int(last.get("grid_rows") or 6)
    grid = [[{} for _ in range(cols)] for _ in range(rows)]
    for cell in last.get("cells") or ():
        grid[int(cell["row"])][int(cell["col"])] = cell
    return grid


def rain_frames(
    payload: dict[str, Any],
    *,
    width: int = 64,
    height: int = 18,
    frames: int = 12,
    density: float = 1.0,
    seed: int = 46,
) -> Iterator[str]:
    """Genera fotogramas ANSI. density=1.0 = 100% de columnas activas."""
    glyphs = glyphs_from_report(payload)
    cols = max(8, width)
    active = max(1, int(round(cols * min(1.0, max(0.0, density)))))
    heads = [((seed * 17 + index * 13) % height) - height for index in range(active)]
    speeds = [1 + ((seed + index) % 3) for index in range(active)]
    grid = [[" " for _ in range(cols)] for _ in range(height)]
    for frame in range(frames):
        for col in range(active):
            heads[col] = (heads[col] + speeds[col])
            row = heads[col] % (height + 8)
            for trail in range(8):
                y = row - trail
                if 0 <= y < height:
                    glyph = glyphs[(frame * 31 + col * 7 + trail * 3) % len(glyphs)]
                    grid[y][col] = glyph
        screen = ["".join(grid[y]) for y in range(height)]
        yield _paint(screen, payload, frame=frame)


def render_html(payload: dict[str, Any], *, density: float = 1.0) -> str:
    data = json.dumps(
        {
            "density": min(1.0, max(0.0, density)),
            "glyphs": glyphs_from_report(payload),
            "batch_id": payload.get("batch_id"),
            "trend": (payload.get("cubesat_ua") or {}).get("trend"),
            "peak_level": (payload.get("cubesat_ua") or {}).get("peak_level"),
            "mean_flagged_pct": (payload.get("cubesat_ua") or {}).get("mean_flagged_pct"),
            "captures": [
                {
                    "granule_id": item["flagged_pct"]["provenance"]["granule_id"],
                    "source": item["flagged_pct"]["provenance"]["source"],
                    "level": item["level"]["value"],
                    "flagged_pct": item["flagged_pct"]["value"],
                    "cells": item.get("cells") or [],
                    "grid_cols": item.get("grid_cols"),
                    "grid_rows": item.get("grid_rows"),
                }
                for item in (payload.get("cubesat_ua") or {}).get("captures") or ()
            ],
            "nasa": [
                {
                    "product": item["product_id"]["value"],
                    "granule_id": item["product_id"]["provenance"]["granule_id"],
                    "source": item["product_id"]["provenance"]["source"],
                }
                for item in (payload.get("nasa_earthdata") or {}).get("granules") or ()
            ],
        },
        ensure_ascii=False,
    )
    return _HTML.replace("__DATA__", data).replace("__TITLE__", escape(str(payload.get("batch_id") or "DARKSKY")))


def _digits(value: Any) -> Iterable[str]:
    if value is None:
        return ()
    return [ch for ch in str(value) if ch.isdigit() or ch in ".-"]


def _paint(screen: list[str], payload: dict[str, Any], *, frame: int) -> str:
    ua = payload.get("cubesat_ua") or {}
    header = (
        f"{BRIGHT}ECOAVES OrbitalOS  MATRIX 100%  lote={payload.get('batch_id')}  "
        f"tendencia={ua.get('trend')}  pico={ua.get('peak_level')}  "
        f"flagged_pct_medio={ua.get('mean_flagged_pct')}  frame={frame}{RESET}"
    )
    body = "\n".join(f"{GREEN}{line}{RESET}" for line in screen)
    grid = latest_grid(payload)
    grid_lines = []
    if grid:
        grid_lines.append(f"{DIM}grilla escena (relativa, no geo) última captura:{RESET}")
        for row in grid:
            cells = []
            for cell in row:
                if not cell:
                    cells.append(" .... ")
                    continue
                value = f"{float(cell['blue_proxy']):.2f}"
                cells.append(f"{BRIGHT}{value}{RESET}" if cell.get("flagged") else f"{DIM}{value}{RESET}")
            grid_lines.append(" ".join(cells))
    return header + "\n" + body + "\n" + "\n".join(grid_lines) + "\n"


_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>OrbitalOS Matrix 100% — __TITLE__</title>
  <style>
    html, body { margin: 0; height: 100%; background: #000; color: #6f6; font-family: ui-monospace, monospace; overflow: hidden; }
    canvas { display: block; width: 100%; height: 100%; }
    #hud {
      position: absolute; inset: auto 16px 16px 16px; display: grid;
      grid-template-columns: 1fr 1fr; gap: 16px; pointer-events: none;
    }
    .panel { background: rgba(0,20,0,.72); border: 1px solid #0f0; padding: 12px 14px; }
    h1 { margin: 0 0 8px; font-size: 14px; letter-spacing: .12em; color: #9f9; }
    .grid { display: grid; gap: 3px; }
    .cell { font-size: 12px; text-align: center; padding: 4px 0; background: #031; }
    .cell.flagged { background: #140; color: #cfffcf; text-shadow: 0 0 8px #6f6; }
    .meta { font-size: 12px; line-height: 1.45; color: #8d8; }
  </style>
</head>
<body>
<canvas id="rain"></canvas>
<div id="hud">
  <div class="panel">
    <h1>CUBESAT UA · ESCENA RELATIVA · 100%</h1>
    <div id="matrix-grid" class="grid"></div>
  </div>
  <div class="panel">
    <h1>PROCEDENCIA</h1>
    <div id="meta" class="meta"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const canvas = document.getElementById("rain");
const ctx = canvas.getContext("2d");
const glyphs = DATA.glyphs || "01001100";
let width, height, font = 16, columns, drops, speeds;

function resize() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
  columns = Math.max(8, Math.floor(width / font));
  const active = Math.max(1, Math.round(columns * (DATA.density ?? 1)));
  drops = Array.from({length: columns}, (_, i) => i < active ? Math.random() * height / font : null);
  speeds = Array.from({length: columns}, (_, i) => 0.65 + (i % 3) * 0.35);
}
window.addEventListener("resize", resize);
resize();

function tick() {
  ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
  ctx.fillRect(0, 0, width, height);
  ctx.font = font + "px monospace";
  for (let i = 0; i < columns; i++) {
    if (drops[i] == null) continue;
    const ch = glyphs[Math.floor((drops[i] * 13 + i * 7) % glyphs.length)];
    ctx.fillStyle = "#9fff9f";
    ctx.fillText(ch, i * font, drops[i] * font);
    ctx.fillStyle = "#0f0";
    const trail = glyphs[Math.floor((drops[i] * 7 + i) % glyphs.length)];
    ctx.fillText(trail, i * font, (drops[i] - 1.2) * font);
    drops[i] += speeds[i];
    if (drops[i] * font > height) drops[i] = -Math.random() * 8;
  }
  requestAnimationFrame(tick);
}
tick();

const last = (DATA.captures || [])[DATA.captures.length - 1];
const host = document.getElementById("matrix-grid");
if (last) {
  host.style.gridTemplateColumns = `repeat(${last.grid_cols || 8}, 1fr)`;
  const cols = last.grid_cols || 8;
  const rows = last.grid_rows || 6;
  const series = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      series.push((DATA.captures || []).map(cap => {
        const cell = (cap.cells || []).find(x => x.row === r && x.col === c) || {blue_proxy: 0, flagged: false};
        return cell;
      }));
    }
  }
  const nodes = series.map((values, index) => {
    const el = document.createElement("div");
    el.className = "cell";
    host.appendChild(el);
    return {el, values};
  });
  let step = 0;
  function paintGrid() {
    const t = step % Math.max(1, (DATA.captures || []).length);
    nodes.forEach(({el, values}) => {
      const cell = values[t] || {blue_proxy: 0, flagged: false};
      el.className = "cell" + (cell.flagged ? " flagged" : "");
      el.textContent = Number(cell.blue_proxy || 0).toFixed(2);
    });
    step += 1;
  }
  paintGrid();
  setInterval(paintGrid, 420);
}
document.getElementById("meta").innerHTML = [
  `lote ${DATA.batch_id || ""} · tendencia ${DATA.trend || "n/a"} · pico ${DATA.peak_level || "n/a"}`,
  `flagged_pct medio ${DATA.mean_flagged_pct ?? "n/a"} (CubeSat, scene_relative)`,
  `densidad lluvia ${(DATA.density * 100).toFixed(0)}% — cada columna activa`,
  ...(DATA.captures || []).map(c => `${c.granule_id}: ${c.level} ${c.flagged_pct}% ← ${c.source}`),
  ...(DATA.nasa || []).map(n => `${n.product} ${n.granule_id} ← ${n.source}`),
  "Sentinel no usado en DARKSKY. Posiciones CubeSat no son geo."
].join("<br/>");
</script>
</body>
</html>
"""
