from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_bmw_sdf_vehicle_assembly_receiver_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_bmw_sdf_vehicle_assembly_receiver_provenance_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _varnode(text: str, *, register: bool = True):
    return {
        "text": text,
        "space": "register" if register else "unique",
        "offset": "0x0",
        "size": 4,
        "constant": False,
        "register": register,
        "unique": not register,
    }


def _ins(
    address: str,
    mnemonic: str,
    operands: list[str],
    *,
    fallthrough: str | None = None,
    flows: list[str] | None = None,
    flow_type: str = "FALL_THROUGH",
    outputs: tuple[str, ...] = (),
):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {' '.join(operands)}".strip(),
        "operands": list(operands),
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else list(flows),
        "references": [],
        "pcode": [
            {
                "opcode": "COPY",
                "text": f"{register} = COPY unknown",
                "output": _varnode(register),
                "inputs": [],
            }
            for register in outputs
        ],
    }


def _row(address: str, name: str, instructions: list[dict]):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _retail_export(tmp_path: Path, module, *, fingerprint_drift: bool = False) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({
            "program_name": module.PROGRAM,
            "executable_md5": module.PE_MD5,
        }),
        encoding="utf-8",
    )

    function_rows = []
    for address, expected in module.TARGETS.items():
        digest = expected["mnemonic_sha256"]
        if fingerprint_drift and address == "0x007615c0":
            digest = "0" * 64
        function_rows.append({
            "address": address,
            "name": expected["name"],
            "size": 32,
            "thunk": False,
            "external": False,
            "calling_convention": expected["calling_convention"],
            "signature": "undefined test(void)",
            "parameters": [],
            "mnemonic_sha256": digest,
        })
    _write_jsonl(root / "functions.jsonl", function_rows)

    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": row["caller"],
                "from_name": module.TARGETS[row["caller"]]["name"],
                "instruction": row["callsite"],
                "to": row["callee"],
                "to_name": module.TARGETS[row["callee"]]["name"],
                "indirect": False,
            }
            for row in module.CALLS
        ],
    )
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [{
            "address": "0x00b09cdc",
            "value": module.INIT_LABEL,
            "length": len(module.INIT_LABEL),
            "xrefs": ["0x0076dff0", "0x0076e053"],
            "functions": ["0x0076df50"],
        }],
    )
    return root


