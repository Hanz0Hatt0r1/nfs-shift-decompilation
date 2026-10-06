from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_render_root_delta_initvehicle_input.py"
SPEC = importlib.util.spec_from_file_location("initvehicle_delta_input", TOOL)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _relation() -> dict:
    return {
        "format": mod.RELATION_FORMAT,
        "version": 1,
        "status": "outer-vehicle-bmw-vhf-fixed-affine-relation-proven",
        "ready": True,
        "semantic_authority": "Process 1",
        "relation": {
            "kind": "fixed_affine",
            "source_frame": "outer_vehicle_root",
            "target_frame": "canonical_bmw_vhf_hierarchy_root",
            "delta_local_source": list(mod.DELTA_FIELDS),
            "delta_producer": mod.DELTA_NAME,
            "delta_lifetime": "Vehicle::InitVehicle/setup state; not runtime pose",
            "relation_matrix_numeric_ready": False,
        },
        "proof": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "static_lifecycle_provenance": {
            mod.INIT_NAME: {
                "address": mod.INIT,
                "size": mod.INIT_SIZE,
                "calling_convention": mod.INIT_CC,
                "mnemonic_sha256": mod.INIT_MNEMONIC_SHA256,
                "source_label": mod.INIT_SOURCE_LABEL,
                "source_file": mod.INIT_SOURCE_FILE,
                "direct_restart_caller": "FUN_0074ddc3",
                "restart_callsite": "0x0074de12",
            },
            mod.DELTA_NAME: {
                "address": mod.DELTA,
                "size": mod.DELTA_SIZE,
                "calling_convention": mod.DELTA_CC,
                "mnemonic_sha256": mod.DELTA_MNEMONIC_SHA256,
                "unique_direct_caller": mod.INIT_NAME,
                "callsite": mod.DELTA_CALLSITE,
            },
        },
    }


def _source(*, target_call: str | None = None, extra_pre: str = "") -> str:
    call = target_call or (
        "  FUN_00795d60(this,param_1,local_2390,"
        "*(void **)((int)this + 0x1d00),param_1);"
    )
    return "\n".join([
        "void unrelated(void) { }",
        "void FUN_00798df0(void *this,char param_1)",
        "{",
        "  float local_2390[16];",
        "  FUN_00783df0(this,local_2390);",
        "  local_2390[2] = 4.0;",
        extra_pre,
        call,
        "  FUN_007911f0(local_2390);",
        "}",
        "",
    ])


def _fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source: str | None = None,
    extra_callers: list[dict] | None = None,
) -> tuple[Path, Path, Path]:
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_json(ghidra / "binary.json", {
        "program_name": mod.PROGRAM,
        "executable_md5": mod.PE_MD5,
    })
    _write_jsonl(ghidra / "functions.jsonl", [
        {
            "address": mod.INIT,
            "name": mod.INIT_NAME,
            "size": mod.INIT_SIZE,
            "calling_convention": mod.INIT_CC,
            "mnemonic_sha256": mod.INIT_MNEMONIC_SHA256,
            "signature": "undefined FUN_00798df0(void * this, char param_1)",
            "thunk": False,
            "external": False,
        },
        {
            "address": mod.DELTA,
            "name": mod.DELTA_NAME,
            "size": mod.DELTA_SIZE,
            "calling_convention": mod.DELTA_CC,
            "mnemonic_sha256": mod.DELTA_MNEMONIC_SHA256,
            "signature": "undefined FUN_00795d60(void * param_1, char param_2, float * param_3, void * param_4, char param_5)",
            "thunk": False,
            "external": False,
        },
    ])
    calls = [
        {
            "from_function": mod.INIT,
            "from_name": mod.INIT_NAME,
            "instruction": "0x00799076",
            "to": "0x00783df0",
            "to_name": "FUN_00783df0",
            "indirect": False,
        },
        {
            "from_function": mod.INIT,
            "from_name": mod.INIT_NAME,
            "instruction": mod.DELTA_CALLSITE,
            "to": mod.DELTA,
            "to_name": mod.DELTA_NAME,
            "indirect": False,
        },
        {
            "from_function": mod.INIT,
            "from_name": mod.INIT_NAME,
            "instruction": "0x007990f5",
            "to": "0x007911f0",
            "to_name": "FUN_007911f0",
            "indirect": False,
        },
    ]
    calls.extend(extra_callers or [])
    _write_jsonl(ghidra / "callgraph.jsonl", calls)
    _write_jsonl(ghidra / "strings_xrefs.jsonl", [
        {
            "address": "0x00b0b640",
            "value": mod.INIT_SOURCE_FILE,
            "xrefs": ["0x00798ea5", "0x00798f08"],
            "functions": [mod.INIT],
        },
        {
            "address": "0x00b0b660",
            "value": mod.INIT_SOURCE_LABEL,
            "xrefs": ["0x00798e9b", "0x00798efe"],
            "functions": [mod.INIT],
        },
    ])

    relation = tmp_path / "relation.json"
    _write_json(relation, _relation())
    source_path = tmp_path / "SHIFT.exe.c"
    source_text = source if source is not None else _source()
    source_path.write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(
        mod,
        "SOURCE_SHA256",
        hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    )
    return ghidra, source_path, relation


