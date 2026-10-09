import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_wheel_runtime_aliases.py"
EXPORTER = ROOT / "tools" / "ghidra" / "ShiftWheelRuntimeAliasExporter.java"
PLAN = ROOT / "evidence" / "p1d_slot3_wheel_runtime_alias_inventory_plan.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_aliases", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**overrides):
    base = {
        "format": "SHIFT.GhidraWheelRuntimeAliasUses/1",
        "program": "SHIFT.exe",
        "function_address": "0x00750000",
        "function_name": "FUN_00750000",
        "field_offset": "0x138",
        "runtime_base_hint": False,
        "stride_hint": False,
        "slot3_absolute_hint": False,
        "field_use_count": 1,
        "has_store": False,
        "has_load": True,
        "has_call": False,
        "has_indirect_call": False,
        "has_copy_like": False,
        "has_address_arithmetic": False,
        "uses": [{
            "instruction_address": "0x00750010",
            "mnemonic": "MOV",
            "text": "MOV EAX,dword ptr [ECX + 0x138]",
            "instruction_scalar_match": True,
            "pcode_constant_match": True,
            "pcode_ops": ["INT_ADD", "LOAD", "COPY"],
        }],
    }
    base.update(overrides)
    return base


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(rec) + "\n" for rec in records), encoding="utf-8")


def test_strong_candidate_requires_topology_plus_writer_or_forwarding_class(tmp_path):
    module = load_module()
    src = tmp_path / "aliases.jsonl"
    strong = row(
        function_address="0x00758b50",
        function_name="FUN_00758b50",
        runtime_base_hint=True,
        stride_hint=True,
        has_store=True,
        has_call=True,
        uses=[{
            "instruction_address": "0x00758c00",
            "mnemonic": "FSTP",
            "text": "FSTP qword ptr [EDI + 0x138]",
            "instruction_scalar_match": True,
            "pcode_constant_match": True,
            "pcode_ops": ["INT_ADD", "STORE"],
        }],
    )
    collision = row(
        function_address="0x00800000",
        function_name="FUN_00800000",
        slot3_absolute_hint=True,
    )
    write_jsonl(src, [collision, strong])

    payload = module.analyze(src)
    assert payload["counts"]["functions_with_exact_0x138_use"] == 2
    assert payload["counts"]["strong_topology_candidates"] == 1
    candidate = payload["strong_topology_candidates"][0]
    assert candidate["function_name"] == "FUN_00758b50"
    assert "store-like" in candidate["usage_classes"]
    assert candidate["selected_hdvehicle_root_proven"] is False
    assert candidate["f64_qword_write_proven"] is False
    assert payload["adjudication"]["selected_hdvehicle_slot3_writer_proven"] is False
    assert payload["adjudication"]["external_provider_count"] == 7


def test_wrong_field_format_is_rejected(tmp_path):
    module = load_module()
    src = tmp_path / "aliases.jsonl"
    bad = row(field_offset="0x28b8")
    write_jsonl(src, [bad])
    try:
        module.analyze(src)
    except ValueError as exc:
        assert "unexpected field offset" in str(exc)
    else:
        raise AssertionError("wrong field offset accepted")


def test_exporter_pins_exact_wheel_topology_constants_and_pcode_classes():
    text = EXPORTER.read_text(encoding="utf-8")
    assert "FIELD = 0x138L" in text
    assert "RUNTIME_BASE = 0x400L" in text
    assert "STRIDE = 0xa80L" in text
    assert "SLOT3_ABSOLUTE = 0x28b8L" in text
    assert "PcodeOp.STORE" in text
    assert "PcodeOp.LOAD" in text
    assert "PcodeOp.CALLIND" in text
    assert "PcodeOp.PTRADD" in text
    assert "PcodeOp.PTRSUB" in text
    assert "functions.getFunctions(true)" in text


def test_plan_keeps_slot3_fail_closed():
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3WheelRuntimeAliasInventoryPlan/1"
    assert payload["target"]["slot3_absolute"] == "HDVehicle+0x28b8"
    assert payload["target"]["per_wheel_field"] == "+0x138"
    adj = payload["adjudication"]
    assert adj["exporter_ready"] is True
    assert adj["machine_inventory_executed"] is False
    assert adj["selected_hdvehicle_slot3_writer_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
