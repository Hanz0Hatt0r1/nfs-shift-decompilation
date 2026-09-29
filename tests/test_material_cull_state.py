from material_cull_state import translate_bmt_cull


def test_retail_bmt_cull_mapping_matches_d3d9_lookup():
    none = translate_bmt_cull("EBFCT_NONE")
    cw = translate_bmt_cull("EBFCT_CLOCKWISE")
    ccw = translate_bmt_cull("EBFCT_ANTICLOCKWISE")

    assert (none["engine_enum_index"], none["d3d9_value"]) == (0, 1)
    assert none["d3d9_name"] == "D3DCULL_NONE"
    assert none["vulkan_cull_mode"] == "VK_CULL_MODE_NONE"

    assert (cw["engine_enum_index"], cw["d3d9_value"]) == (1, 2)
    assert cw["d3d9_name"] == "D3DCULL_CW"
    assert cw["vulkan_cull_mode"] == "VK_CULL_MODE_BACK_BIT"

    assert (ccw["engine_enum_index"], ccw["d3d9_value"]) == (2, 3)
    assert ccw["d3d9_name"] == "D3DCULL_CCW"
    assert ccw["vulkan_cull_mode"] == "VK_CULL_MODE_FRONT_BIT"


def test_retail_bmt_cull_accepts_enum_indices():
    assert translate_bmt_cull(0)["engine_name"] == "EBFCT_NONE"
    assert translate_bmt_cull(1)["engine_name"] == "EBFCT_CLOCKWISE"
    assert translate_bmt_cull(2)["engine_name"] == "EBFCT_ANTICLOCKWISE"


def test_unknown_bmt_cull_fails_closed():
    result = translate_bmt_cull("EBFCT_MAGIC")
    assert result["ready"] is False
    assert result["blocking_reasons"] == [
        "material-cull:unsupported:EBFCT_MAGIC"
    ]


def test_missing_bmt_cull_is_explicitly_not_supplied():
    result = translate_bmt_cull(None)
    assert result["ready"] is True
    assert result["status"] == "not-supplied"
    assert result["evidence_status"] == "not-supplied"
