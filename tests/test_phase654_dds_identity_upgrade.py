from __future__ import annotations

import bmw_playable_render_resource_identity as gate


def test_phase654_legacy_dds_claim_may_omit_index_before_unique_occurrence_scan():
    claim, blockers = gate._claim(
        kind="texture-0",
        primitive_index=3,
        raw={
            "archive": "BMW_M3_E36.bff",
            "path": "vehicles/bmw_m3_e36/common_paint.dds",
            "sha256": "a" * 64,
        },
        require_index=False,
    )

    assert blockers == []
    assert claim is not None
    assert claim["index"] is None
    assert claim["normalized_path"] == "vehicles/bmw_m3_e36/common_paint.dds"


def test_phase654_non_dds_resource_still_requires_emitted_entry_index():
    claim, blockers = gate._claim(
        kind="material",
        primitive_index=3,
        raw={
            "archive": "BMW_M3_E36.bff",
            "path": "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
            "sha256": "b" * 64,
        },
    )

    assert claim is None
    assert blockers == ["phase654:primitive-3:material:entry-index-invalid"]
