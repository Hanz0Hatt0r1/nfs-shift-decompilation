from vertex_layout import build_vertex_layout

def test_known_float_and_skin_attributes():
    r=build_vertex_layout(["200","220","130","310","580"])
    a={x["property_id"]:x for x in r["attributes"]}
    assert a["200"]["android"]=="FLOAT32x3"
    assert (a["310"]["usage"],a["310"]["usage_index"])==("BLENDWEIGHT",0)
    assert a["580"]["android"]=="UINT8x4"
    assert a["580"]["name"]=="bone_indices"

def test_color_keeps_d3d9_ambiguity():
    r=build_vertex_layout(["460"])
    a=r["attributes"][0]
    assert set(a["d3d9_candidates"])=={"D3DCOLOR","UBYTE4N"}
    assert a["normalized"] is True


def test_color_candidates_preserve_channel_order_ambiguity():
    r=build_vertex_layout(["460","461"])
    by={x["property_id"]:x for x in r["attributes"]}
    for pid in ("460","461"):
        assert by[pid]["channel_order_candidates"]==["RGBA","BGRA"]
        assert set(by[pid]["android_candidates"])=={"UINT8x4_RGBA","UINT8x4_BGRA"}


def test_vertex_layout_exposes_deterministic_repack_offsets():
    r = build_vertex_layout(["200", "220", "130"])
    by = {x["property_id"]: x for x in r["attributes"]}
    assert by["200"]["offset"] == 0
    assert by["220"]["offset"] == 12
    assert by["130"]["offset"] == 24
    assert r["buffer_stride"] == 32


def test_vertex_abi_keeps_color_channel_order_ambiguous():
    from vertex_layout import property_abi
    abi = property_abi("460")
    assert abi["confidence"] == "ambiguous-channel-order"
    assert abi["channel_order_candidates"] == ["RGBA", "BGRA"]


def test_vertex_layout_exposes_explicit_abi_evidence_status():
    r = build_vertex_layout(["200", "310", "580", "460"])
    by = {x["property_id"]: x for x in r["attributes"]}
    assert by["200"]["abi_status"] == "inferred"
    assert by["310"]["abi_status"] == "proven"
    assert by["580"]["abi_status"] == "proven"
    assert by["460"]["abi_status"] == "ambiguous"
    assert "460" in r["evidence"]["ambiguous_properties"]


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
