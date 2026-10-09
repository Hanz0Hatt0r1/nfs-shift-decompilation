import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_topology_aliases.py"
EXPORTER = ROOT / "tools" / "ghidra" / "ShiftP13ASlot01TopologyAliasExporter.java"
PLAN = ROOT / "evidence" / "p1a_p13a_slot01_topology_alias_inventory_plan.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_slot01_topology", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**overrides):
    base = {
        "format": "SHIFT.GhidraP13ASlot01TopologyAliasCandidates/1",
        "program": "SHIFT.exe",
        "function_address": "0x00750000",
        "function_name": "FUN_00750000",
        "runtime_base_hint": True,
        "stride_hint": True,
        "exact_local_0x538_hint": False,
        "slot0_absolute_hint": False,
        "slot1_absolute_hint": False,
        "has_store": False,
        "has_load": True,
        "has_call": False,
        "has_indirect_call": False,
        "has_copy_like": False,
        "has_address_arithmetic": True,
        "events": [{
            "instruction_address": "0x00750010",
            "mnemonic": "LEA",
            "text": "LEA EAX,[ECX+EDX*4]",
            "runtime_base_scalar": False,
            "stride_scalar": False,
            "local_0x538_scalar": False,
            "slot0_0x938_scalar": False,
            "slot1_0x13b8_scalar": False,
            "pcode_ops": ["INT_ADD", "PTRADD"],
        }],
    }
    base.update(overrides)
    return base


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(rec) + "\n" for rec in records), encoding="utf-8")


def test_novel_candidate_prioritizes_nonliteral_topology_writer(tmp_path):
    module = load_module()
    src = tmp_path / "aliases.jsonl"
    novel = row(
        function_address="0x00758b50",
        function_name="FUN_00758b50",
        has_store=True,
        has_call=True,
    )
    already_bounded = row(
        function_address="0x00760000",
        function_name="FUN_00760000",
        exact_local_0x538_hint=True,
        has_store=True,
    )
    write_jsonl(src, [already_bounded, novel])

    payload = module.analyze(src)
    assert payload["counts"]["topology_functions"] == 2
    assert payload["counts"]["novel_nonliteral_0x538_candidates"] == 1
    candidate = payload["novel_candidates"][0]
    assert candidate["function_name"] == "FUN_00758b50"
    assert "store-like" in candidate["operation_classes"]
    assert candidate["selected_hdvehicle_root_proven"] is False
    assert candidate["target_range_write_proven"] is False
    assert payload["adjudication"]["p13a_slot0_complete"] is False
    assert payload["adjudication"]["p13a_slot1_complete"] is False
    assert payload["adjudication"]["external_provider_count"] == 7


def test_row_without_required_topology_is_rejected(tmp_path):
    module = load_module()
    src = tmp_path / "aliases.jsonl"
    write_jsonl(src, [row(stride_hint=False)])
    try:
        module.analyze(src)
    except ValueError as exc:
        assert "missing required +0x400/+0xa80 topology" in str(exc)
    else:
        raise AssertionError("row without required topology accepted")


def test_exporter_pins_topology_targets_and_candidate_operations():
    text = EXPORTER.read_text(encoding="utf-8")
    assert "RUNTIME_BASE = 0x400L" in text
    assert "STRIDE = 0xa80L" in text
    assert "LOCAL_FIELD = 0x538L" in text
    assert "SLOT0_ABSOLUTE = 0x938L" in text
    assert "SLOT1_ABSOLUTE = 0x13b8L" in text
    assert "scan.runtimeBaseHint && scan.strideHint" in text
    assert "PcodeOp.STORE" in text
    assert "PcodeOp.CALLIND" in text
    assert "PcodeOp.COPY" in text
    assert "PcodeOp.PTRADD" in text
    assert "functions.getFunctions(true)" in text


def test_plan_keeps_slot0_slot1_and_p13_fail_closed():
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1A.P13ASlot01TopologyAliasInventoryPlan/1"
    assert payload["search_shape"]["required_same_function_hints"] == [
        "+0x400 wheel-runtime base",
        "+0xa80 wheel stride",
    ]
    adj = payload["adjudication"]
    assert adj["exporter_ready"] is True
    assert adj["analyzer_ready"] is True
    assert adj["authoritative_machine_inventory_captured"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
