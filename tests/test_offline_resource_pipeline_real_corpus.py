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

    validation = coverage["validation"]
    assert validation["total"] == len(catalog["resources"])
    assert validation["supported"] + validation["unsupported"] == validation["total"]
    assert validation["verified"] == 0
    assert validation["supported"] == validation["deferred"]
    assert validation["blocked"] == 0
    assert validation["malformed"] == 0
    assert validation["unknown_version_layout"] == 0
    assert validation["unclassified_blocked"] == 0
    assert validation["unresolved_dependency_edges"] == 0
    assert validation["unresolved_dependency_resources"] == 0
