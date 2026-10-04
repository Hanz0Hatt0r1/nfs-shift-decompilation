from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_memory_load_provenance.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_memory_load_provenance", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _varnode(
    text: str,
    *,
    space: str = "register",
    offset: str = "0x0",
    size: int = 4,
    constant: bool = False,
    register: bool = True,
    unique: bool = False,
) -> dict:
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _load_instruction(
    address: str,
    operand: str,
    *,
    output: str = "EAX",
    fallthrough: str,
) -> dict:
    return {
        "address": address,
        "bytes": "8b",
        "mnemonic": "MOV",
        "text": f"MOV {output},{operand}",
        "operands": [output, operand],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "LOAD",
                "text": f"{output} = LOAD ram({operand})",
                "output": _varnode(output),
                "inputs": [
                    _varnode(
                        "RAM",
                        space="const",
                        offset="0x1",
                        constant=True,
                        register=False,
                    ),
                    _varnode("ECX"),
                ],
            }
        ],
    }


def _store_instruction(address: str, *, fallthrough: str, field: int = 0x33B0) -> dict:
    operand = f"[ECX+0x{field:x}]"
    return {
        "address": address,
        "bytes": "89",
        "mnemonic": "MOV",
        "text": f"MOV {operand},EAX",
        "operands": [operand, "EAX"],
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [],
        "references": [],
        "pcode": [
            {
                "opcode": "STORE",
                "text": f"STORE ram({operand}) = EAX",
                "output": None,
                "inputs": [
                    _varnode(
                        "RAM",
                        space="const",
                        offset="0x1",
                        constant=True,
                        register=False,
                    ),
                    _varnode("ECX"),
                    _varnode("EAX"),
                ],
            }
        ],
    }


def _ret(address: str) -> dict:
    return {
        "address": address,
        "bytes": "c3",
        "mnemonic": "RET",
        "text": "RET",
        "operands": [],
        "flow_type": "TERMINATOR",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": [],
    }


