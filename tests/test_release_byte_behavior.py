import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_release_byte_behavior.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_release_byte_behavior", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, target=None, ref_type="UNCONDITIONAL_CALL"):
    refs = [] if target is None else [{"to": target, "type": ref_type}]
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": " ".join([mnemonic] + list(operands or [])),
        "operands": list(operands or []),
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": list(flows or ([] if target is None else [target])),
        "references": refs,
    }


def _row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": len(instructions),
            "calling_convention": "__fastcall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write(path: Path, backend):
    thunk = [
        _ins(
            "0x0064f4c0",
            "JMP",
            ["0x0064f3a0"],
            flows=["0x0064f3a0"],
            target="0x0064f3a0",
            ref_type="UNCONDITIONAL_JUMP",
        )
    ]
    rows = [
        _row("0x0064f4c0", "thunk_FUN_0064f3a0", thunk),
        _row("0x0064f3a0", "FUN_0064f3a0", backend),
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_entry_dl_forwarding_and_branch_influence_are_observed(tmp_path):
    module = _load_module()
    source = tmp_path / "backend.jsonl"
    backend = [
        _ins("0x0064f3a0", "TEST", ["DL", "DL"], fallthrough="0x0064f3a2"),
        _ins(
            "0x0064f3a2",
            "JZ",
            ["0x0064f3a8"],
            fallthrough="0x0064f3a4",
            flows=["0x0064f3a8"],
        ),
        _ins("0x0064f3a4", "RET"),
        _ins("0x0064f3a8", "RET"),
    ]
    _write(source, backend)

    report = module.analyze_release_byte_behavior(source)

    assert report["analysis_complete"] is True
    assert report["thunk_entry_dl_forwarded_to_release_backend"] is True
    assert report["release_backend_entry_dl_observed"] is True
    assert report["release_backend_entry_dl_controls_conditional_branch"] is True
    backend_row = next(row for row in report["functions"] if row["address"] == "0x0064f3a0")
    assert backend_row["condition_observations"][0]["mnemonic"] == "TEST"
    assert backend_row["branch_observations"][0]["mnemonic"] == "JZ"
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["delete_kind_role_proven"] is False


def test_bitwise_transform_of_entry_dl_is_recorded_without_semantic_promotion(tmp_path):
    module = _load_module()
    source = tmp_path / "backend.jsonl"
    backend = [
        _ins("0x0064f3a0", "AND", ["DL", "0x1"], fallthrough="0x0064f3a3"),
        _ins("0x0064f3a3", "TEST", ["DL", "DL"], fallthrough="0x0064f3a5"),
        _ins(
            "0x0064f3a5",
            "JNZ",
            ["0x0064f3aa"],
            fallthrough="0x0064f3a7",
            flows=["0x0064f3aa"],
        ),
        _ins("0x0064f3a7", "RET"),
        _ins("0x0064f3aa", "RET"),
    ]
    _write(source, backend)

    report = module.analyze_release_byte_behavior(source)

    assert report["release_backend_entry_dl_bitwise_transformed"] is True
    assert report["release_backend_entry_dl_controls_conditional_branch"] is True
    backend_row = next(row for row in report["functions"] if row["address"] == "0x0064f3a0")
    assert backend_row["bitwise_observations"][0]["mnemonic"] == "AND"
    assert report["scope"]["release_flag_role_proven"] is False


def test_overwriting_edx_removes_entry_dl_influence(tmp_path):
    module = _load_module()
    source = tmp_path / "backend.jsonl"
    backend = [
        _ins("0x0064f3a0", "XOR", ["EDX", "EDX"], fallthrough="0x0064f3a2"),
        _ins("0x0064f3a2", "TEST", ["DL", "DL"], fallthrough="0x0064f3a4"),
        _ins(
            "0x0064f3a4",
            "JNZ",
            ["0x0064f3a8"],
            fallthrough="0x0064f3a6",
            flows=["0x0064f3a8"],
        ),
        _ins("0x0064f3a6", "RET"),
        _ins("0x0064f3a8", "RET"),
    ]
    _write(source, backend)

    report = module.analyze_release_byte_behavior(source)

    assert report["release_backend_entry_dl_observed"] is True
    assert report["release_backend_entry_dl_controls_conditional_branch"] is False
    backend_row = next(row for row in report["functions"] if row["address"] == "0x0064f3a0")
    assert backend_row["branch_observations"] == []


def test_unsupported_tainted_register_write_marks_analysis_incomplete(tmp_path):
    module = _load_module()
    source = tmp_path / "backend.jsonl"
    backend = [
        _ins("0x0064f3a0", "IMUL", ["EDX", "EAX"], fallthrough="0x0064f3a3"),
        _ins("0x0064f3a3", "TEST", ["DL", "DL"], fallthrough="0x0064f3a5"),
        _ins("0x0064f3a5", "RET"),
    ]
    _write(source, backend)

    report = module.analyze_release_byte_behavior(source)

    assert report["analysis_complete"] is False
    backend_row = next(row for row in report["functions"] if row["address"] == "0x0064f3a0")
    assert any("outside modeled DL-taint subset" in reason for reason in backend_row["uncertainty_reasons"])
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False
