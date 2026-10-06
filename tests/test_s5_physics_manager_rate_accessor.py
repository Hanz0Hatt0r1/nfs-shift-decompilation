from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_physics_manager_rate_accessor.py"
RUNNER = ROOT / "tools/ghidra/run_s5_physics_manager_rate_accessor_slice.sh"
SPEC = importlib.util.spec_from_file_location("analyze_s5_physics_manager_rate_accessor", ANALYZER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _varnode(text: str, *, space: str = "register", output: bool = False) -> dict:
    offsets = {"EAX": "0x0", "ECX": "0x4", "ESP": "0x10"}
    return {
        "text": text,
        "space": space,
        "offset": offsets.get(text, "0x100"),
        "size": 4,
        "constant": space == "const",
        "register": space == "register",
        "unique": space == "unique",
    }


def _op(opcode: str, *, output=None, inputs=None) -> dict:
    return {
        "opcode": opcode,
        "text": opcode,
        "output": output,
        "inputs": inputs or [],
    }


def _ins(address: int, mnemonic: str, operands=None, pcode=None, flows=None) -> dict:
    operands = operands or []
    return {
        "address": f"0x{address:08x}",
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "references": [],
        "flows": [f"0x{value:08x}" for value in (flows or [])],
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "pcode": pcode or [_op("COPY")],
    }


def _call(address: int, target: int) -> dict:
    return _ins(
        address,
        "CALL",
        [f"0x{target:08x}"],
        [_op("CALL", inputs=[_varnode(f"0x{target:08x}", space="const")])],
        [target],
    )


def _branch(address: int, target: int) -> dict:
    return _ins(
        address,
        "JNZ",
        [f"0x{target:08x}"],
        [_op("CBRANCH", inputs=[_varnode(f"0x{target:08x}", space="const")])],
        [target],
    )


def _row(address: int, name: str, instructions: list[dict]) -> dict:
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "requested": f"0x{address:08x}",
        "found": True,
        "function": {"address": f"0x{address:08x}", "name": name},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(
    tmp_path: Path,
    *,
    accessor_clobber: bool = False,
    singleton_load_storage: str = "DAT_00c00000",
    consumer_clobber: bool = False,
) -> tuple[Path, Path, Path, Path]:
    consumer = [_call(0x0071307C, 0x0070FE90)]
    if consumer_clobber:
        consumer.append(
            _ins(
                0x00713080,
                "MOV",
                ["EAX", "ECX"],
                [_op("COPY", output=_varnode("EAX"), inputs=[_varnode("ECX")])],
            )
        )
    consumer.extend(
        [
            _ins(
                0x00713084,
                "FILD",
                ["dword ptr [EAX + 0x388]"],
                [_op("LOAD", output=_varnode("u_rate", space="unique"))],
            ),
            _ins(0x00713090, "RET", [], [_op("RETURN")]),
        ]
    )

    accessor = [_call(0x0070FE93, 0x0041903C)]
    if accessor_clobber:
        accessor.append(
            _ins(
                0x0070FE97,
                "MOV",
                ["EAX", "ECX"],
                [_op("COPY", output=_varnode("EAX"), inputs=[_varnode("ECX")])],
            )
        )
    accessor.append(_ins(0x0070FE98, "RET", [], [_op("RETURN")]))

    wrapper = [
        _call(0x00419042, 0x0070FE99),
        _ins(0x00419046, "RET", [], [_op("RETURN")]),
    ]

    singleton = [
        _ins(
            0x0070FEA0,
            "CMP",
            ["dword ptr [DAT_00c00000]", "0"],
            [_op("LOAD", output=_varnode("u_guard", space="unique"))],
        ),
        _branch(0x0070FEA8, 0x0070FED8),
        _call(0x0070FEC7, 0x0070FAE0),
        _ins(
            0x0070FECC,
            "MOV",
            ["dword ptr [DAT_00c00000]", "EAX"],
            [_op("STORE", inputs=[_varnode("EAX")])],
        ),
        _call(0x0070FED1, 0x00900FB3),
        _ins(
            0x0070FED8,
            "MOV",
            ["EAX", f"dword ptr [{singleton_load_storage}]"],
            [_op("LOAD", output=_varnode("EAX"))],
        ),
        _ins(0x0070FEE0, "RET", [], [_op("RETURN")]),
    ]

    constructor = [_ins(0x0070FAE0, "RET", [], [_op("RETURN")])]

    export = tmp_path / "instructions.jsonl"
    export.write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in [
                _row(0x00713050, "FUN_00713050", consumer),
                _row(0x0070FE90, "FUN_0070fe90", accessor),
                _row(0x0041903C, "FUN_0041903c", wrapper),
                _row(0x0070FE99, "FUN_0070fe99", singleton),
                _row(0x0070FAE0, "FUN_0070fae0", constructor),
            ]
        ),
        encoding="utf-8",
    )

    functions = tmp_path / "functions.jsonl"
    function_rows = [
        {
            "address": "0x0070fe90",
            "name": "FUN_0070fe90",
            "calling_convention": "__stdcall",
            "parameters": [],
            "mnemonic_sha256": "a81f2450cab727e62d5915024328163bbc4ba11d7c1d57322e48dead4ff422d1",
        },
        {
            "address": "0x0041903c",
            "name": "FUN_0041903c",
            "calling_convention": "__stdcall",
            "parameters": [],
            "mnemonic_sha256": "176a39ed845abe7a6fbe51c430190743abeda60e4c62b6f9c3b68280720750d4",
        },
        {
            "address": "0x0070fe99",
            "name": "FUN_0070fe99",
            "calling_convention": "__stdcall",
            "parameters": [],
            "mnemonic_sha256": "6bec7a7a51d4bd781503a6c2d6c09ebad9bef45d2ef171ecce650cea7c9e3ced",
        },
        {
            "address": "0x0070fae0",
            "name": "FUN_0070fae0",
            "calling_convention": "__fastcall",
            "parameters": [{"name": "param_1", "type": "undefined4 *", "storage": "ECX:4"}],
            "mnemonic_sha256": MODULE.CONSTRUCTOR_FINGERPRINT,
        },
    ]
    functions.write_text(
        "".join(json.dumps(row) + "\n" for row in function_rows), encoding="utf-8"
    )

    owner = tmp_path / "owner.json"
    owner.write_text(
        json.dumps(
            {
                "format": "SHIFT.PhysicsManagerSchedulerEntryOwner/1",
                "ready": True,
                "owner": "MWL::Core::cPhysicsManager",
                "provenance": {"source_manager_contract": "SHIFT.PhysicsManagerRuntime/1"},
            }
        ),
        encoding="utf-8",
    )

    runtime = tmp_path / "physics_system_runtime.py"
    runtime.write_text(
        'MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"\n'
        'MANAGER_VTABLE = "PTR_FUN_00b04524"\n'
        'MANAGER_LAYOUT = {"functions": ["FUN_0070fae0"], "named_object": "Physics Manager"}\n'
        'X = {"named_object": "Physics Manager"}\n',
        encoding="utf-8",
    )
    return export, functions, owner, runtime


