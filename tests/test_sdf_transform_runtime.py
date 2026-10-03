import math

import sdf_transform_runtime as runtime


def test_matrix_block_offsets():
    c = runtime.build_matrix_block_contract()
    assert c["base_offset"] == 0xD4
    assert c["float_offsets"] == [hex(v) for v in (0xD4,0xD8,0xDC,0xE0,0xE4,0xE8,0xEC,0xF0,0xF4)]
    assert c["layout"]["m00"] == "0xd4"
    assert c["layout"]["m22"] == "0xf4"


def test_forward_transform_matches_row_major_formula():
    matrix = (
        0.0, -1.0, 0.0,
        1.0,  0.0, 0.0,
        0.0,  0.0, 1.0,
    )
    assert runtime.transform_forward(matrix, (2.0, 3.0, 4.0)) == (-3.0, 2.0, 4.0)


def test_transposed_transform_matches_fun_007af0a0_order():
    matrix = (
        0.0, -1.0, 0.0,
        1.0,  0.0, 0.0,
        0.0,  0.0, 1.0,
    )
    assert runtime.transform_transposed(matrix, (-3.0, 2.0, 4.0)) == (2.0, 3.0, 4.0)


def test_helpers_reject_wrong_component_counts():
    try:
        runtime.transform_forward((1.0,) * 9, (1.0, 2.0))
    except ValueError:
        pass
    else:
        raise AssertionError("expected vector arity failure")
    try:
        runtime.transform_forward((1.0,) * 8, (1.0, 2.0, 3.0))
    except ValueError:
        pass
    else:
        raise AssertionError("expected matrix arity failure")


def test_numeric_boundary_is_machine_backed():
    c = runtime.build_transform_helper_contract()
    assert c["format"] == "SHIFT.SDFTransformRuntime/3"
    assert c["version"] == 3
    assert c["canonical_transform_format"] == "SHIFT.MatrixVectorTransformRuntime/3"
    boundary = c["numeric_boundary"]
    assert boundary["input_components_are_cast_to_float"] is False
    assert boundary["machine_vector_operand_width_bits"] == 64
    assert boundary["matrix_component_width_bits"] == 32
    assert boundary["output_component_width_bits"] == 64
    assert boundary["x87_extended_intermediates"] is True


def test_sdf_adapter_preserves_binary64_input_perturbation():
    identity = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )
    perturbation = 1.0 + 2.0 ** -30
    assert runtime.transform_forward(identity, (perturbation, 0.0, 0.0))[0] == perturbation
    assert runtime.transform_transposed(identity, (perturbation, 0.0, 0.0))[0] == perturbation
