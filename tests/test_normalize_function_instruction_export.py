import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "normalize_function_instruction_export.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("normalize_function_instruction_export", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_normalizes_v2_to_v1_without_mutating_source(tmp_path):
    module = _load_module()
    source = tmp_path / "v2.jsonl"
    output = tmp_path / "compat.jsonl"
    row = {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "found": True,
        "function": {"address": "0x00886930", "name": "FUN_00886930"},
        "instructions": [
            {
                "address": "0x00886930",
                "bytes": "55",
                "mnemonic": "PUSH",
                "operands": ["EBP"],
                "pcode": [{"opcode": "COPY", "text": "unique:1 = COPY EBP"}],
            }
        ],
    }
    _write_jsonl(source, [row])

    report = module.normalize_export(source, output)

    original = json.loads(source.read_text(encoding="utf-8"))
    compat = json.loads(output.read_text(encoding="utf-8"))
    assert original["format"] == "SHIFT.GhidraFunctionInstructions/2"
    assert "pcode" in original["instructions"][0]
    assert compat["format"] == "SHIFT.GhidraFunctionInstructions/1"
    assert "pcode" not in compat["instructions"][0]
    assert compat["instructions"][0]["mnemonic"] == "PUSH"
    assert report["input_formats"] == ["SHIFT.GhidraFunctionInstructions/2"]
    assert report["output_format"] == "SHIFT.GhidraFunctionInstructions/1"
    assert report["row_count"] == 1


def test_v1_round_trip_preserves_machine_instruction_fields(tmp_path):
    module = _load_module()
    source = tmp_path / "v1.jsonl"
    output = tmp_path / "compat.jsonl"
    _write_jsonl(
        source,
        [
            {
                "format": "SHIFT.GhidraFunctionInstructions/1",
                "found": True,
                "instructions": [
                    {
                        "address": "0x00886930",
                        "bytes": "55",
                        "mnemonic": "PUSH",
                        "operands": ["EBP"],
                    }
                ],
            }
        ],
    )

    module.normalize_export(source, output)
    compat = json.loads(output.read_text(encoding="utf-8"))
    assert compat["format"] == "SHIFT.GhidraFunctionInstructions/1"
    assert compat["instructions"][0]["bytes"] == "55"
    assert compat["instructions"][0]["operands"] == ["EBP"]


def test_rejects_unknown_instruction_export_format(tmp_path):
    module = _load_module()
    source = tmp_path / "bad.jsonl"
    output = tmp_path / "compat.jsonl"
    _write_jsonl(source, [{"format": "SHIFT.GhidraFunctionInstructions/99"}])

    try:
        module.normalize_export(source, output)
    except ValueError as exc:
        assert "unsupported instruction export format" in str(exc)
    else:
        raise AssertionError("unknown format must be rejected")
