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
        / "analyze_vehicle_create_backend_return_frontier.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_create_backend_return_frontier", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")
    return path


def _p(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, pcode=None):
    operands = operands or []
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + ((" " + ",".join(operands)) if operands else ""),
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _row(module, address, name, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": len(instructions) * 4,
            "calling_convention": "__fastcall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _default_backend_a(module):
    return [
        _ins(
            module.ALLOCATION_BACKEND,
            "CALL",
            ["0x00639000"],
            fallthrough="0x00638025",
            flows=["0x00639000"],
            pcode=[_p("CALL")],
        ),
        _ins("0x00638025", "RET", pcode=[_p("RETURN")]),
    ]


def _default_backend_b(module):
    return [
        _ins(
            module.FALLBACK_BACKEND,
            "JMP",
            ["0x0063a000"],
            flows=["0x0063a000"],
            pcode=[_p("BRANCH")],
        )
    ]


def _fixture(tmp_path, *, backend_a=None, backend_b=None, upstream_ready=True):
    module = _load_module()
    upstream = _write_json(
        tmp_path / "create_helper_return.json",
        {
            "format": module.UPSTREAM_FORMAT,
            "all_reachable_helper_exits_backend_sourced": upstream_ready,
            "exits": [
                {
                    "kind": "ret",
                    "backend_target": module.ALLOCATION_BACKEND,
                    "machine_exit_provenance_state": "verified",
                },
                {
                    "kind": "tail-call",
                    "backend_target": module.FALLBACK_BACKEND,
                    "machine_exit_provenance_state": "verified",
                },
            ],
            "vehicle_create_bridges": [
                {
                    "descriptor": 2,
                    "class_name": "VehicleCandidate",
                    "vehicle_pointer_function": "0x00715700",
                    "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                    "stored_table_address": "0x00402200",
                    "factory_function": "0x00100000",
                    "preinitializer_helper": "0x00886900",
                    "initializer_candidate": "0x00102000",
                    "allocation_request_value": 56,
                    "helper_machine_exit_provenance_state": "verified",
                    "helper_return_value_semantics_state": "inferred",
                    "helper_return_is_allocated_pointer_proven": False,
                }
            ],
        },
    )
    backend = _write_json(
        tmp_path / "memory_backend.json",
        {
            "format": module.BACKEND_FORMAT,
            "functions": [
                {
                    "address": module.ALLOCATION_BACKEND,
                    "name": "FUN_00638020",
                    "role": "allocation-diagnostic-backend",
                    "calling_convention": "__fastcall",
                },
                {
                    "address": module.FALLBACK_BACKEND,
                    "name": "FUN_006382b0",
                    "role": "create-fallback-backend",
                    "calling_convention": "__fastcall",
                },
            ],
        },
    )
    export = _write_jsonl(
        tmp_path / "backend_instructions.jsonl",
        [
            _row(
                module,
                module.ALLOCATION_BACKEND,
                "FUN_00638020",
                backend_a if backend_a is not None else _default_backend_a(module),
            ),
            _row(
                module,
                module.FALLBACK_BACKEND,
                "FUN_006382b0",
                backend_b if backend_b is not None else _default_backend_b(module),
            ),
        ],
    )
    return module, upstream, backend, export


def test_exact_call_result_and_tail_target_form_verified_frontier(tmp_path):
    module, upstream, backend, export = _fixture(tmp_path)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)

    assert report["format"] == "SHIFT.VehicleCreateBackendReturnOriginFrontier/1"
    assert report["backend_count"] == 2
    assert report["verified_backend_return_origin_count"] == 2
    assert report["all_backend_machine_return_origins_resolved"] is True
    assert report["next_backend_return_targets"] == ["0x00639000", "0x0063a000"]

    allocation = next(row for row in report["backends"] if row["address"] == module.ALLOCATION_BACKEND)
    ret = allocation["exits"][0]
    assert ret["kind"] == "ret"
    assert ret["machine_return_origin_state"] == "verified"
    assert ret["unique_eax_origin"]["kind"] == "direct-call-result"
    assert ret["unique_eax_origin"]["target"] == "0x00639000"
    assert ret["allocated_pointer_return_proven"] is False

    fallback = next(row for row in report["backends"] if row["address"] == module.FALLBACK_BACKEND)
    tail = fallback["exits"][0]
    assert tail["kind"] == "external-tail-transfer"
    assert tail["target"] == "0x0063a000"
    assert tail["machine_return_origin_state"] == "verified"

    joined = report["vehicle_create_bridges"][0]
    assert joined["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert joined["allocation_request_value"] == 56
    assert joined["create_backend_return_frontier_state"] == "verified"
    assert joined["backend_return_value_semantics_state"] == "unknown"
    assert joined["helper_return_is_allocated_pointer_proven"] is False
    assert report["scope"]["allocated_pointer_return_proven"] is False
    assert report["scope"]["operator_new_identity_proven"] is False


def test_eax_constant_clobber_replaces_prior_call_origin_without_false_target(tmp_path):
    module = _load_module()
    backend_a = [
        _ins(
            module.ALLOCATION_BACKEND,
            "CALL",
            ["0x00639000"],
            fallthrough="0x00638025",
            flows=["0x00639000"],
            pcode=[_p("CALL")],
        ),
        _ins(
            "0x00638025",
            "XOR",
            ["EAX", "EAX"],
            fallthrough="0x00638027",
            pcode=[_p("INT_XOR")],
        ),
        _ins("0x00638027", "RET", pcode=[_p("RETURN")]),
    ]
    module, upstream, backend, export = _fixture(tmp_path, backend_a=backend_a)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)

    allocation = next(row for row in report["backends"] if row["address"] == module.ALLOCATION_BACKEND)
    origin = allocation["exits"][0]["unique_eax_origin"]
    assert origin["kind"] == "constant"
    assert origin["detail"] == "0x0"
    assert allocation["machine_return_origins_resolved"] is True
    assert "0x00639000" not in report["next_backend_return_targets"]
    assert "0x0063a000" in report["next_backend_return_targets"]


