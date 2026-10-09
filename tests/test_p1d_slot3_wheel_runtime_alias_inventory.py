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
        "field_offset": "0x538",
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
            "text": "MOV EAX,dword ptr [ECX + 0x538]",
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
            "text": "FSTP qword ptr [EDI + 0x538]",
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
    assert payload["counts"]["functions_with_exact_0x538_use"] == 2
    assert payload["counts"]["strong_topology_candidates"] == 1
    candidate = payload["strong_topology_candidates"][0]
    assert candidate["function_name"] == "FUN_00758b50"
    assert "store-like" in candidate["usage_classes"]
    assert candidate["selected_hdvehicle_root_proven"] is False
    assert candidate["f64_qword_write_proven"] is False
    assert payload["target"]["normalization"] == "0x400 + 3*0xa80 + 0x538 = 0x28b8"
    assert payload["adjudication"]["selected_hdvehicle_slot3_writer_proven"] is False
    assert payload["adjudication"]["external_provider_count"] == 7


def test_old_contract_local_0x138_is_rejected(tmp_path):
    module = load_module()
    src = tmp_path / "aliases.jsonl"
    bad = row(field_offset="0x138")
    write_jsonl(src, [bad])
    try:
        module.analyze(src)
    except ValueError as exc:
        assert "unexpected field offset" in str(exc)
    else:
        raise AssertionError("contract-local 0x138 accepted as machine displacement")


def test_exporter_pins_exact_machine_displacement_and_wheel_topology():
    text = EXPORTER.read_text(encoding="utf-8")
    assert "FIELD = 0x538L" in text
    assert "FIELD = 0x138L" not in text
    assert "RUNTIME_BASE = 0x400L" in text
    assert "STRIDE = 0xa80L" in text
    assert "SLOT3_ABSOLUTE = 0x28b8L" in text
    assert "PcodeOp.STORE" in text
    assert "PcodeOp.LOAD" in text
    assert "PcodeOp.CALLIND" in text
    assert "PcodeOp.PTRADD" in text
    assert "PcodeOp.PTRSUB" in text
    assert "functions.getFunctions(true)" in text


def test_plan_keeps_slot3_fail_closed_and_records_correction():
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3WheelRuntimeAliasInventoryPlan/1"
    target = payload["target"]
    assert target["slot3_absolute"] == "HDVehicle+0x28b8"
    assert target["machine_receiver_field"] == "+0x538"
    assert target["normalization"] == "0x400 + 3*0xa80 + 0x538 = 0x28b8"
    assert payload["correction"]["superseded_scan_displacement"] == "+0x138"
    assert payload["correction"]["correct_machine_displacement"] == "+0x538"
    adj = payload["adjudication"]
    assert adj["exporter_ready"] is True
    assert adj["machine_inventory_executed"] is False
    assert adj["selected_hdvehicle_slot3_writer_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
