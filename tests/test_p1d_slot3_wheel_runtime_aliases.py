import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_wheel_runtime_aliases.py"
EXPORTER = ROOT / "tools" / "ghidra" / "ShiftWheelRuntimeAliasExporter.java"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_alias", ANALYZER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path) -> None:
    rows = [
        {
            "format": "SHIFT.GhidraWheelRuntimeAliasUses/1",
            "program": "SHIFT.exe",
            "function_address": "0x00758b50",
            "function_name": "FUN_00758b50",
            "field_offset": "0x538",
            "runtime_base_hint": True,
            "stride_hint": True,
            "slot3_absolute_hint": False,
            "field_use_count": 1,
            "has_store": False,
            "has_load": True,
            "has_call": True,
            "has_indirect_call": False,
            "has_copy_like": True,
            "has_address_arithmetic": True,
            "uses": [{
                "instruction_address": "0x00758d60",
                "mnemonic": "LEA",
                "text": "LEA ECX,[ESI + 0x538]",
                "instruction_scalar_match": True,
                "pcode_constant_match": True,
                "pcode_ops": ["INT_ADD", "COPY"],
            }],
        },
        {
            "format": "SHIFT.GhidraWheelRuntimeAliasUses/1",
            "program": "SHIFT.exe",
            "function_address": "0x00600000",
            "function_name": "FUN_00600000",
            "field_offset": "0x538",
            "runtime_base_hint": False,
            "stride_hint": False,
            "slot3_absolute_hint": False,
            "field_use_count": 1,
            "has_store": True,
            "has_load": False,
            "has_call": False,
            "has_indirect_call": False,
            "has_copy_like": False,
            "has_address_arithmetic": False,
            "uses": [{
                "instruction_address": "0x00600010",
                "mnemonic": "FSTP",
                "text": "FSTP qword ptr [EAX + 0x538]",
                "instruction_scalar_match": True,
                "pcode_constant_match": True,
                "pcode_ops": ["STORE"],
            }],
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_exporter_is_candidate_only_and_pins_topology_constants():
    text = EXPORTER.read_text(encoding="utf-8")
    assert 'FIELD = 0x538L' in text
    assert 'FIELD = 0x138L' not in text
    assert 'RUNTIME_BASE = 0x400L' in text
    assert 'STRIDE = 0xa80L' in text
    assert 'SLOT3_ABSOLUTE = 0x28b8L' in text
    assert "numeric constant equality is never semantic object identity" in text


def test_analyzer_ranks_topology_context_but_stays_fail_closed(tmp_path):
    module = load_module()
    input_path = tmp_path / "aliases.jsonl"
    write_rows(input_path)
    payload = module.analyze(input_path)

    assert payload["format"] == "SHIFT.P1D.Slot3WheelRuntimeAliasInventory/1"
    assert payload["counts"]["functions_with_exact_0x538_use"] == 2
    assert payload["counts"]["known_caller_rows"] == 1
    assert payload["ranked_candidates"][0]["function_name"] == "FUN_00758b50"
    assert payload["ranked_candidates"][0]["selected_hdvehicle_root_proven"] is False
    assert payload["ranked_candidates"][0]["f64_qword_write_proven"] is False

    adj = payload["adjudication"]
    assert adj["inventory_complete_for_exported_exact_0x538_uses"] is True
    assert adj["scalar_or_topology_hints_prove_object_identity"] is False
    assert adj["selected_hdvehicle_slot3_writer_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_analyzer_rejects_field_drift_and_old_contract_offset(tmp_path):
    module = load_module()
    for bad_offset in ("0x539", "0x138"):
        path = tmp_path / f"bad-{bad_offset}.jsonl"
        path.write_text(json.dumps({
            "format": "SHIFT.GhidraWheelRuntimeAliasUses/1",
            "field_offset": bad_offset,
        }) + "\n", encoding="utf-8")
        try:
            module.analyze(path)
        except ValueError as exc:
            assert "unexpected field offset" in str(exc)
        else:
            raise AssertionError(f"expected field drift rejection for {bad_offset}")
