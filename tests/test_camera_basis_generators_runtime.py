from camera_basis_generators_runtime import (
    basis_400,
    basis_500,
    describe_basis_generator,
)


def test_basis_400_has_exact_nine_assignments():
    result = basis_400(
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
    )
    assert len(result) == 9
    assert result[0] == 6.0 - (-5.0) * (-4.0) * (-6.0)
    assert result[1] == 10.0


def test_basis_500_matches_source_order():
    result = basis_500(
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
    )
    assert result == [
        6.0,
        4.0 * 5.0 * 3.0 - (-6.0) * 1.0,
        (-6.0) * (-4.0) + 1.0 * 5.0 * 3.0,
        (-6.0) * 2.0,
        3.0 * 1.0 + (-4.0) * (-5.0) * (-6.0),
        (-6.0) * 1.0 * (-5.0) - (-4.0) * 3.0,
        5.0,
        2.0 * (-4.0),
        2.0 * 1.0,
    ]


def test_basis_generator_keeps_helper_values_opaque():
    result = describe_basis_generator(
        variant="500",
        b10_values=[0.1, 0.2, 0.3],
        c40_values=[0.4, 0.5, 0.6],
    )
    assert result["evidence"]["function"] == "FUN_0081b500"
    assert result["limitations"][0].startswith("FUN_00900b10")
