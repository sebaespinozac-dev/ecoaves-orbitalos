from __future__ import annotations

import pytest

from apps.darksky import DarkskyApp
from apps.darksky.matrix import glyphs_from_report, rain_frames, render_html
from core.models import SOURCE_CUBESAT_UA
from datahub.adapter import DiscoverCriteria
from matrix import alfabeto_para, captura_hud, celdas_por_posicion
from simulators.memory import cubesat_adapter, nasa_adapter


def _report():
    scenes = []
    for adapter in (nasa_adapter(), cubesat_adapter()):
        for ref in adapter.discover(DiscoverCriteria()):
            if adapter.source == SOURCE_CUBESAT_UA and "schema-sample" in ref.granule_id:
                continue
            scenes.append(adapter.normalize(adapter.fetch(ref)))
    return DarkskyApp().process(scenes, batch_id="MX")


def test_matrix_glyphs_are_the_report_numbers() -> None:
    payload = _report().payload
    glyphs = glyphs_from_report(payload)
    assert any(ch.isdigit() for ch in glyphs)
    last = payload["cubesat_ua"]["captures"][-1]
    assert last["cells"]
    assert last["cells"][0]["position_frame"] == "scene_relative"
    assert str(int(float(last["flagged_pct"]["value"])))[0] in glyphs


def test_matrix_rain_is_full_density_and_moves() -> None:
    payload = _report().payload
    frames = list(rain_frames(payload, width=24, height=8, frames=4, density=1.0, seed=1))
    assert len(frames) == 4
    assert frames[0] != frames[-1]
    assert "MATRIX 100%" in frames[0]
    body_lines = [line for line in frames[0].splitlines() if "MATRIX" not in line and "grilla" not in line]
    raining = [line for line in body_lines if any(ch.isdigit() for ch in line)]
    assert raining


def test_matrix_html_embeds_cited_numbers() -> None:
    payload = _report().payload
    html = render_html(payload, density=1.0)
    assert "requestAnimationFrame" in html
    assert payload["batch_id"] in html
    assert "cubesat_ua" in html
    assert str(payload["cubesat_ua"]["captures"][-1]["flagged_pct"]["value"]) in html


def test_pygame_alphabet_uses_report_digits() -> None:
    payload = _report().payload
    alphabet = alfabeto_para(payload)
    assert any(ch.isdigit() for ch in alphabet)
    assert str(payload["cubesat_ua"]["captures"][0]["flagged_pct"]["value"])[0] in alphabet
    assert glyphs_from_report(payload) in alphabet


def test_pygame_hud_cycles_real_capture_cells() -> None:
    payload = _report().payload
    captures = payload["cubesat_ua"]["captures"]
    assert captures
    first = captura_hud(payload, 0.0)
    later = captura_hud(payload, 0.45 * (len(captures) + 1))
    assert first is not None and later is not None
    assert first["captura"] is captures[0]
    assert later["captura"] is captures[1 % len(captures)]
    cell = first["captura"]["cells"][0]
    assert cell["position_frame"] == "scene_relative"
    assert cell["geo_referenced"] is False
    keyed = celdas_por_posicion(first["captura"])
    assert keyed[(int(cell["row"]), int(cell["col"]))]["blue_proxy"] == cell["blue_proxy"]


def test_pygame_optional_extra() -> None:
    pytest.importorskip("pygame")
    from matrix import _require_pygame

    assert _require_pygame() is not None