def test_positive_chain_proves_object_alias_but_not_units_or_frequency_name(tmp_path):
    report = MODULE.analyze(*_fixture(tmp_path))

    assert report["format"] == "SHIFT.PhysicsManagerRateAccessorAlias/1"
    assert report["ready"] is True
    assert report["status"] == "accessor-alias-and-plus-0x388-owner-proven"
    adjudication = report["adjudication"]
    assert adjudication["FUN_0070fe90_return_aliases_source_backed_cPhysicsManager_instance"] is True
    assert adjudication["plus_0x388_is_cPhysicsManager_field"] is True
    assert adjudication["plus_0x388_semantic_name_frequency"] is False
    assert adjudication["plus_0x388_value_or_units_proven"] is False
    assert adjudication["fixed_timestep_semantics_proven"] is False
    assert adjudication["retail_cadence_admitted"] is False


def test_eax_clobber_in_passthrough_wrapper_fails_closed(tmp_path):
    report = MODULE.analyze(*_fixture(tmp_path, accessor_clobber=True))

    assert report["ready"] is False
    assert report["wrapper_return_provenance"]["FUN_0070fe90"][
        "callee_eax_reaches_return_unchanged"
    ] is False
    assert "FUN_0070fe90-return-alias-to-Physics-Manager-constructor-not-proven" in report[
        "blocking_reasons"
    ]


def test_singleton_storage_mismatch_fails_closed(tmp_path):
    report = MODULE.analyze(
        *_fixture(tmp_path, singleton_load_storage="DAT_00c00004")
    )

    assert report["ready"] is False
    singleton = report["wrapper_return_provenance"]["FUN_0070fe99"]
    assert singleton["constructor_return_populates_returned_singleton_storage"] is False


def test_consumer_eax_clobber_before_plus_0x388_load_fails_closed(tmp_path):
    report = MODULE.analyze(*_fixture(tmp_path, consumer_clobber=True))

    assert report["ready"] is False
    assert report["consumer_rate_read"][
        "accessor_return_directly_bases_plus_0x388_load"
    ] is False


def test_runtime_contract_drift_is_rejected(tmp_path):
    export, functions, owner, runtime = _fixture(tmp_path)
    runtime.write_text('MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="runtime source contract drift"):
        MODULE.analyze(export, functions, owner, runtime)


def test_runner_scope_is_exact_static_five_function_slice():
    source = RUNNER.read_text(encoding="utf-8")
    assert "run_shift_function_instructions.sh" in source
    assert "analyze_s5_physics_manager_rate_accessor.py" in source
    for name in (
        "FUN_00713050",
        "FUN_0070fe90",
        "FUN_0041903c",
        "FUN_0070fe99",
        "FUN_0070fae0",
    ):
        assert source.count(name) == 1
    assert "shift_d3d9_capture" not in source.lower()
    assert "wine" not in source.lower()
    assert "game/runtime execution" in source.lower()
