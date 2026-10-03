import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_body_writer_bridge_candidates.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_body_writer_bridge_candidates", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _access(function, register, displacement, access, instruction, *, name=None):
    return {
        "function": function,
        "function_name": name or f"FUN_{function[2:]}",
        "instruction": instruction,
        "instruction_text": f"synthetic {access} [{register}+0x{displacement:x}]",
        "operand_index": 0,
        "operand": f"dword ptr [{register} + 0x{displacement:x}]",
        "base_register": register,
        "displacement": displacement,
        "displacement_hex": f"0x{displacement:x}",
        "pcode_memory_ops": ["LOAD"] if access == "read" else ["STORE"],
        "access": access,
        "status": "syntactic-register-relative-memory-access",
        "promoted": False,
    }


def _report(accesses):
    return {
        "format": "SHIFT.GhidraRegisterRelativeAccesses/1",
        "accesses": accesses,
    }


def test_detects_accumulator_to_motion_on_same_function_and_register():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "ECX", 0x48, "read", "0x00700010"),
                _access("0x00700000", "ECX", 0x78, "write", "0x00700020"),
            ]
        )
    )

    assert report["candidate_count"] == 1
    candidate = report["candidates"][0]
    assert candidate["kind"] == "accumulator-to-motion"
    assert candidate["base_register"] == "ECX"
    assert candidate["read_offsets"] == [0x48]
    assert candidate["write_offsets"] == [0x78]
    assert candidate["body_pointer_proven"] is False
    assert candidate["persistent_writer_proven"] is False


def test_detects_motion_to_pose_and_combined_bridge_on_same_register():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "ESI", 0x60, "read", "0x00700010"),
                _access("0x00700000", "ESI", 0x18, "read-write", "0x00700020"),
                _access("0x00700000", "ESI", 0xD4, "write", "0x00700030"),
            ]
        )
    )

    assert report["accumulator_to_motion_candidate_count"] == 1
    assert report["motion_to_pose_candidate_count"] == 1
    assert report["combined_bridge_function_count"] == 1
    assert report["combined_bridge_functions"] == ["0x00700000"]
    assert report["combined_bridge_groups"] == [
        {"function": "0x00700000", "base_register": "ESI"}
    ]


def test_does_not_join_offsets_across_different_base_registers():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "ECX", 0x48, "read", "0x00700010"),
                _access("0x00700000", "ESI", 0x78, "write", "0x00700020"),
                _access("0x00700000", "ECX", 0x78, "read", "0x00700030"),
                _access("0x00700000", "ESI", 0x00, "write", "0x00700040"),
            ]
        )
    )

    assert report["candidate_count"] == 0
    assert report["combined_bridge_function_count"] == 0
    assert report["combined_bridge_groups"] == []


def test_same_function_different_register_stages_are_not_combined():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "ECX", 0x48, "read", "0x00700010"),
                _access("0x00700000", "ECX", 0x78, "write", "0x00700020"),
                _access("0x00700000", "ESI", 0x78, "read", "0x00700030"),
                _access("0x00700000", "ESI", 0x00, "write", "0x00700040"),
            ]
        )
    )

    assert report["candidate_count"] == 2
    assert report["combined_bridge_function_count"] == 0
    assert report["combined_bridge_groups"] == []


def test_read_write_access_counts_for_both_sides():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "EDI", 0x50, "read-write", "0x00700010"),
                _access("0x00700000", "EDI", 0x80, "read-write", "0x00700020"),
                _access("0x00700000", "EDI", 0x08, "read-write", "0x00700030"),
            ]
        )
    )

    assert {row["kind"] for row in report["candidates"]} == {
        "accumulator-to-motion",
        "motion-to-pose",
    }
    assert report["combined_bridge_group_count"] == 1


def test_unrelated_or_one_sided_accesses_are_not_candidates():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                _access("0x00700000", "ECX", 0x48, "write", "0x00700010"),
                _access("0x00700000", "ECX", 0x78, "read", "0x00700020"),
                _access("0x00700000", "ECX", 0x128, "write", "0x00700030"),
            ]
        )
    )
    assert report["candidate_count"] == 0


def test_malformed_rows_are_preserved_as_blockers():
    module = _load_module()
    report = module.build_body_writer_bridge_candidates(
        _report(
            [
                {"function": "0x00700000", "base_register": "ECX", "access": "read"},
                _access("0x00700000", "ECX", 0x48, "read", "0x00700010"),
            ]
        )
    )
    assert report["malformed_access_count"] == 1
    assert report["malformed_accesses"][0]["reason"].startswith("missing function")


def test_rejects_wrong_input_format(tmp_path):
    module = _load_module()
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"format": "WRONG", "accesses": []}), encoding="utf-8")
    try:
        module._load(path)
    except ValueError as exc:
        assert "SHIFT.GhidraRegisterRelativeAccesses/1" in str(exc)
    else:
        raise AssertionError("wrong input format must fail closed")
