import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "summarize_memory_retail_static_evidence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("summarize_memory_retail_static_evidence", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _inputs(tmp_path: Path, *, complete=True):
    forwarding = tmp_path / "forwarding.json"
    backend = tmp_path / "backend.json"
    allocation = tmp_path / "allocation.json"
    free = tmp_path / "free.json"
    chain = tmp_path / "chain.json"
    release_byte = tmp_path / "release_byte.json"

    _write(
        forwarding,
        {
            "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
            "wrapper_count": 5,
            "confirmed_wrapper_forwarding_count": 5 if complete else 4,
            "all_wrapper_forwarding_confirmed": complete,
        },
    )
    _write(
        backend,
        {
            "format": "SHIFT-MEMORY-BACKEND-EVIDENCE/1",
            "allocation_backend_diagnostic_proven": complete,
            "free_backend_diagnostic_proven": complete,
            "release_thunk_to_free_diagnostic_path_proven": complete,
            "diagnostic_inventory": [{"kind": "pool-allocation-diagnostic"}],
        },
    )
    _write(
        allocation,
        {
            "format": "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1",
            "allocation_size_role_proven": complete,
            "allocation_size_entry_storage": "EDX:4" if complete else None,
        },
    )
    _write(
        free,
        {
            "format": "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1",
            "free_pointer_role_proven": complete,
            "free_pointer_entry_storage": "ECX:4" if complete else None,
        },
    )
    _write(
        chain,
        {
            "format": "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1",
            "release_pointer_to_wrapper_storage_proven": complete,
            "wrapper_paths": (
                [
                    {
                        "wrapper": "FUN_00886930",
                        "wrapper_input_storage": "Stack[0x4]:4",
                        "released_pointer_path_proven": True,
                    },
                    {
                        "wrapper": "FUN_00886950",
                        "wrapper_input_storage": "Stack[0x4]:4",
                        "released_pointer_path_proven": True,
                    },
                ]
                if complete
                else []
            ),
        },
    )
    _write(
        release_byte,
        {
            "format": "SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1",
            "analysis_complete": complete,
            "thunk_entry_dl_forwarded_to_release_backend": True,
            "release_backend_entry_dl_observed": True,
            "release_backend_entry_dl_controls_conditional_branch": True,
            "release_backend_entry_dl_bitwise_transformed": False,
            "scope": {"entry_dl_behavior_observed": True},
        },
    )
    return forwarding, backend, allocation, free, chain, release_byte


def _alternate_release(tmp_path: Path, *, proven=True):
    path = tmp_path / "alternate_release.json"
    _write(
        path,
        {
            "format": "SHIFT-MEMORY-RELEASE-ALTERNATE-BACKEND/1",
            "wrapper": "FUN_00886950",
            "alternate_backend": "0x0064f260",
            "proven_released_pointer_wrapper_storage": (
                "Stack[0x4]:4" if proven else None
            ),
            "alternate_backend_released_pointer_entry_storage": (
                "EDX:4" if proven else None
            ),
            "released_pointer_to_alternate_backend_storage_proven": proven,
            "blockers": [] if proven else ["alternate_backend_pointer_match_not_unique"],
        },
    )
    return path


def test_static_summary_reports_completed_retail_chain(tmp_path):
    module = _load_module()
    paths = _inputs(tmp_path)

    report = module.summarize_memory_retail_static_evidence(*paths)

    assert report["wrapper_forwarding"]["all_wrapper_forwarding_confirmed"] is True
    assert report["backend_diagnostics"]["allocation_backend_diagnostic_proven"] is True
    assert report["backend_diagnostics"]["free_backend_diagnostic_proven"] is True
    assert report["backend_diagnostics"]["release_thunk_to_free_diagnostic_path_proven"] is True
    assert report["proven_physical_roles"]["allocation_size"]["entry_storage"] == "EDX:4"
    assert report["proven_physical_roles"]["free_pointer_local"]["entry_storage"] == "ECX:4"
    assert report["proven_physical_roles"]["released_pointer_wrapper"]["wrapper_input_storage"] == [
        "Stack[0x4]:4"
    ]
    alternate = report["proven_physical_roles"]["alternate_release_backend_pointer"]
    assert alternate["proven"] is False
    assert alternate["entry_storage"] is None
    assert report["alternate_release_backend_evidence"] == {
        "present": False,
        "released_pointer_role_proven": False,
        "blockers": [],
    }
    assert report["release_byte_behavior"]["controls_conditional_branch"] is True
    assert report["static_evidence_chain_complete"] is True
    assert report["ready_for_source_semantic_join"] is True
    assert report["blockers"] == []
    assert report["scope"]["source_decompiler_output_required"] is False
    assert report["scope"]["alternate_release_backend_pointer_physical_role_proven"] is False
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False