def _instruction_export(tmp_path: Path, *, load_operand: str = "[ECX+0x20]") -> Path:
    instructions = [
        _load_instruction("0x0076b280", load_operand, fallthrough="0x0076b284"),
        _store_instruction("0x0076b284", fallthrough="0x0076b288"),
        _ret("0x0076b288"),
    ]
    row = {
        "format": MODULE.INSTRUCTION_FORMAT,
        "program": MODULE._stores.PROGRAM,
        "requested": MODULE._stores.TARGET,
        "found": True,
        "function": {
            "address": MODULE._stores.TARGET,
            "name": MODULE._stores.TARGET_NAME,
            "size": MODULE._stores.TARGET_SIZE,
            "calling_convention": MODULE._stores.TARGET_CALLING_CONVENTION,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }
    path = tmp_path / "instructions.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


def _store_report(
    tmp_path: Path,
    *,
    dependency_opcode: str = "LOAD",
    root_kinds: tuple[str, ...] = ("external-or-memory-varnode",),
    numeric_preclaim: bool = False,
) -> Path:
    report = {
        "format": MODULE.STORE_FORMAT,
        "version": 1,
        "ready": True,
        "retail": {
            "function": {
                "address": MODULE._stores.TARGET,
                "mnemonic_sha256": MODULE._stores.TARGET_MNEMONIC_SHA256,
            }
        },
        "analysis": {
            "store_candidates": [
                {
                    "instruction": "0x0076b284",
                    "target_is_FUN_0076b280_entry_ECX_on_all_reachable_paths": True,
                    "HDVehicle_field_semantics_joined_from_symbolic_relation": True,
                    "BMW_numeric_offset_value_proven": numeric_preclaim,
                    "offset33b_fields_touched": ["offset33b.x"],
                    "dependency_slice": [
                        {
                            "id": "0x0076b280:0",
                            "instruction": "0x0076b280",
                            "opcode": dependency_opcode,
                            "text": "EAX = LOAD ram([ECX+0x20])",
                        }
                    ],
                    "terminal_root_kinds": list(root_kinds),
                }
            ]
        },
        "handoff": {
            "offset33b_store_provenance_ready": True,
            "offset33b_value_root_frontier_ready": True,
            "BMW_numeric_offset33b_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }
    path = tmp_path / "stores.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _additional_mass_proof(
    tmp_path: Path,
    *,
    participant_offset: int = 0xBA0,
    vehicle_offset: int = 0x860,
) -> Path:
    report = {
        "format": MODULE.ADDITIONAL_MASS_FORMAT,
        "ready": True,
        "proof": {
            "storage_alias": {
                "participant_additional_mass_offset": participant_offset,
                "vehicle_additional_mass_offset": vehicle_offset,
            },
            "offset33b_root": {
                "semantic_name": "additional participant mass term",
                "participant_storage": "participant+0xba0",
                "vehicle_alias_storage": "Vehicle+0x860",
                "value_type": "float32",
                "value": 0.0,
                "numeric_value_proven": True,
            },
        },
        "gates": {
            "offset33b_additional_mass_bootstrap_zero_ready": True,
            "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap": True,
            "BMW_numeric_offset33b_ready": False,
        },
    }
    path = tmp_path / "additional_mass.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_exact_load_becomes_object_origin_field_worklist(tmp_path):
    report = MODULE.analyze_bmw_offset33b_memory_load_provenance(
        _store_report(tmp_path),
        _instruction_export(tmp_path),
        _additional_mass_proof(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "exact-memory-field-worklist-ready"
    assert report["analysis"]["slice_LOAD_node_count"] == 1
    assert report["analysis"]["machine_LOAD_join_count"] == 1

    load = report["analysis"]["load_sources"][0]
    assert load["node_id"] == "0x0076b280:0"
    assert load["base_register"] == "ECX"
    assert load["base_register_origins"] == ["entry:ECX"]
    assert load["base_origin_class"] == "single-entry-register-origin"
    assert load["displacement"] == 0x20
    assert load["load_width"] == 4
    assert load["feeds_offset33b_fields"] == ["offset33b.x"]
    assert load["object_field_reference_ready"] is True
    assert load["resource_or_object_semantics_proven"] is False
    assert load["numeric_loaded_value_proven"] is False

    worklist = report["analysis"]["exact_object_field_worklist"]
    assert worklist == [
        {
            "base_origin_expression_set": ["entry:ECX"],
            "displacement": 0x20,
            "displacement_hex": "0x20",
            "load_width": 4,
            "load_node_ids": ["0x0076b280:0"],
            "load_instructions": ["0x0076b280"],
            "feeds_offset33b_fields": ["offset33b.x"],
            "semantic_owner_or_resource": None,
            "semantic_field_name": None,
            "semantic_join_ready": False,
        }
    ]
    assert report["handoff"]["offset33b_exact_memory_field_worklist_ready"] is True
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_additional_mass_displacement_is_not_semantically_promoted(tmp_path):
    report = MODULE.analyze_bmw_offset33b_memory_load_provenance(
        _store_report(tmp_path),
        _instruction_export(tmp_path, load_operand="[ECX+0xba0]"),
        _additional_mass_proof(tmp_path),
    )

    load = report["analysis"]["load_sources"][0]
    assert load["displacement"] == 0xBA0
    assert load["matches_additional_mass_displacement_only"] is True
    assert load["additional_mass_pointer_identity_proven"] is False
    assert load["additional_mass_zero_applied_to_this_load"] is False
    reduction = report["known_semantic_reductions"]["additional_mass_first_bootstrap"]
    assert reduction["value"] == 0.0
    assert reduction["term_elidable_for_first_bootstrap"] is True
    assert reduction["machine_LOAD_pointer_identity_joined"] is False
    assert reduction["displacement_only_candidate_load_nodes"] == ["0x0076b280:0"]
    assert reduction["displacement_match_is_semantic_identity"] is False
    assert report["scope"]["matching_0xba0_or_0x860_displacement_promoted_to_additional_mass"] is False


def test_complex_machine_load_operand_blocks_structural_join(tmp_path):
    report = MODULE.analyze_bmw_offset33b_memory_load_provenance(
        _store_report(tmp_path),
        _instruction_export(tmp_path, load_operand="[ECX+EAX*4]"),
        _additional_mass_proof(tmp_path),
    )

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert report["analysis"]["machine_LOAD_join_count"] == 0
    assert report["handoff"]["offset33b_memory_LOAD_frontier_ready"] is False
    assert any(
        row["id"] == "offset33b-slice-load-machine-operand-ambiguous"
        for row in report["blockers"]
    )


def test_memory_root_without_structured_load_remains_semantic_blocker(tmp_path):
    report = MODULE.analyze_bmw_offset33b_memory_load_provenance(
        _store_report(tmp_path, dependency_opcode="INT_ADD"),
        _instruction_export(tmp_path),
        _additional_mass_proof(tmp_path),
    )

    assert report["ready"] is True
    assert report["status"] == "memory-load-frontier-ready"
    assert report["analysis"]["slice_LOAD_node_count"] == 0
    assert report["handoff"]["offset33b_exact_memory_field_worklist_ready"] is False
    assert any(
        row["id"] == "offset33b-memory-root-without-structured-LOAD-node"
        for row in report["blockers"]
    )


def test_store_numeric_preclaim_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims numeric value"):
        MODULE.analyze_bmw_offset33b_memory_load_provenance(
            _store_report(tmp_path, numeric_preclaim=True),
            _instruction_export(tmp_path),
            _additional_mass_proof(tmp_path),
        )


def test_additional_mass_alias_drift_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="participant offset drift"):
        MODULE.analyze_bmw_offset33b_memory_load_provenance(
            _store_report(tmp_path),
            _instruction_export(tmp_path),
            _additional_mass_proof(tmp_path, participant_offset=0xB9C),
        )


def test_dependency_load_node_must_exist_in_exact_instruction_export(tmp_path):
    stores = json.loads(_store_report(tmp_path).read_text(encoding="utf-8"))
    stores["analysis"]["store_candidates"][0]["dependency_slice"][0]["id"] = "0x0076b281:0"
    store_path = tmp_path / "stores_missing_node.json"
    store_path.write_text(json.dumps(stores), encoding="utf-8")

    report = MODULE.analyze_bmw_offset33b_memory_load_provenance(
        store_path,
        _instruction_export(tmp_path),
        _additional_mass_proof(tmp_path),
    )
    assert report["ready"] is False
    assert any(
        row["id"] == "offset33b-slice-load-node-missing-from-instruction-export"
        for row in report["blockers"]
    )
