from __future__ import annotations

import os
from pathlib import Path

import pytest

import offline_resource_pipeline as pipeline


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not configured")
    path = Path(value)
    if not path.is_file():
        pytest.skip(f"{name} does not exist: {path}")
    return path


def test_real_vehicle_and_silverstone_corpus_catalog():
    vehicles = _required_path("SHIFT_REAL_VEHICLES_ZIP")
    silverstone = _required_path("SHIFT_REAL_SILVERSTONE_ZIP")
    with pipeline.materialize_bff_inputs([vehicles, silverstone]) as archives:
        catalog, graph, coverage = pipeline.build_catalog(
            archives,
            decode_known=False,
        )

    archive_names = {row["archive_name"] for row in catalog["archives"]}
    assert len(catalog["archives"]) >= 20
    assert "Ford_Mustang_2010.bff" in archive_names
    assert "Silverstone_Era3_GrandPrix.bff" in archive_names
    assert "Silverstone_Era3_GrandPrix_Physics.bff" in archive_names
    assert catalog["summary"]["extensions"][".meb"] > 0
    assert catalog["summary"]["extensions"][".bmt"] > 0
    assert catalog["summary"]["extensions"][".dds"] > 0
    assert catalog["summary"]["extensions"][".cdf"] > 0
    assert catalog["summary"]["extensions"][".aiw"] > 0
    assert graph["summary"]["edges"] == 0
    assert coverage["parsed"] == 0
