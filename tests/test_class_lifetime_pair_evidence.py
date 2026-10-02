import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "build_class_lifetime_pair_evidence.py"
        spec = importlib.util.spec_from_file_location(
            "build_class_lifetime_pair_evidence", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_pairs_strong_create_and_delete_shapes_by_descriptor(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("/* synthetic */\n", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()

    create = tmp_path / "create.json"
    _write_json(
        create,
        {
            "format": "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "links": [
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "factory_function": "FUN_00100000",
                    "initializer_candidate": "FUN_00110000",
                    "immediate_preinitializer_helper": "FUN_00886900",
                    "helper_literal_arguments": [0x38, 4],
                    "create_wrapper_shape": True,
                    "ghidra_factory_to_helper": True,
                    "ghidra_factory_to_initializer": True,
                },
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "factory_function": "FUN_00100010",
                    "initializer_candidate": "FUN_00110000",
                    "immediate_preinitializer_helper": "FUN_00886900",
                    "helper_literal_arguments": [0x38],
                    "create_wrapper_shape": True,
                    "ghidra_factory_to_helper": True,
                    "ghidra_factory_to_initializer": True,
                },
                {
                    "class_name": "B",
                    "descriptor": 2,
                    "factory_function": "FUN_00200000",
                    "initializer_candidate": "FUN_00210000",
                    "immediate_preinitializer_helper": "FUN_00886900",
                    "helper_literal_arguments": [0x20],
                    "create_wrapper_shape": True,
                    "ghidra_factory_to_helper": True,
                    "ghidra_factory_to_initializer": True,
                },
                {
                    "class_name": "Weak",
                    "descriptor": 4,
                    "create_wrapper_shape": False,
                },
            ],
        },
    )

    deleting = tmp_path / "delete.json"
    _write_json(
        deleting,
        {
            "format": "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "source_sha256": sha,
            "wrappers": [
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "wrapper_function": "FUN_00120000",
                    "teardown_transition_function": "FUN_00121000",
                    "release_helper": "FUN_00886930",
                    "deleting_wrapper_shape": True,
                    "ghidra_teardown_edge": True,
                    "ghidra_release_edge": True,
                },
                {
                    "class_name": "C",
                    "descriptor": 3,
                    "wrapper_function": "FUN_00320000",
                    "teardown_transition_function": "FUN_00321000",
                    "release_helper": "FUN_00886930",
                    "deleting_wrapper_shape": True,
                    "ghidra_teardown_edge": False,
                    "ghidra_release_edge": True,
                },
            ],
        },
    )

    lifecycle = tmp_path / "lifecycle.json"
    _write_json(
        lifecycle,
        {
            "format": "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1",
            "source": str(source),
            "source_sha256": sha,
            "targets": [
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "nearest_ancestor_with_unique_vtable": "Base",
                    "own_vtable": 0x00402200,
                    "ancestor_vtable": 0x00402100,
                },
                {"class_name": "B", "descriptor": 2},
                {"class_name": "C", "descriptor": 3},
            ],
        },
    )

    report = module.build_lifetime_pairs(create, deleting, lifecycle)
    assert report["format"] == "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"
    assert report["class_count"] == 3
    assert report["paired_lifetime_shape_count"] == 1
    assert report["ghidra_paired_lifetime_shape_count"] == 1
    assert report["unambiguous_helper_pair_count"] == 1
    assert report["identity"]["current_source_matches"] is True

    rows = {row["class_name"]: row for row in report["classes"]}
    a = rows["A"]
    assert a["paired_lifetime_shape"] is True
    assert a["ghidra_paired_lifetime_shape"] is True
    assert a["create_shape_count"] == 2
    assert a["delete_shape_count"] == 1
    assert a["unambiguous_preinitializer_helper"] == "FUN_00886900"
    assert a["unambiguous_release_helper"] == "FUN_00886930"
    assert a["helper_literal_argument_sets"] == [[0x38], [0x38, 4]]
    assert a["initializer_candidates"] == ["FUN_00110000"]
    assert a["teardown_transition_functions"] == ["FUN_00121000"]
    assert a["nearest_ancestor_with_unique_vtable"] == "Base"
    assert a["own_vtable"] == 0x00402200
    assert a["lifetime_evidence_blockers"] == []

    b = rows["B"]
    assert b["paired_lifetime_shape"] is False
    assert b["lifetime_evidence_blockers"] == ["no_deleting_wrapper_shape"]

    c = rows["C"]
    assert c["paired_lifetime_shape"] is False
    assert c["lifetime_evidence_blockers"] == ["no_create_wrapper_shape"]
    assert report["scope"]["constructor_semantics_proven"] is False


def test_rejects_source_identity_mismatch(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("x\n", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()

    create = tmp_path / "create.json"
    deleting = tmp_path / "delete.json"
    lifecycle = tmp_path / "lifecycle.json"
    _write_json(
        create,
        {
            "format": "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "links": [],
        },
    )
    _write_json(
        deleting,
        {
            "format": "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1",
            "source": str(source),
            "source_sha256": sha,
            "wrappers": [],
        },
    )
    _write_json(
        lifecycle,
        {
            "format": "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1",
            "source": str(source),
            "source_sha256": "0" * 64,
            "targets": [],
        },
    )

    try:
        module.build_lifetime_pairs(create, deleting, lifecycle)
    except ValueError as exc:
        assert "source SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("expected source SHA-256 mismatch")
