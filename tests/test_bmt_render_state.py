from resource_formats import (
    BMT_BLEND_FACTOR_NAMES,
    BMT_BLEND_OP_NAMES,
    BMT_ELEMENT_NAMES,
    BMT_TEST_FUNCTION_NAMES,
    _material_summary_from_tree,
)


def _field(name_id, name, value, attr_id=0):
    return {
        "name_id": name_id,
        "name": name,
        "attributes": [{
            "name_id": attr_id,
            "name": f"hash_{attr_id:08X}",
            "value": value,
        }],
        "children": [],
    }


def _tree():
    return {
        "name_id": 3596240483,
        "name": "material",
        "attributes": [
            {"value": "TEST"},
            {"value": r"render\shaders\body.fx"},
            {"value": "Default"},
            {"value": False},
            {"value": 1.0},
            {"value": 0.0},
            {"value": "EBFCT_ANTICLOCKWISE"},
        ],
        "children": [
            {
                "name_id": 3396092427,
                "name": "depthparams",
                "attributes": [],
                "children": [
                    _field(3875134881, "enabled", True, 101),
                    _field(2101237497, "writeenabled", False, 119),
                    _field(
                        367069359,
                        "function",
                        "ETF_LESS_THAN_OR_EQUAL",
                        102,
                    ),
                ],
            },
            {
                "name_id": 624549390,
                "name": "alphatestparams",
                "attributes": [],
                "children": [
                    _field(3875134881, "enabled", True, 101),
                    _field(
                        367069359,
                        "function",
                        "ETF_GREATER_THAN_OR_EQUAL",
                        102,
                    ),
                    _field(1773598955, "value", 64.0, 118),
                ],
            },
            {
                "name_id": 14911235,
                "name": "alphablendparams",
                "attributes": [],
                "children": [
                    _field(3875134881, "enabled", True, 101),
                    _field(
                        3982835436,
                        "sourceblend",
                        "EBF_SOURCE_ALPHA",
                        114178,
                    ),
                    _field(
                        3277320897,
                        "destblend",
                        "EBF_INV_SOURCE_ALPHA",
                        99298,
                    ),
                    _field(486381061, "blendop", "EBO_ADD", 97327),
                ],
            },
        ],
    }


def test_phase531_observed_bmt_ids_are_named():
    assert BMT_ELEMENT_NAMES[3396092427] == "depthparams"
    assert BMT_ELEMENT_NAMES[624549390] == "alphatestparams"
    assert BMT_ELEMENT_NAMES[14911235] == "alphablendparams"
    assert BMT_ELEMENT_NAMES[3875134881] == "enabled"
    assert BMT_ELEMENT_NAMES[2101237497] == "writeenabled"
    assert BMT_ELEMENT_NAMES[3982835436] == "sourceblend"
    assert BMT_ELEMENT_NAMES[3277320897] == "destblend"
    assert BMT_ELEMENT_NAMES[486381061] == "blendop"


def test_bmt_render_state_extracts_depth_alpha_test_and_blend():
    material = _material_summary_from_tree(_tree())
    state = material["render_state"]

    assert state["format"] == "SHIFT.BMTRenderState/1"

    depth = state["depth"]
    assert depth["enabled"] is True
    assert depth["write_enabled"] is False
    assert depth["function"]["raw"] == "ETF_LESS_THAN_OR_EQUAL"
    assert depth["function"]["engine_enum_index"] == 3

    alpha_test = state["alpha_test"]
    assert alpha_test["enabled"] is True
    assert alpha_test["function"]["engine_enum_index"] == 6
    assert alpha_test["value_raw"] == 64.0
    assert alpha_test["value_normalized"] == 64.0 / 255.0

    alpha_blend = state["alpha_blend"]
    assert alpha_blend["enabled"] is True
    assert alpha_blend["source_blend"]["engine_enum_index"] == 4
    assert alpha_blend["dest_blend"]["engine_enum_index"] == 5
    assert alpha_blend["blend_op"]["engine_enum_index"] == 0


def test_bmt_render_state_preserves_unknown_fields_without_inference():
    tree = _tree()
    tree["children"][0]["children"].append(
        _field(0x12345678, "hash_12345678", 0.125, 0x87654321)
    )
    state = _material_summary_from_tree(tree)["render_state"]["depth"]

    assert state["unmapped_fields"][0]["element_id"] == 0x12345678
    assert state["unmapped_fields"][0]["value"] == 0.125


def test_bmt_render_state_keeps_unknown_enum_explicit():
    tree = _tree()
    tree["children"][0]["children"][2]["attributes"][0]["value"] = "ETF_MAGIC"
    function = _material_summary_from_tree(tree)["render_state"]["depth"]["function"]

    assert function == {
        "raw": "ETF_MAGIC",
        "engine_enum_index": None,
        "status": "unknown",
    }


def test_retail_enum_tables_match_static_string_table_order():
    assert BMT_TEST_FUNCTION_NAMES == [
        "ETF_FAIL",
        "ETF_LESS_THAN",
        "ETF_EQUAL",
        "ETF_LESS_THAN_OR_EQUAL",
        "ETF_GREATER_THAN",
        "ETF_NOT_EQUAL",
        "ETF_GREATER_THAN_OR_EQUAL",
        "ETF_PASS",
    ]
    assert len(BMT_BLEND_FACTOR_NAMES) == 11
    assert BMT_BLEND_FACTOR_NAMES[4] == "EBF_SOURCE_ALPHA"
    assert BMT_BLEND_FACTOR_NAMES[5] == "EBF_INV_SOURCE_ALPHA"
    assert BMT_BLEND_OP_NAMES == [
        "EBO_ADD",
        "EBO_DEST_MINUS_SOURCE",
        "EBO_MIN",
        "EBO_MAX",
        "EBO_SOURCE_MINUS_DEST",
    ]



def test_bmt_render_state_preserves_only_unknown_nested_groups():
    tree = _tree()
    tree["children"].append({
        "name_id": 0xDEADBEEF,
        "name": "hash_DEADBEEF",
        "attributes": [],
        "children": [
            _field(0x11111111, "hash_11111111", True, 101),
        ],
    })
    tree["children"].append({
        "name_id": 648867590,
        "name": "shaderparam",
        "attributes": [{"name": "name", "value": "Diffuse"}],
        "children": [
            {
                "name_id": 1688245861,
                "name": "type",
                "attributes": [{"name": "t", "value": "TEXTURE"}],
                "children": [],
            },
        ],
    })

    state = _material_summary_from_tree(tree)["render_state"]

    assert len(state["unmapped_groups"]) == 1
    assert state["unmapped_groups"][0]["element_id"] == 0xDEADBEEF
