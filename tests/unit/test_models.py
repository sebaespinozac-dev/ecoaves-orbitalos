from __future__ import annotations

import pytest

from core.models import (
    SCENE_SCHEMA_VERSION,
    SOURCE_CUBESAT_UA,
    SOURCE_NASA_EARTHDATA,
    GranuleRef,
    Observation,
    Provenance,
    ProvenanceError,
    Scene,
)


def _prov(**overrides) -> Provenance:
    data = dict(
        source=SOURCE_NASA_EARTHDATA,
        product_id="VJ146A1",
        granule_id="VJ146A1.A2026001.h08v05.002.2026003120000.h5",
        acquisition_time="2026-01-01T00:00:00Z",
        retrieval_time="2026-01-02T00:00:00Z",
        license="NASA ESDIS open data",
        processing_level="Level-3",
        schema_version=SCENE_SCHEMA_VERSION,
    )
    data.update(overrides)
    return Provenance(**data)


def test_provenance_rejects_unknown_source() -> None:
    with pytest.raises(ProvenanceError, match="source no reconocido"):
        _prov(source="landsat_invented")


def test_provenance_rejects_empty_product_id() -> None:
    with pytest.raises(ProvenanceError, match="product_id"):
        _prov(product_id=" ")


def test_provenance_rejects_other_schema_version() -> None:
    with pytest.raises(ProvenanceError, match="schema_version"):
        _prov(schema_version="v0")


def test_scene_requires_provenance() -> None:
    scene = Scene(
        scene_id="s1",
        provenance=_prov(),
        georeferenced=True,
        spatial=None,
        observations=(Observation("x", 1, None, "none"),),
        payload={"synthetic": True},
    )
    assert scene.provenance.source == SOURCE_NASA_EARTHDATA
    cited = scene.cite("x")
    assert cited["value"] == 1
    assert cited["provenance"]["granule_id"] == scene.provenance.granule_id


def test_scene_cite_missing_observation() -> None:
    scene = Scene(
        scene_id="s1",
        provenance=_prov(),
        georeferenced=False,
        spatial=None,
        observations=(),
        payload={},
    )
    with pytest.raises(KeyError):
        scene.cite("flagged_pct")


def test_non_georeferenced_scene_cannot_carry_extent() -> None:
    from core.models import SpatialExtent

    with pytest.raises(ProvenanceError, match="no geo-referenciada"):
        Scene(
            scene_id="ua-1",
            provenance=_prov(source=SOURCE_CUBESAT_UA, product_id="CAP001", granule_id="CAP001"),
            georeferenced=False,
            spatial=SpatialExtent("EPSG:4326", (-71.0, -24.0, -70.0, -23.0), "invented"),
            observations=(),
            payload={},
        )


def test_granule_ref_requires_uri() -> None:
    with pytest.raises(ProvenanceError, match="uri"):
        GranuleRef(
            source=SOURCE_NASA_EARTHDATA,
            product_id="VJ146A1",
            granule_id="g",
            uri="",
            extra={},
        )
