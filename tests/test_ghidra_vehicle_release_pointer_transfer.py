import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_release_pointer_transfer.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_release_pointer_transfer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _pcode(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _ins(address, mnemonic, operands, *, flows=None, pcode=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} " + ",".join(operands),
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _call(address, target):
    return _ins(address, "CALL", [target], flows=[target], pcode=[_pcode("CALL")])


def _row(helper_format, address, cc, instructions):
    return {
        "format": helper_format,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions) * 4,
            "calling_convention": cc,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(tmp_path, *, pushed_register="ESI", wrapper_cc="__thiscall", manifest_storage="Stack[0x4]:4"):
    module = _load_module()
    wrapper = "0x00103000"
    teardown = "0x00104000"
    release = "0x00886930"

    teardown_trace = {
        "evidence_state": "verified",
        "status": "register-copy-chain",
        "source": {"kind": "function-entry-register", "register": "ECX"},
        "chain": [],
    }
    lifetime = {
        "format": module.LIFETIME_FORMAT,
        "delete_transfer_count": 1,
        "delete_transfers": [
            {
                "descriptor": 2,
                "class_name": "Child",
                "deleting_wrapper_function": wrapper,
                "teardown_transition_function": teardown,
                "release_helper": release,
                "machine_wrapper_entry_to_teardown_receiver_state": "verified",
                "machine_wrapper_entry_to_teardown_receiver": teardown_trace,
                "teardown_value_transfer_state": "inferred",
                "release_argument_value_transfer_state": "unknown",
            }
        ],
    }
    lifetime_path = tmp_path / "lifetime.json"
    _write_json(lifetime_path, lifetime)

    manifest = {
        "format": module.MANIFEST_FORMAT,
        "runtime_contract_status": "source-joined-semantic-roles",
        "wrappers": [
            {
                "address": release,
                "name": "FUN_00886930",
                "reported_calling_convention": "__fastcall",
                "forwarding_confirmed": True,
                "parameters": [
                    {
                        "source_argument_index": 0,
                        "entry_storage": "ECX:4",
                        "name": "arg0",
                        "semantic_role": None,
                        "semantic_role_proven": False,
                    },
                    {
                        "source_argument_index": 1,
                        "entry_storage": "DL:1",
                        "name": "arg1",
                        "semantic_role": None,
                        "semantic_role_proven": False,
                    },
                    {
                        "source_argument_index": 2,
                        "entry_storage": manifest_storage,
                        "name": "released_pointer",
                        "semantic_role": "released-pointer",
                        "semantic_role_proven": True,
                    },
                ],
                "status": "partial-semantic-parameters",
                "blockers": [],
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)

    prefix = []
    if pushed_register == "ESI":
        prefix.append(_ins("0x00103004", "MOV", ["ESI", "ECX"], pcode=[_pcode("COPY")]))
        prefix.append(_ins("0x00103008", "MOV", ["ECX", "ESI"], pcode=[_pcode("COPY")]))
    elif pushed_register == "EAX":
        prefix.append(_ins("0x00103004", "MOV", ["EAX", "ECX"], pcode=[_pcode("COPY")]))
        prefix.append(_ins("0x00103008", "MOV", ["ECX", "EAX"], pcode=[_pcode("COPY")]))
    else:
        prefix.append(_ins("0x00103004", "MOV", [pushed_register, "ECX"], pcode=[_pcode("COPY")]))
        prefix.append(_ins("0x00103008", "MOV", ["ECX", pushed_register], pcode=[_pcode("COPY")]))

    wrapper_instructions = prefix + [
        _call("0x0010300c", teardown),
        _ins("0x00103011", "TEST", ["EAX", "EAX"], pcode=[_pcode("INT_EQUAL")]),
        _ins("0x00103013", "PUSH", [pushed_register], pcode=[_pcode("STORE")]),
        _ins("0x00103014", "MOV", ["DL", "1"], pcode=[_pcode("COPY")]),
        _ins("0x00103016", "MOV", ["ECX", "0"], pcode=[_pcode("COPY")]),
        _call("0x0010301b", release),
    ]
    export_path = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export_path,
        [
            _row(module.INSTRUCTION_FORMAT, wrapper, wrapper_cc, wrapper_instructions),
            _row(module.INSTRUCTION_FORMAT, teardown, "__thiscall", [_ins("0x00104000", "NOP", [])]),
        ],
    )
    return {
        "module": module,
        "lifetime": lifetime_path,
        "manifest": manifest_path,
        "export": export_path,
        "wrapper": wrapper,
        "teardown": teardown,
        "release": release,
    }


def _run(fx):
    return fx["module"].analyze_vehicle_release_pointer_transfer(
        fx["lifetime"], fx["manifest"], fx["export"]
    )


def test_joins_saved_nonvolatile_wrapper_value_to_proven_released_pointer_parameter(tmp_path):
    fx = _fixture(tmp_path)
    report = _run(fx)

    assert report["format"] == "SHIFT.VehicleReleasePointerTransfer/1"
    assert report["transfer_count"] == 1
    row = report["transfers"][0]
    assert row["released_pointer_parameter_semantic_state"] == "proven"
    assert row["released_pointer_parameter_semantics_proven"] is True
    assert row["release_stack_argument"]["status"] == "released-pointer-stack-argument-push"
    assert row["release_stack_argument"]["stack_mapping_state"] == "verified"
    assert row["release_stack_argument"]["push_register"] == "ESI"
    assert row["release_stack_argument"]["origin"]["source"] == {
        "kind": "function-entry-register",
        "register": "ECX",
    }
    assert row["release_stack_argument_machine_state"] == "inferred"
    assert row["release_argument_originates_at_wrapper_entry_ecx"] is True
    assert row["wrapper_entry_to_teardown_receiver_verified"] is True
    assert row["same_wrapper_entry_value_to_teardown_and_release_state"] == "inferred"
    assert row["release_pointer_lifetime_transfer_state"] == "inferred"
    crossed = row["release_stack_argument"]["origin"]["crossed_calls"]
    assert crossed[0]["target"] == fx["teardown"]
    assert crossed[0]["tracked_nonvolatile_register"] == "ESI"
    assert row["operator_delete_identity_proven"] is False


def test_volatile_saved_register_cannot_cross_teardown_call(tmp_path):
    fx = _fixture(tmp_path, pushed_register="EAX")
    report = _run(fx)
    row = report["transfers"][0]
    assert row["release_stack_argument"]["origin"]["status"] == "call-clobber-boundary"
    assert row["release_stack_argument_machine_state"] == "ambiguous"
    assert row["release_argument_originates_at_wrapper_entry_ecx"] is False
    assert row["release_pointer_lifetime_transfer_state"] == "unknown"


def test_unsupported_manifest_storage_keeps_release_transfer_unknown(tmp_path):
    fx = _fixture(tmp_path, manifest_storage="Stack[0x8]:4")
    report = _run(fx)
    row = report["transfers"][0]
    assert row["released_pointer_parameter_status"] == "released-pointer-storage-shape-unsupported"
    assert row["released_pointer_parameter_semantic_state"] == "unknown"
    assert row["release_stack_argument"]["status"] == "released-pointer-storage-shape-unsupported"


def test_unconfirmed_memory_wrapper_forwarding_is_not_promoted(tmp_path):
    fx = _fixture(tmp_path)
    manifest = json.loads(fx["manifest"].read_text(encoding="utf-8"))
    manifest["wrappers"][0]["forwarding_confirmed"] = False
    _write_json(fx["manifest"], manifest)

    report = _run(fx)
    row = report["transfers"][0]
    assert row["released_pointer_parameter_status"] == "wrapper-forwarding-unconfirmed"
    assert row["released_pointer_parameter_semantics_proven"] is False


def test_non_register_push_is_not_guessed_as_pointer_transfer(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    wrapper = rows[0]
    push = next(ins for ins in wrapper["instructions"] if ins["mnemonic"] == "PUSH")
    push["operands"] = ["dword ptr [ESI]"]
    push["text"] = "PUSH dword ptr [ESI]"
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    row = report["transfers"][0]
    assert row["release_stack_argument"]["status"] == "released-pointer-stack-argument-not-full-gpr-push"
    assert row["release_stack_argument_machine_state"] == "unknown"


def test_stack_pointer_change_between_push_and_call_blocks_mapping(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    wrapper = rows[0]
    release_index = next(i for i, ins in enumerate(wrapper["instructions"]) if fx["release"] in ins["flows"])
    wrapper["instructions"].insert(
        release_index,
        _ins("0x00103019", "SUB", ["ESP", "4"], pcode=[_pcode("INT_SUB")]),
    )
    wrapper["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    row = report["transfers"][0]
    assert row["release_stack_argument"]["status"] in {
        "stack-pointer-modified-before-release-call",
        "explicit-stack-pointer-write-before-release-call",
    }
    assert row["release_stack_argument_machine_state"] == "ambiguous"


def test_multiple_release_calls_remain_ambiguous(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    wrapper = rows[0]
    wrapper["instructions"].append(_call("0x00103030", fx["release"]))
    wrapper["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    row = report["transfers"][0]
    assert row["release_call_count"] == 2
    assert row["release_stack_argument"]["status"] == "release-callsite-not-unique"
    assert row["release_stack_argument_machine_state"] == "ambiguous"


def test_wrapper_not_thiscall_keeps_final_receiver_role_unknown(tmp_path):
    fx = _fixture(tmp_path, wrapper_cc="__cdecl")
    report = _run(fx)
    row = report["transfers"][0]
    assert row["released_pointer_parameter_semantics_proven"] is True
    assert row["wrapper_receiver_abi_role_state"] == "unknown"
    assert row["release_pointer_lifetime_transfer_state"] == "unknown"


def test_missing_teardown_export_blocks_nonvolatile_preservation(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["function"]["address"] != fx["teardown"]]
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    row = report["transfers"][0]
    assert row["release_stack_argument"]["origin"]["status"] == "call-clobber-boundary"
    assert row["release_stack_argument_machine_state"] == "ambiguous"


def test_input_format_drift_fails_closed(tmp_path):
    fx = _fixture(tmp_path)
    manifest = json.loads(fx["manifest"].read_text(encoding="utf-8"))
    manifest["format"] = "SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/0"
    _write_json(fx["manifest"], manifest)

    with pytest.raises(ValueError, match="expected SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1"):
        _run(fx)
