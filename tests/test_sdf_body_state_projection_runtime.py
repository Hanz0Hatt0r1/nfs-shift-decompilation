import sdf_body_state_projection_runtime as runtime


def test_body_state_projection_contract_matches_retail_call_order():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["ready"] is True
    assert report["entry"] == "FUN_007bc680"
    assert [item["function"] for item in report["pre_coupling"]] == [
        "FUN_007aefb0",
        "FUN_007bac60",
        "FUN_007bae40",
        "FUN_007bb090",
    ]
    assert [item["function"] for item in report["coupling"]] == [
        "FUN_007bb250",
        "FUN_007bb6c0",
    ]
    assert report["coupling"][0]["scope"] == "HINGE-HINGE"
    assert report["coupling"][1]["scope"] == "BAR-BAR"


def test_body_state_projection_preserves_exact_residual_equations():
    report = runtime.describe_sdf_body_state_projection_contract()
    eq = report["state_transforms"]["residual_equations"]
    assert eq["x"] == "+0x48 - (+0x40*+0x20 - +0x38*+0x28)"
    assert eq["y"] == "+0x50 - (+0x30*+0x28 - +0x40*+0x18)"
    assert eq["z"] == "+0x58 - (+0x38*+0x18 - +0x30*+0x20)"
    assert report["storage"]["row_pointer_table"] == "+0x158"


def test_body_state_projection_keeps_side_flag_sign_rule():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["coupling"][0]["side_rule"] == (
        "equal sample-side flags add; differing flags subtract"
    )
    assert report["coupling"][1]["side_rule"] == (
        "equal sample-side flags add; differing flags subtract"
    )


def test_body_state_projection_records_source_equations_and_storage_targets():
    report = runtime.describe_sdf_body_state_projection_contract()
    equations = report["constraint_projection_equations"]

    joint = equations["JOINT"]
    assert joint["sample_stride"] == 0x40
    assert joint["scalar_base_field"] == "+0x30"
    assert joint["cross_product_terms"]["d2"] == (
        "sample[+0x28]*body[+0x20] - sample[+0x20]*body[+0x28]"
    )
    assert joint["cross_product_terms"]["d3"] == (
        "body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]"
    )
    assert joint["cross_product_terms"]["d5"] == (
        "sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]"
    )
    assert joint["sign_source"] == "sample +0x34: zero => add, nonzero => subtract"

    hinge = equations["HINGE"]
    assert hinge["sample_stride"] == 0xA0
    assert hinge["scalar_base_field"] == "+0x94"

    bar = equations["BAR"]
    assert bar["sample_stride"] == 0x60
    assert bar["scalar_base_field"] == "+0x30"
    assert bar["output_components"] == ["+0x150[index] += sign * d3"]
    assert bar["sign_source"] == (
        "sample +0x34: zero => add, nonzero => subtract with +0x48 correction term"
    )
