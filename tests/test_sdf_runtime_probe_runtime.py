import pytest

import sdf_runtime_probe_runtime as runtime


def test_probe_function_addresses_and_image_base_are_source_backed():
    assert runtime.IMAGE_BASE == 0x00400000
    assert runtime.FUNCTIONS == {
        "frame_entry": 0x007B3F40,
        "builtin_solver": 0x007B0F20,
        "post_solve": 0x007B4110,
    }


def test_solver_call_stack_layout_matches_thiscall_arguments():
    result = runtime.solver_call_stack_layout(0x1000)
    assert result == {
        "return_address": 0x1000,
        "solver_state": 0x1004,
        "row_pointer_table": 0x1008,
        "rhs": 0x100C,
        "scalar_count": 0x1010,
    }


def test_solver_state_derives_physics_system_from_0x4c():
    assert runtime.derive_physics_system_from_solver_state(0x2000) == 0x1FB4


def test_capture_geometry_reports_exact_retail_sizes():
    result = runtime.capture_geometry(
        physics_system=0x10000000,
        solver_state=0x0FFFFFFC,
        scalar_count=40,
        row_pointer_table=0x10001000,
        rhs_pointer=0x10002000,
        solver_state=0x1000004C,
    )
    assert result["ready"] is True
    assert result["sizes"] == {
        "rhs_bytes": 320,
        "matrix_bytes": 12800,
        "row_pointer_bytes": 160,
    }
    assert result["physics_offsets"]["solver_scalar_count"] == 0x34


def test_validate_probe_dump_shape_accepts_40_scalar_frame():
    result = runtime.validate_dump_shape(
        scalar_count=40,
        rhs=[0.0] * 40,
        matrix=[[0.0] * 40 for _ in range(40)],
    )
    assert result["ready"] is True
    assert result["matrix_cells"] == 1600


def test_validate_probe_dump_shape_reports_bad_matrix_shape():
    result = runtime.validate_dump_shape(
        scalar_count=2,
        rhs=[0.0, 0.0],
        matrix=[[0.0, 0.0]],
    )
    assert result["ready"] is False
    assert "matrix-row-count" in result["errors"]


def test_u32_from_bytes_uses_little_endian():
    assert runtime.u32_from_bytes(b"xV4") == 0x12345678


def test_probe_contract_declares_builtin_thiscall_stack_and_post_solve_fastcall():
    report = runtime.describe_sdf_runtime_probe_contract()
    assert report["breakpoints"]["builtin_solver"]["abi"] == "__thiscall"
    assert report["breakpoints"]["builtin_solver"]["stack_arguments"]["scalar_count"] == "[ESP+0x10]"
    assert report["breakpoints"]["post_solve"]["abi"] == "__fastcall"
    assert report["output"]["number_format"] == "little-endian IEEE-754 binary64"
    assert "A running retail target and debugger attachment are required." in report["limitations"]