def _positive_init(module):
    return [
        _ins(
            "0x0076df50",
            "MOV",
            ["ESI", "ECX"],
            fallthrough="0x0076df52",
            outputs=("ESI",),
        ),
        _ins(
            "0x0076df52",
            "CALL",
            ["0x00700000"],
            fallthrough="0x0076e230",
            flows=["0x00700000"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x0076e230",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x0076e238",
            outputs=("ECX",),
        ),
        _ins(
            "0x0076e238",
            "CALL",
            ["0x007615c0"],
            fallthrough="0x0076e23d",
            flows=["0x007615c0"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076e23d", "RET", [], flow_type="TERMINATOR"),
    ]


def _positive_assembly(module):
    return [
        _ins(
            "0x007615c0",
            "MOV",
            ["EDI", "ECX"],
            fallthrough="0x007615c2",
            outputs=("EDI",),
        ),
        _ins(
            "0x007615c2",
            "CALL",
            ["0x00700010"],
            fallthrough="0x007615e8",
            flows=["0x00700010"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x007615e8",
            "MOV",
            ["ECX", "EDI"],
            fallthrough="0x007615ed",
            outputs=("ECX",),
        ),
        _ins(
            "0x007615ed",
            "CALL",
            ["0x007b6900"],
            fallthrough="0x007615f2",
            flows=["0x007b6900"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x007615f2", "RET", [], flow_type="TERMINATOR"),
    ]


def _instruction_export(tmp_path: Path, module, *, init=None, assembly=None) -> Path:
    path = tmp_path / "targeted.jsonl"
    _write_jsonl(
        path,
        [
            _row(
                "0x0076df50",
                "FUN_0076df50",
                _positive_init(module) if init is None else init,
            ),
            _row(
                "0x007615c0",
                "FUN_007615c0",
                _positive_assembly(module) if assembly is None else assembly,
            ),
        ],
    )
    return path


def test_proves_same_physical_receiver_through_vehicle_init_to_sdf_loader(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    instructions = _instruction_export(tmp_path, module)

    report = module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
        root,
        instructions,
    )

    assert report["format"] == "SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1"
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["blocking_reasons"] == []
    assert len(report["receiver_links"]) == 2
    assert all(
        row["receiver_origins_before_call"] == ["entry:ECX"]
        for row in report["receiver_links"]
    )
    assert all(
        row["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
        for row in report["receiver_links"]
    )
    assert report["analysis"][
        "high_detail_vehicle_init_to_sdf_loader_receiver_continuity_proven"
    ] is True
    assert report["handoff"]["SDF_loader_owner_receiver_continuity_ready"] is True
    assert report["handoff"][
        "SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX"
    ] is True
    assert report["handoff"][
        "SDF_model_to_VHF_vehicle_root_frame_relation_ready"
    ] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["receiver_pointer_identity_is_frame_identity"] is False
    assert report["scope"]["SDF_model_frame_equals_VHF_root_frame_assumed"] is False
    assert report["remaining_frame_blockers"][0]["id"] == (
        "high-detail-vehicle-receiver-to-vhf-root-frame-semantic-binding-unproven"
    )


def test_memory_reload_before_sdf_loader_blocks_receiver_chain(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    assembly = _positive_assembly(module)
    assembly[2] = _ins(
        "0x007615e8",
        "MOV",
        ["ECX", "[EDI+0x20]"],
        fallthrough="0x007615ed",
        outputs=("ECX",),
    )
    instructions = _instruction_export(tmp_path, module, assembly=assembly)

    report = module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
        root,
        instructions,
    )

    assert report["ready"] is False
    second = report["receiver_links"][1]
    assert second["classification"] == "memory-derived-nonidentity"
    assert second["receiver_origins_before_call"] == ["memory:[edi+0x20]"]
    assert report["handoff"]["SDF_loader_owner_receiver_continuity_ready"] is False
    assert report["blocking_reasons"][0]["id"] == (
        "physics-assembly-to-sdf-loader-ECX-continuity-unproven"
    )


def test_divergent_init_cfg_path_keeps_first_receiver_link_ambiguous(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    init = [
        _ins(
            "0x0076df50",
            "MOV",
            ["ESI", "ECX"],
            fallthrough="0x0076df52",
            outputs=("ESI",),
        ),
        _ins(
            "0x0076df52",
            "JNZ",
            ["0x0076e230"],
            fallthrough="0x0076df54",
            flows=["0x0076e230"],
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins(
            "0x0076df54",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x0076df56",
            outputs=("ECX",),
        ),
        _ins(
            "0x0076df56",
            "JMP",
            ["0x0076e238"],
            flows=["0x0076e238"],
            flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins(
            "0x0076e230",
            "MOV",
            ["ECX", "EDI"],
            fallthrough="0x0076e238",
            outputs=("ECX",),
        ),
        _ins(
            "0x0076e238",
            "CALL",
            ["0x007615c0"],
            fallthrough="0x0076e23d",
            flows=["0x007615c0"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076e23d", "RET", [], flow_type="TERMINATOR"),
    ]
    instructions = _instruction_export(tmp_path, module, init=init)

    report = module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
        root,
        instructions,
    )

    assert report["ready"] is False
    first = report["receiver_links"][0]
    assert first["classification"] == "ambiguous"
    assert first["receiver_origins_before_call"] == ["entry:ECX", "entry:EDI"]
    assert report["analysis"][
        "high_detail_vehicle_init_to_sdf_loader_receiver_continuity_proven"
    ] is False


def test_rejects_wrong_direct_call_target(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    init = _positive_init(module)
    init[3] = _ins(
        "0x0076e238",
        "CALL",
        ["0x007615d0"],
        fallthrough="0x0076e23d",
        flows=["0x007615d0"],
        flow_type="UNCONDITIONAL_CALL",
    )
    instructions = _instruction_export(tmp_path, module, init=init)

    with pytest.raises(ValueError, match="expected direct target 0x007615c0"):
        module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
            root,
            instructions,
        )


def test_rejects_retail_mnemonic_fingerprint_drift(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module, fingerprint_drift=True)
    instructions = _instruction_export(tmp_path, module)

    with pytest.raises(ValueError, match="0x007615c0: mnemonic fingerprint drift"):
        module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
            root,
            instructions,
        )


def test_rejects_missing_high_detail_vehicle_init_source_anchor(tmp_path):
    module = _module()
    root = _retail_export(tmp_path, module)
    (root / "strings_xrefs.jsonl").write_text("", encoding="utf-8")
    instructions = _instruction_export(tmp_path, module)

    with pytest.raises(ValueError, match="HighDetailVehicle::Init source/debug label"):
        module.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
            root,
            instructions,
        )
