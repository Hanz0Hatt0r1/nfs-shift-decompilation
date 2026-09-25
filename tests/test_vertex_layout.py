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
    assert abi["confidence"] == "ambiguous-declaration-and-channel-order"
    assert abi["channel_order_candidates"] == ["RGBA", "BGRA"]
    assert abi["source_evidence"]["function"] == "FUN_008310c0"
    assert abi["source_evidence"]["little_endian_memory_order"] == "BGRA"


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


def test_verified_color_bridge_resolves_color_layout_without_changing_default():
    import vertex_layout
    from pathlib import Path
    assert Path(vertex_layout.__file__).resolve() == (Path(__file__).resolve().parents[1] / "vertex_layout.py")
    assert vertex_layout.D3DDECLTYPES["460"]["confidence"] == "ambiguous-declaration-and-channel-order"
    assert vertex_layout.D3DDECLTYPES["461"]["confidence"] == "ambiguous-channel-order"
    bridge = {
        "format": "SHIFT.MEBD3D9ColorBridgeEvidence/1",
        "verified_abi": True,
        "properties": {
            "460": {
                "property_to_type": {
                    "status": "observed",
                    "selected": {
                        "code": 4,
                        "name": "D3DCOLOR",
                        "memory_order": "BGRA",
                        "shader_order": "RGBA",
                    },
                },
            },
            "461": {
                "property_to_type": {
                    "status": "observed",
                    "selected": {
                        "code": 4,
                        "name": "D3DCOLOR",
                        "memory_order": "BGRA",
                        "shader_order": "RGBA",
                    },
                },
            },
        },
    }

    default = build_vertex_layout(["460", "461"])
    resolved = build_vertex_layout(
        ["460", "461"],
        color_abi_evidence=bridge,
    )

    default_rows = {row["property_id"]: row for row in default["attributes"]}
    resolved_rows = {row["property_id"]: row for row in resolved["attributes"]}

    assert default_rows["460"]["abi_status"] == "ambiguous"
    assert default_rows["461"]["abi_status"] == "ambiguous"
    assert resolved_rows["460"]["abi_status"] == "proven"
    assert resolved_rows["461"]["abi_status"] == "proven"
    assert resolved_rows["460"]["d3d9"] == "D3DCOLOR"
    assert resolved_rows["460"]["channel_order_candidates"] == ["BGRA"]
    assert resolved_rows["460"]["android_candidates"] == ["UINT8x4_BGRA"]
    assert resolved_rows["461"]["d3d9"] == "D3DCOLOR"


def test_vertex_layout_module_signature_is_valid():
    import vertex_layout
    assert callable(vertex_layout.build_vertex_layout)


def test_vertex_abi_status_table_is_immutable():
    import vertex_layout
    assert vertex_layout.ABI_STATUS["ambiguous-declaration-and-channel-order"] == "ambiguous"
    try:
        vertex_layout.ABI_STATUS["ambiguous-declaration-and-channel-order"] = "unknown"
    except TypeError:
        pass
    else:
        raise AssertionError("ABI_STATUS must be immutable")


def test_color1_channel_order_status_is_ambiguous():
    r = build_vertex_layout(["461"])
    assert r["attributes"][0]["abi_status"] == "ambiguous"
