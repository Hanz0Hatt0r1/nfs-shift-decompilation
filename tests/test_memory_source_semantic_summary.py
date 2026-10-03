import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "shift_live_dump" / "summarize_memory_source_semantics.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("summarize_memory_source_semantics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _static_summary():
    return {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": True,
        "release_byte_behavior": {
            "analysis_complete": True,
            "thunk_forwarded_to_release_backend": True,
            "release_backend_observed": True,
            "controls_conditional_branch": True,
            "bitwise_transformed": False,
        },
        "scope": {
            "release_byte_behavior_observed": True,
            "release_flag_role_proven": False,
        },
    }


def _allocation(rows):
    return {
        "format": "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1",
        "rows": rows,
        "scope": {"allocation_size_role_proven": bool(rows)},
    }


def _released(rows):
    return {
        "format": "SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1",
        "rows": rows,
        "scope": {"released_pointer_role_proven": bool(rows)},
    }


def test_summary_aggregates_only_proven_roles_and_keeps_dl_semantics_unassigned(tmp_path):
    module = _load_module()
    static_path = _write(tmp_path / "static.json", _static_summary())
    allocation_path = _write(
        tmp_path / "allocation.json",
        _allocation(
            [
                {
                    "wrapper": "FUN_00886900",
                    "caller": "FUN_00100000",
                    "occurrence": 1,
                    "allocation_size_source_argument_index": 0,
                    "allocation_size_source_argument_expression": "count * 4",
                    "allocation_size_role_proven": True,
                },
                {
                    "wrapper": "FUN_00886900",
                    "caller": "FUN_00100010",
                    "occurrence": 1,
                    "allocation_size_source_argument_index": 0,
                    "allocation_size_source_argument_expression": "bytes",
                    "allocation_size_role_proven": True,
                },
                {
                    "wrapper": "FUN_008868d0",
                    "caller": "FUN_00100020",
                    "occurrence": 1,
                    "allocation_size_source_argument_index": None,
                    "allocation_size_role_proven": False,
                },
            ]
        ),
    )
    released_path = _write(
        tmp_path / "released.json",
        _released(
            [
                {
                    "wrapper": "FUN_00886930",
                    "caller": "FUN_00200000",
                    "occurrence": 1,
                    "released_pointer_source_argument_index": 2,
                    "released_pointer_source_argument_expression": "ptr",
                    "released_pointer_role_proven": True,
                }
            ]
        ),
    )

    report = module.summarize_memory_source_semantics(
        static_path, allocation_path, released_path
    )

    assert report["format"] == "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"
    assert report["allocation_size_role_proven"] is True
    assert report["allocation_size_proven_callsite_count"] == 2
    assert report["released_pointer_role_proven"] is True
    assert report["released_pointer_proven_callsite_count"] == 1
    assert report["semantic_profiles_consistent"] is True

    profiles = {row["wrapper"]: row for row in report["wrapper_profiles"]}
    allocation = profiles["FUN_00886900"]["allocation_size"]
    assert allocation["source_argument_index_consistent"] is True
    assert allocation["source_argument_index"] == 0
    assert allocation["proven_callsite_count"] == 2
    assert profiles["FUN_00886900"]["proven_source_roles"] == ["allocation-size"]

    released = profiles["FUN_00886930"]["released_pointer"]
    assert released["source_argument_index"] == 2
    assert profiles["FUN_00886930"]["proven_source_roles"] == ["released-pointer"]

    assert report["release_byte_behavior"]["controls_conditional_branch"] is True
    assert report["release_byte_behavior"]["semantic_role_assigned"] is False
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False


def test_summary_fails_closed_on_conflicting_proven_source_indices(tmp_path):
    module = _load_module()
    static_path = _write(tmp_path / "static.json", _static_summary())
    allocation_path = _write(
        tmp_path / "allocation.json",
        _allocation(
            [
                {
                    "wrapper": "FUN_00886900",
                    "caller": "FUN_A",
                    "occurrence": 1,
                    "allocation_size_source_argument_index": 0,
                    "allocation_size_source_argument_expression": "a",
                    "allocation_size_role_proven": True,
                },
                {
                    "wrapper": "FUN_00886900",
                    "caller": "FUN_B",
                    "occurrence": 1,
                    "allocation_size_source_argument_index": 1,
                    "allocation_size_source_argument_expression": "b",
                    "allocation_size_role_proven": True,
                },
            ]
        ),
    )
    released_path = _write(tmp_path / "released.json", _released([]))

    report = module.summarize_memory_source_semantics(
        static_path, allocation_path, released_path
    )

    profile = report["wrapper_profiles"][0]
    assert profile["allocation_size"]["source_argument_index_consistent"] is False
    assert profile["allocation_size"]["source_argument_index"] is None
    assert profile["proven_source_roles"] == []
    assert report["semantic_profiles_consistent"] is False
    assert report["blockers"] == [
        "FUN_00886900:allocation_size_source_index_conflict"
    ]


def test_summary_rejects_wrong_input_format(tmp_path):
    module = _load_module()
    static_path = _write(tmp_path / "static.json", {"format": "wrong"})
    allocation_path = _write(tmp_path / "allocation.json", _allocation([]))
    released_path = _write(tmp_path / "released.json", _released([]))

    try:
        module.summarize_memory_source_semantics(
            static_path, allocation_path, released_path
        )
    except ValueError as exc:
        assert "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1" in str(exc)
    else:
        raise AssertionError("wrong static summary format was accepted")