def test_positive_frontier_binds_exact_call_and_bounds_producers(tmp_path, monkeypatch):
    ghidra, source, relation = _fixture(tmp_path, monkeypatch)
    report = mod.analyze(ghidra, source, relation)

    assert report["format"] == mod.FORMAT
    assert report["ready"] is True
    assert report["binding"]["callsite"] == mod.DELTA_CALLSITE
    assert report["binding"]["callee_param3_source_local"] == mod.DELTA_LOCAL
    assert report["binding"]["source_to_callsite_binding_ready"] is True
    assert report["binding"]["stack_argument_numeric_value_proven"] is False

    frontier = report["source_reference_frontier"]
    assert frontier["pre_call_reference_count"] == 3
    assert frontier["post_call_reference_count"] == 1
    assert frontier["producer_candidate_count"] == 2
    assert frontier["direct_fun_target_worklist"] == ["0x00783df0"]
    assert frontier["lexical_source_order_is_all_path_value_proof"] is False
    assert frontier["pointer_argument_implies_callee_write"] is False

    kinds = [row["kind"] for row in frontier["references"]]
    assert kinds == [
        "local-declaration",
        "direct-function-call-reference",
        "direct-local-write",
        "target-delta-call",
        "direct-function-call-reference",
    ]
    call_candidate = next(
        row for row in frontier["producer_candidates"]
        if row["kind"] == "direct-function-call-reference"
    )
    assert call_candidate["direct_callgraph_joins"] == [{
        "target": "0x00783df0",
        "matching_pre_delta_direct_calls": [{
            "instruction": "0x00799076",
            "to": "0x00783df0",
            "to_name": "FUN_00783df0",
        }],
        "unique_pre_delta_direct_call": True,
    }]

    handoff = report["handoff"]
    assert handoff["initvehicle_delta_param3_source_local_binding_ready"] is True
    assert handoff["initvehicle_delta_input_reference_frontier_ready"] is True
    assert handoff["initvehicle_delta_input_producer_worklist_ready"] is True
    assert handoff["selected_BMW_render_root_delta_numeric_ready"] is False
    assert handoff["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert handoff["BODY0_bind_frame_proof_ready"] is False


def test_rejects_second_direct_caller_of_delta(tmp_path, monkeypatch):
    extra = [{
        "from_function": "0x00123456",
        "from_name": "FUN_00123456",
        "instruction": "0x00123480",
        "to": mod.DELTA,
        "to_name": mod.DELTA_NAME,
        "indirect": False,
    }]
    ghidra, source, relation = _fixture(
        tmp_path, monkeypatch, extra_callers=extra
    )
    with pytest.raises(ValueError, match="expected one direct caller"):
        mod.analyze(ghidra, source, relation)


def test_rejects_source_sha_drift(tmp_path, monkeypatch):
    ghidra, source, relation = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "SOURCE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="source SHA-256"):
        mod.analyze(ghidra, source, relation)


def test_rejects_delta_call_param3_source_drift(tmp_path, monkeypatch):
    changed = _source(target_call=(
        "  FUN_00795d60(this,param_1,local_2380,"
        "*(void **)((int)this + 0x1d00),param_1);"
    ))
    ghidra, source, relation = _fixture(
        tmp_path, monkeypatch, source=changed
    )
    with pytest.raises(ValueError, match="expected one source delta call reference|delta call statement drift"):
        mod.analyze(ghidra, source, relation)


def test_unclassified_precall_reference_stays_explicit_blocker(tmp_path, monkeypatch):
    changed = _source(extra_pre="  if (local_2390[0] > 0.0) { param_1 = 1; }")
    ghidra, source, relation = _fixture(
        tmp_path, monkeypatch, source=changed
    )
    report = mod.analyze(ghidra, source, relation)

    assert report["ready"] is True
    assert report["source_reference_frontier"][
        "unclassified_pre_call_reference_count"
    ] == 1
    assert report["blockers"][0]["id"] == (
        "initvehicle-local2390-unclassified-precall-reference"
    )
    assert report["handoff"]["selected_BMW_render_root_delta_numeric_ready"] is False


def test_relation_numeric_preclaim_is_rejected(tmp_path, monkeypatch):
    ghidra, source, relation_path = _fixture(tmp_path, monkeypatch)
    relation = _relation()
    relation["relation"]["relation_matrix_numeric_ready"] = True
    _write_json(relation_path, relation)

    with pytest.raises(ValueError, match="already has numeric matrix"):
        mod.analyze(ghidra, source, relation_path)


def test_source_label_must_belong_to_initvehicle(tmp_path, monkeypatch):
    ghidra, source, relation = _fixture(tmp_path, monkeypatch)
    rows = [
        {
            "address": "0x00b0b640",
            "value": mod.INIT_SOURCE_FILE,
            "xrefs": ["0x00798ea5"],
            "functions": ["0x00111111"],
        },
        {
            "address": "0x00b0b660",
            "value": mod.INIT_SOURCE_LABEL,
            "xrefs": ["0x00798e9b"],
            "functions": [mod.INIT],
        },
    ]
    _write_jsonl(ghidra / "strings_xrefs.jsonl", rows)
    with pytest.raises(ValueError, match="not xref-owned"):
        mod.analyze(ghidra, source, relation)


def test_scope_never_promotes_lexical_or_callgraph_context_to_value_proof(tmp_path, monkeypatch):
    ghidra, source, relation = _fixture(tmp_path, monkeypatch)
    report = mod.analyze(ghidra, source, relation)

    scope = report["scope"]
    assert scope["callgraph_adjacency_used_as_value_proof"] is False
    assert scope["source_lexical_order_used_as_all_path_proof"] is False
    assert scope["numeric_delta_invented"] is False
    assert scope["runtime_capture_used"] is False
    assert scope["original_game_executed"] is False
