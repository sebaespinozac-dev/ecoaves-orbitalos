"""Hito 6: documentación y molde presentes; FIRE/TAILINGS/RAVINE no implementados."""

from __future__ import annotations

from pathlib import Path

from apps import default_registry

ROOT = Path(__file__).resolve().parents[2]


def test_hito6_docs_exist() -> None:
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    gaps = (ROOT / "docs" / "gaps.md").read_text(encoding="utf-8")
    template = (ROOT / "apps" / "_template" / "README.md").read_text(encoding="utf-8")
    assert "Fuentes" in architecture and "DataHub" in architecture
    assert "software de vuelo" in architecture.lower()
    assert "geo-referenciación" in gaps.lower() or "geo-referenciacion" in gaps.lower()
    assert "2026-11-01" in gaps
    assert "marzo 2026" in gaps.lower()
    assert "luces nocturnas" in gaps.lower()
    assert "cuotas" in gaps.lower()
    assert "FIRE" in template and "TAILINGS" in template and "RAVINE" in template
    assert "no" in template.lower()


def test_future_apps_not_registered_or_packaged() -> None:
    names = set(default_registry().names())
    assert names == {"darksky"}
    for app in ("fire", "tailings", "ravine"):
        assert not (ROOT / "apps" / app).exists()
        assert not (ROOT / "apps" / f"{app}.py").exists()
