import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_outer_update_scheduling_gate.py"
    )
    spec = importlib.util.spec_from_file_location("outer_update_scheduling_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_text(gates=(r"'\0'", r"'\0'", r"'\x01'")):
    return f"""void __thiscall FUN_00713050(void *this,int *param_1)
{{
  FUN_00794a30((void *)(*piVar1 + 0x340),CONCAT44(2,1),0,0x20000000,0x3fa11111,{gates[0]});
  FUN_00794a30((void *)(*param_1 + 0x340),SUB84(dVar2,0),0,SUB84(dVar4,0),iVar6,{gates[1]});
  FUN_00794a30((void *)(*param_1 + 0x340),SUB84(dVar2,0),0,SUB84(dVar4,0),iVar6,{gates[2]});
}}
"""


def _edge(source, instruction, target, *, indirect=False):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": indirect,
    }


def _fixture(tmp_path, *, gates=(r"'\0'", r"'\0'", r"'\x01'")):
    module = _load_module()
    source = _source_text(gates)
    source_path = tmp_path / "SHIFT.exe.c"
    source_path.write_text(source, encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

    # Deliberately store the machine edges out of order. The report may expose
    # the finite machine candidate set in address order, but it must not pair
    # those addresses with source ordinals without an independent mapping.
    batch_edges = [
        _edge(module.UPSTREAM_BATCH, "0x007131b5", module.FIRST_CALLER),
        _edge(module.UPSTREAM_BATCH, "0x00713112", module.FIRST_CALLER),
        _edge(module.UPSTREAM_BATCH, "0x00713135", module.FIRST_CALLER),
    ]
    report = {
        "format": module.CALLSITE_FORMAT,
        "source": {"sha256": source_hash},
        "scope": {
            "source_snapshot_hash_verified": True,
            "ghidra_binary_identity_verified": True,
            "source_and_direct_callgraph_cross_checked": True,
            "rendered_frame_schedule_proven": False,
        },
        "outer_update": {
            "function": module.OUTER_UPDATE,
            "receiver_at_callsites": "DAT_00c13700",
        },
        "direct_callsites": [
            {
                "caller": module.FIRST_CALLER,
                "gate": [module.EXPECTED_PARAM5_GATE, "caller +0x234 == 0"],
                "outer_mode_argument": 0,
                "ghidra_call": _edge(
                    module.FIRST_CALLER,
                    "0x00794a6e",
                    module.OUTER_UPDATE,
                ),
            },
            {
                "caller": "0x0079b2d0",
                "gate": ["caller +0x34 != 0"],
                "ghidra_call": _edge(
                    "0x0079b2d0",
                    "0x0079b310",
                    module.OUTER_UPDATE,
                ),
            },
        ],
        "upstream_batch_path": {
            "function": module.UPSTREAM_BATCH,
            "first_caller_source_call_count": 3,
            "direct_calls_to_first_caller": batch_edges,
        },
        "upstream_owner_path": {
            "function": module.UPSTREAM_OWNER,
            "direct_call": _edge(
                module.UPSTREAM_OWNER,
                "0x00715434",
                module.UPSTREAM_BATCH,
            ),
        },
    }
    report_path = tmp_path / "outer_update_callsite_static.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return module, source_path, source_hash, report_path


def test_proves_one_source_call_can_pass_param5_gate_without_claiming_cadence(tmp_path):
    module, source, source_hash, contract = _fixture(tmp_path)
    report = module.build_outer_update_scheduling_gate(
        source,
        contract,
        expected_source_sha256=source_hash,
    )

    assert report["format"] == "SHIFT.OuterUpdateSchedulingGate/1"
    assert report["constant_param5_sequence"] == [0, 0, 1]
    assert report["nonzero_param5_source_ordinals"] == [2]
    assert report["nonconstant_param5_source_ordinals"] == []
    assert report["unique_nonzero_param5_source_call_proven"] is True
    assert report["unique_nonzero_param5_source_ordinal"] == 2
    assert report["source_calls_to_first_caller"][0]["param5_gate_state"] == "blocked-by-param5-zero"
    assert report["source_calls_to_first_caller"][2]["param5_gate_state"] == "param5-gate-eligible"
    assert report["source_calls_to_first_caller"][2]["remaining_runtime_gate"] == "caller +0x234 == 0"

    assert [row["instruction"] for row in report["machine_callsite_candidates"]] == [
        "0x00713112",
        "0x00713135",
        "0x007131b5",
    ]
    assert report["source_to_machine_callsite_mapping_state"] == "unknown"
    assert report["outer_update_dynamic_call_count_state"] == "unknown"
    assert report["cadence_owner_state"] == "unknown"
    assert report["next_instruction_targets"] == [module.UPSTREAM_BATCH]
    assert "source_call_to_machine_callsite_identity_not_proven" in report["blockers"]
    assert "unique_nonzero_FUN_00713050_param5_call_not_proven" not in report["blockers"]
    assert report["scope"]["unique_param5_gate_eligible_source_call_proven"] is True
    assert report["scope"]["source_order_equals_machine_instruction_order_assumed"] is False
    assert report["scope"]["source_to_machine_callsite_mapping_proven"] is False
    assert report["scope"]["dynamic_statement_execution_count_proven"] is False
    assert report["scope"]["fixed_step_cadence_owner_proven"] is False
    assert report["scope"]["rendered_frame_cadence_proven"] is False


def test_multiple_nonzero_gate_arguments_stay_ambiguous(tmp_path):
    module, source, source_hash, contract = _fixture(
        tmp_path,
        gates=(r"'\0'", r"'\x01'", r"'\x01'"),
    )
    report = module.build_outer_update_scheduling_gate(
        source,
        contract,
        expected_source_sha256=source_hash,
    )

    assert report["constant_param5_sequence"] == [0, 1, 1]
    assert report["nonzero_param5_source_ordinals"] == [1, 2]
    assert report["unique_nonzero_param5_source_call_proven"] is False
    assert report["unique_nonzero_param5_source_ordinal"] is None
    assert "unique_nonzero_FUN_00713050_param5_call_not_proven" in report["blockers"]
    assert report["scope"]["fixed_step_cadence_owner_proven"] is False


def test_nonconstant_gate_argument_is_reported_without_semantic_guess(tmp_path):
    module, source, source_hash, contract = _fixture(
        tmp_path,
        gates=(r"'\0'", r"'\0'", "param_6"),
    )
    report = module.build_outer_update_scheduling_gate(
        source,
        contract,
        expected_source_sha256=source_hash,
    )

    assert report["constant_param5_sequence"] == [0, 0, None]
    assert report["nonzero_param5_source_ordinals"] == []
    assert report["nonconstant_param5_source_ordinals"] == [2]
    assert report["source_calls_to_first_caller"][2]["param5_gate_state"] == "unknown"
    assert "one_or_more_FUN_00713050_param5_arguments_not_constant" in report["blockers"]
    assert "unique_nonzero_FUN_00713050_param5_call_not_proven" in report["blockers"]


def test_rejects_upstream_contract_that_preclaims_frame_cadence(tmp_path):
    module, source, source_hash, contract = _fixture(tmp_path)
    payload = json.loads(contract.read_text(encoding="utf-8"))
    payload["scope"]["rendered_frame_schedule_proven"] = True
    contract.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="preclaims frame cadence"):
        module.build_outer_update_scheduling_gate(
            source,
            contract,
            expected_source_sha256=source_hash,
        )


