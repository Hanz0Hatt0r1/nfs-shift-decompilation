from bmw_golden_manifest import build_golden_manifest, select_bmw_resource


def test_bmw_golden_manifest_selects_exact_resource():
    row = {
        "id": "resource-id",
        "collector_version": "115.0",
        "source": {
            "archive": "Pakfiles/Vehicles/BMW_M3_E36.bff",
            "root_relative_path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "resource_sha256": "abc",
            "resource_size": 300764,
            "entry_index": 863,
        },
        "mesh": {
            "name": "BMW_M3_E36_KIT00_BODY_LODA",
            "vertex_count": 3550,
            "triangle_count": 5034,
            "property_descriptors": [
                {"id": "200", "words": [2, 0, 0]},
                {"id": "460", "words": [4, 6, 0]},
                {"id": "220", "words": [2, 2, 0]},
                {"id": "240", "words": [2, 4, 0]},
                {"id": "250", "words": [2, 5, 0]},
                {"id": "130", "words": [1, 3, 0]},
                {"id": "132", "words": [1, 3, 2]},
                {"id": "133", "words": [1, 3, 3]},
            ],
            "property_layouts": [
                {"id": "200"}, {"id": "460"}, {"id": "220"}, {"id": "240"},
                {"id": "250"}, {"id": "130"}, {"id": "132"}, {"id": "133"},
            ],
            "primitives": [{"first_index": 0, "index_count": 3, "material": "x.mtx"}],
            "skinning": {"skinned": False},
        },
    }
    selected = select_bmw_resource([row])
    assert selected is row
    manifest = build_golden_manifest(row, source_bundle="bundle.zip")
    assert manifest["golden"]["resource_sha256"] == "abc"
    assert manifest["mesh"]["vertex_count"] == 3550
    assert manifest["mesh"]["color460_descriptor"]["words"] == [4, 6, 0]
    descriptors = {
        row["id"]: row["words"]
        for row in manifest["mesh"]["property_descriptors"]
    }
    assert descriptors["200"] == [2, 0, 0]
    assert descriptors["460"] == [4, 6, 0]
    assert descriptors["220"] == [2, 2, 0]
    assert descriptors["240"] == [2, 4, 0]
    assert descriptors["250"] == [2, 5, 0]
    assert descriptors["130"] == [1, 3, 0]
    assert descriptors["132"] == [1, 3, 2]
    assert descriptors["133"] == [1, 3, 3]
    assert manifest["render_requirements"]["runtime_archive_access"] is False
