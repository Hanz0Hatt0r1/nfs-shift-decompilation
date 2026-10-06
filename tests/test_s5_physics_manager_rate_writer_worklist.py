from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SELECTOR_PATH = ROOT / "tools/ghidra/select_s5_physics_manager_rate_writer_targets.py"
ANALYZER_PATH = ROOT / "tools/ghidra/analyze_s5_physics_manager_rate_writer_candidates.py"
RUNNER = ROOT / "tools/ghidra/run_s5_physics_manager_rate_writer_worklist.sh"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECTOR = _load(SELECTOR_PATH, "select_s5_physics_manager_rate_writer_targets")
ANALYZER = _load(ANALYZER_PATH, "analyze_s5_physics_manager_rate_writer_candidates")


def _function(address: int, name: str, digest: str = "f" * 64, **extra) -> dict:
    return {
        "address": f"0x{address:08x}",
        "name": name,
        "namespace": "Global",
        "size": 16,
        "thunk": False,
        "external": False,
        "calling_convention": "__cdecl",
        "parameters": [],
        "mnemonic_sha256": digest,
        **extra,
    }


def _functions(tmp_path: Path, *, drift_anchor: bool = False) -> Path:
    rows = [
        _function(0x0070E000, "FUN_0070e000"),
        _function(0x0070F100, "FUN_0070f100"),
        _function(
            0x0070FAE0,
            "FUN_0070fae0",
            "0" * 64 if drift_anchor else SELECTOR.ANCHORS[0x0070FAE0]["mnemonic_sha256"],
        ),
        _function(
            0x0070FE90,
            "FUN_0070fe90",
            SELECTOR.ANCHORS[0x0070FE90]["mnemonic_sha256"],
        ),
        _function(
            0x00710000,
            "FUN_00710000",
            external=True,
        ),
        _function(
            0x00713050,
            "FUN_00713050",
            SELECTOR.ANCHORS[0x00713050]["mnemonic_sha256"],
        ),
        _function(0x00713060, "FUN_00713060"),
    ]
    path = tmp_path / "functions.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _selection(tmp_path: Path) -> tuple[Path, dict]:
    report = SELECTOR.select(_functions(tmp_path))
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path, report


def _access(
    function: str,
    name: str,
    instruction: str,
    *,
    displacement: int,
    access: str,
    base: str = "ECX",
) -> dict:
    return {
        "function": function,
        "function_name": name,
        "instruction": instruction,
        "instruction_text": f"MOV dword ptr [{base} + 0x{displacement:x}], EAX",
        "operand_index": 0,
        "operand": f"dword ptr [{base} + 0x{displacement:x}]",
        "base_register": base,
        "displacement": displacement,
        "displacement_hex": f"0x{displacement:x}",
        "pcode": [{"opcode": "STORE", "text": "STORE"}],
        "pcode_memory_ops": ["STORE"] if access == "write" else ["LOAD"],
        "promoted": False,
        "access": access,
        "status": "syntactic-register-relative-memory-access",
    }


def _access_report(
    tmp_path: Path,
    selection: dict,
    rows: list[dict],
    *,
    pcode_blockers: int = 0,
    unparsed: int = 0,
) -> Path:
    report = {
        "format": "SHIFT.GhidraRegisterRelativeAccesses/1",
        "instruction_export": "retail.jsonl",
        "instruction_export_format": "SHIFT.GhidraFunctionInstructions/2",
        "base_register_filter": None,
        "function_count": selection["target_count"],
        "instruction_count": 100,
        "access_count": len(rows),
        "access_group_count": len(rows),
        "write_access_count": sum(row["access"] in {"write", "read-write"} for row in rows),
        "read_access_count": sum(row["access"] in {"read", "read-write"} for row in rows),
        "filtered_access_count": 0,
        "pcode_classification_blocker_count": pcode_blockers,
        "unparsed_memory_operand_count": unparsed,
        "accesses": rows,
        "access_groups": [],
        "pcode_classification_blockers": [{}] * pcode_blockers,
        "unparsed_memory_operands": [{}] * unparsed,
        "scope": {"field_semantics_proven": False},
    }
    path = tmp_path / "accesses.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_selector_bounds_export_cost_without_promoting_address_proximity(tmp_path):
    report = SELECTOR.select(_functions(tmp_path))

    assert report["format"] == "SHIFT.PhysicsManagerRateWriterTargetSelection/1"
    assert report["status"] == "bounded-discovery-targets-ready"
    assert report["window"] == {
        "start": "0x0070f000",
        "end": "0x00713050",
        "inclusive": True,
        "selection_semantics": "candidate-discovery-only",
    }
    assert report["target_names"] == [
        "FUN_0070f100",
        "FUN_0070fae0",
        "FUN_0070fe90",
        "FUN_00713050",
    ]
    assert report["target_count"] == 4
    assert all(row["class_membership_proven"] is False for row in report["targets"])
    scope = report["scope"]
    assert scope["address_adjacency_proves_class_membership"] is False
    assert scope["selected_function_writes_plus_0x388"] is False
    assert scope["retail_cadence_admitted"] is False


