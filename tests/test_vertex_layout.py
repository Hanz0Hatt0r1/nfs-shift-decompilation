from vertex_layout import build_vertex_layout

def test_known_float_and_skin_attributes():
    r=build_vertex_layout(["200","220","130","310","580"])
    a={x["property_id"]:x for x in r["attributes"]}
    assert a["200"]["android"]=="FLOAT32x3"
    assert (a["310"]["usage"],a["310"]["usage_index"])==("BLENDWEIGHT",0)
    assert a["580"]["android"]=="UINT8x4"
    assert a["580"]["name"]=="bone_indices"

def test_color_uses_source_correlated_d3d9_abi():
    r=build_vertex_layout(["460"])
    a=r["attributes"][0]
    assert a["d3d9"] == "D3DCOLOR"
    assert set(a["d3d9_candidates"]) == {"D3DCOLOR", "UBYTE4N"}
    assert a["normalized"] is True
    assert a["abi_status"] == "proven"
    assert a["channel_order"] == "BGRA"
    assert a["shader_order"] == "RGBA"


def test_color_keeps_alternate_candidates_for_forensics():
    r=build_vertex_layout(["460","461"])
    by={x["property_id"]:x for x in r["attributes"]}
    for pid in ("460","461"):
        assert by[pid]["channel_order_candidates"] == ["BGRA"]
        assert set(by[pid]["android_candidates"]) == {"UINT8x4_RGBA","UINT8x4_BGRA"}
        assert by[pid]["channel_order"] == "BGRA"


def test_vertex_layout_exposes_deterministic_repack_offsets():
    r = build_vertex_layout(["200", "220", "130"])
    by = {x["property_id"]: x for x in r["attributes"]}
    assert by["200"]["offset"] == 0
    assert by["220"]["offset"] == 12
    assert by["130"]["offset"] == 24
    assert r["buffer_stride"] == 32


def test_vertex_abi_uses_source_correlated_color_order():
    from vertex_layout import property_abi
    abi = property_abi("460")
    assert abi["confidence"] == "exact"
    assert abi["d3d9"] == "D3DCOLOR"
    assert abi["channel_order"] == "BGRA"
    assert abi["shader_order"] == "RGBA"
    assert abi["source_evidence"]["function"] == "FUN_008310c0"
    assert abi["source_evidence"]["source_memory_order"] == "BGRA"


def test_vertex_layout_exposes_explicit_abi_evidence_status():
    r = build_vertex_layout(["200", "310", "580", "460"])
    by = {x["property_id"]: x for x in r["attributes"]}
    assert by["200"]["abi_status"] == "inferred"
    assert by["310"]["abi_status"] == "proven"
    assert by["580"]["abi_status"] == "proven"
    assert by["460"]["abi_status"] == "proven"
    assert "460" in r["evidence"]["proven_properties"]


def test_vertex_layout_reports_semantic_collisions_without_guessing():
    r = build_vertex_layout(["130", "230"])
    assert r["semantic_collisions"] == [
        {"usage": "TEXCOORD", "usage_index": 0, "property_ids": ["130", "230"]}
    ]


def test_vertex_layout_uses_consistent_unknown_abi_schema():
    r = build_vertex_layout(["999"])
    a = r["attributes"][0]
    assert a["abi_status"] == "unknown"
    assert "property id is not decoded" in a["evidence_basis"]
    from vertex_layout import property_abi
    abi = property_abi("999")
    assert abi["abi_status"] == "unknown"