def test_rejects_machine_edge_target_drift(tmp_path):
    module, source, source_hash, contract = _fixture(tmp_path)
    payload = json.loads(contract.read_text(encoding="utf-8"))
    payload["upstream_batch_path"]["direct_calls_to_first_caller"][0]["to"] = "0x00794a40"
    contract.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="direct edge target drift"):
        module.build_outer_update_scheduling_gate(
            source,
            contract,
            expected_source_sha256=source_hash,
        )


def test_rejects_source_bytes_that_do_not_match_callsite_contract(tmp_path):
    module, source, source_hash, contract = _fixture(tmp_path)
    payload = json.loads(contract.read_text(encoding="utf-8"))
    payload["source"]["sha256"] = "0" * 64
    contract.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="source bytes do not match"):
        module.build_outer_update_scheduling_gate(
            source,
            contract,
            expected_source_sha256=source_hash,
        )


def test_rejects_missing_param5_gate_in_first_caller_contract(tmp_path):
    module, source, source_hash, contract = _fixture(tmp_path)
    payload = json.loads(contract.read_text(encoding="utf-8"))
    payload["direct_callsites"][0]["gate"] = ["caller +0x234 == 0"]
    contract.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="param_5 gate is not proven"):
        module.build_outer_update_scheduling_gate(
            source,
            contract,
            expected_source_sha256=source_hash,
        )