def test_selector_anchor_fingerprint_drift_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="anchor fingerprint drift"):
        SELECTOR.select(_functions(tmp_path, drift_anchor=True))


def test_plus_0x388_store_becomes_candidate_only(tmp_path):
    selection_path, selection = _selection(tmp_path)
    accesses_path = _access_report(
        tmp_path,
        selection,
        [
            _access(
                "0x0070f100",
                "FUN_0070f100",
                "0x0070f110",
                displacement=0x388,
                access="write",
            ),
            _access(
                "0x0070fe90",
                "FUN_0070fe90",
                "0x0070fe94",
                displacement=0x388,
                access="read",
                base="EAX",
            ),
            _access(
                "0x0070fae0",
                "FUN_0070fae0",
                "0x0070fb00",
                displacement=0x384,
                access="write",
            ),
        ],
    )

    report = ANALYZER.analyze(selection_path, accesses_path)

    assert report["format"] == "SHIFT.PhysicsManagerRateWriterWorklist/1"
    assert report["ready"] is True
    assert report["status"] == "writer-candidate-worklist-ready"
    assert report["writer_candidate_count"] == 1
    candidate = report["writer_candidates"][0]
    assert candidate["function"] == "0x0070f100"
    assert candidate["displacement"] == 0x388
    assert candidate["machine_store_candidate"] is True
    assert candidate["base_register_aliases_cPhysicsManager"] is False
    assert candidate["cPhysicsManager_plus_0x388_writer_proven"] is False
    assert candidate["stored_value_provenance_proven"] is False
    assert candidate["physical_units_proven"] is False
    assert report["scan_completeness"][
        "full_program_writer_surface_complete"
    ] is False
    adjudication = report["adjudication"]
    assert adjudication["any_cPhysicsManager_plus_0x388_writer_proven"] is False
    assert adjudication["plus_0x388_semantic_name_frequency"] is False
    assert adjudication["retail_cadence_admitted"] is False


def test_unparsed_or_pcode_blockers_preserve_candidates_but_mark_scan_incomplete(tmp_path):
    selection_path, selection = _selection(tmp_path)
    accesses_path = _access_report(
        tmp_path,
        selection,
        [
            _access(
                "0x0070fae0",
                "FUN_0070fae0",
                "0x0070fb20",
                displacement=0x388,
                access="read-write",
            )
        ],
        pcode_blockers=1,
        unparsed=2,
    )

    report = ANALYZER.analyze(selection_path, accesses_path)

    assert report["ready"] is True
    assert report["status"] == "writer-candidate-worklist-ready-with-scan-blockers"
    assert report["scan_completeness"][
        "selected_window_simple_register_relative_scan_complete"
    ] is False
    assert (
        "selected-window-register-relative-scan-has-unparsed-or-pcode-blockers"
        in report["blocking_reasons"]
    )


def test_read_only_plus_0x388_surface_does_not_create_writer(tmp_path):
    selection_path, selection = _selection(tmp_path)
    accesses_path = _access_report(
        tmp_path,
        selection,
        [
            _access(
                "0x00713050",
                "FUN_00713050",
                "0x00713084",
                displacement=0x388,
                access="read",
                base="EAX",
            )
        ],
    )

    report = ANALYZER.analyze(selection_path, accesses_path)
    assert report["ready"] is False
    assert report["status"] == "blocked-no-writer-candidate"
    assert report["writer_candidates"] == []


def test_candidate_outside_exact_selection_is_rejected(tmp_path):
    selection_path, selection = _selection(tmp_path)
    accesses_path = _access_report(
        tmp_path,
        selection,
        [
            _access(
                "0x00720000",
                "FUN_00720000",
                "0x00720010",
                displacement=0x388,
                access="write",
            )
        ],
    )
    with pytest.raises(ValueError, match="outside exact target selection"):
        ANALYZER.analyze(selection_path, accesses_path)


def test_runner_chains_selector_instruction_export_and_generic_access_inventory():
    source = RUNNER.read_text(encoding="utf-8")
    assert "select_s5_physics_manager_rate_writer_targets.py" in source
    assert "--names-out" in source
    assert "mapfile -t TARGETS" in source
    assert "run_shift_function_instructions.sh" in source
    assert "analyze_register_relative_accesses.py" in source
    assert "analyze_s5_physics_manager_rate_writer_candidates.py" in source
    assert "shift_d3d9_capture" not in source.lower()
    assert "wine" not in source.lower()
    assert "no game/runtime execution" in source.lower()