def test_cfg_merge_with_two_call_results_is_ambiguous(tmp_path):
    module = _load_module()
    backend_a = [
        _ins(
            module.ALLOCATION_BACKEND,
            "JZ",
            ["0x00638030"],
            fallthrough="0x00638022",
            flows=["0x00638030"],
            pcode=[_p("CBRANCH")],
        ),
        _ins(
            "0x00638022",
            "CALL",
            ["0x00639100"],
            fallthrough="0x00638040",
            flows=["0x00639100"],
            pcode=[_p("CALL")],
        ),
        _ins(
            "0x00638030",
            "CALL",
            ["0x00639200"],
            fallthrough="0x00638040",
            flows=["0x00639200"],
            pcode=[_p("CALL")],
        ),
        _ins("0x00638040", "RET", pcode=[_p("RETURN")]),
    ]
    module, upstream, backend, export = _fixture(tmp_path, backend_a=backend_a)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)

    allocation = next(row for row in report["backends"] if row["address"] == module.ALLOCATION_BACKEND)
    ret = allocation["exits"][0]
    assert ret["machine_return_origin_state"] == "ambiguous"
    assert len(ret["eax_origins"]) == 2
    assert allocation["machine_return_origins_resolved"] is False
    assert report["all_backend_machine_return_origins_resolved"] is False
    assert any(row["id"] == "ret-eax-origin-not-unique-and-resolved" for row in allocation["blockers"])


def test_call_without_pcode_call_keeps_return_origin_ambiguous(tmp_path):
    module = _load_module()
    backend_a = [
        _ins(
            module.ALLOCATION_BACKEND,
            "CALL",
            ["0x00639000"],
            fallthrough="0x00638025",
            flows=["0x00639000"],
            pcode=[],
        ),
        _ins("0x00638025", "RET", pcode=[_p("RETURN")]),
    ]
    module, upstream, backend, export = _fixture(tmp_path, backend_a=backend_a)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)
    allocation = next(row for row in report["backends"] if row["address"] == module.ALLOCATION_BACKEND)
    assert allocation["exits"][0]["unique_eax_origin"]["kind"] == "ambiguous-call-result"
    assert allocation["exits"][0]["machine_return_origin_state"] == "ambiguous"
    assert allocation["machine_return_origins_resolved"] is False


def test_external_tail_without_branch_pcode_is_ambiguous(tmp_path):
    module = _load_module()
    backend_b = [
        _ins(
            module.FALLBACK_BACKEND,
            "JMP",
            ["0x0063a000"],
            flows=["0x0063a000"],
            pcode=[],
        )
    ]
    module, upstream, backend, export = _fixture(tmp_path, backend_b=backend_b)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)
    fallback = next(row for row in report["backends"] if row["address"] == module.FALLBACK_BACKEND)
    assert fallback["exits"][0]["machine_return_origin_state"] == "ambiguous"
    assert fallback["machine_return_origins_resolved"] is False
    assert any(row["id"] == "external-tail-not-exact-direct-branch" for row in fallback["blockers"])


def test_partial_eax_write_after_call_is_fail_closed(tmp_path):
    module = _load_module()
    backend_a = [
        _ins(
            module.ALLOCATION_BACKEND,
            "CALL",
            ["0x00639000"],
            fallthrough="0x00638025",
            flows=["0x00639000"],
            pcode=[_p("CALL")],
        ),
        _ins(
            "0x00638025",
            "MOV",
            ["AL", "1"],
            fallthrough="0x00638027",
            pcode=[_p("COPY")],
        ),
        _ins("0x00638027", "RET", pcode=[_p("RETURN")]),
    ]
    module, upstream, backend, export = _fixture(tmp_path, backend_a=backend_a)
    report = module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)
    allocation = next(row for row in report["backends"] if row["address"] == module.ALLOCATION_BACKEND)
    assert allocation["exits"][0]["unique_eax_origin"]["kind"] == "partial-eax-write"
    assert allocation["machine_return_origins_resolved"] is False


def test_upstream_create_helper_frontier_must_be_fully_backend_sourced(tmp_path):
    module, upstream, backend, export = _fixture(tmp_path, upstream_ready=False)
    with pytest.raises(ValueError, match="not fully backend-sourced"):
        module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)


def test_missing_backend_instruction_export_fails_closed(tmp_path):
    module, upstream, backend, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    _write_jsonl(export, rows[:1])
    with pytest.raises(ValueError, match="instruction export missing create backend"):
        module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)


def test_backend_role_drift_fails_closed(tmp_path):
    module, upstream, backend, export = _fixture(tmp_path)
    payload = json.loads(backend.read_text(encoding="utf-8"))
    payload["functions"][0]["role"] = "guessed-allocator"
    _write_json(backend, payload)
    with pytest.raises(ValueError, match="backend role drift"):
        module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)


def test_instruction_format_drift_fails_closed(tmp_path):
    module, upstream, backend, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_vehicle_create_backend_return_frontier(upstream, backend, export)