def test_static_summary_promotes_optional_alternate_backend_pointer_role(tmp_path):
    module = _load_module()
    paths = _inputs(tmp_path)
    alternate_path = _alternate_release(tmp_path)

    report = module.summarize_memory_retail_static_evidence(
        *paths,
        alternate_path,
    )

    role = report["proven_physical_roles"]["alternate_release_backend_pointer"]
    assert role == {
        "proven": True,
        "function": "FUN_0064f260",
        "entry_storage": "EDX:4",
        "wrapper": "FUN_00886950",
        "wrapper_input_storage": "Stack[0x4]:4",
        "semantic_anchor": "cross-branch identity with diagnostic-proven released pointer",
    }
    assert report["alternate_release_backend_evidence"] == {
        "present": True,
        "released_pointer_role_proven": True,
        "blockers": [],
    }
    assert report["scope"]["alternate_release_backend_pointer_physical_role_proven"] is True
    assert report["scope"]["alternate_release_backend_function_semantics_proven"] is False
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["static_evidence_chain_complete"] is True
    assert report["blockers"] == []


def test_static_summary_keeps_optional_alternate_failure_separate(tmp_path):
    module = _load_module()
    paths = _inputs(tmp_path)
    alternate_path = _alternate_release(tmp_path, proven=False)

    report = module.summarize_memory_retail_static_evidence(
        *paths,
        alternate_path,
    )

    assert report["static_evidence_chain_complete"] is True
    assert report["blockers"] == []
    assert report["alternate_release_backend_evidence"]["released_pointer_role_proven"] is False
    assert report["alternate_release_backend_evidence"]["blockers"] == [
        "alternate_backend_pointer_match_not_unique"
    ]


def test_static_summary_lists_fail_closed_blockers(tmp_path):
    module = _load_module()
    paths = _inputs(tmp_path, complete=False)

    report = module.summarize_memory_retail_static_evidence(*paths)

    assert report["static_evidence_chain_complete"] is False
    assert report["ready_for_source_semantic_join"] is False
    assert "wrapper_forwarding_not_fully_proven" in report["blockers"]
    assert "allocation_backend_diagnostic_not_proven" in report["blockers"]
    assert "free_backend_diagnostic_not_proven" in report["blockers"]
    assert "release_thunk_to_free_diagnostic_path_not_proven" in report["blockers"]
    assert "allocation_size_backend_storage_not_proven" in report["blockers"]
    assert "free_pointer_diagnostic_storage_not_proven" in report["blockers"]
    assert "released_pointer_wrapper_storage_not_proven" in report["blockers"]
    assert "release_byte_behavior_incomplete" in report["blockers"]
    assert report["scope"]["release_flag_role_proven"] is False


def test_static_summary_rejects_wrong_input_format(tmp_path):
    module = _load_module()
    paths = list(_inputs(tmp_path))
    paths[0].write_text('{"format":"WRONG"}\n', encoding="utf-8")

    try:
        module.summarize_memory_retail_static_evidence(*paths)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-FORWARDING/1" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_static_summary_rejects_wrong_optional_alternate_format(tmp_path):
    module = _load_module()
    paths = _inputs(tmp_path)
    alternate = tmp_path / "alternate.json"
    _write(alternate, {"format": "WRONG"})

    try:
        module.summarize_memory_retail_static_evidence(*paths, alternate)
    except ValueError as exc:
        assert "SHIFT-MEMORY-RELEASE-ALTERNATE-BACKEND/1" in str(exc)
    else:
        raise AssertionError("expected ValueError")
