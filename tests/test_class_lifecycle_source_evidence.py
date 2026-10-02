import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "extract_class_lifecycle_source_evidence.py"
        spec = importlib.util.spec_from_file_location(
            "extract_class_lifecycle_source_evidence", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_extracts_vtable_base_and_field_evidence(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        r'''
void * FUN_00101000(void *this)
{
    *(void ***)this = &PTR_FUN_00402100;
    *(int *)((int)this + 0x08) = 7;
    return this;
}

void * FUN_00102000(void *this)
{
    FUN_00101000(this);
    *(void ***)this = &PTR_FUN_00402200;
    *(int *)((int)this + 0x10) = 0;
    *(int *)((int)this + 0x14) = 1;
    return this;
}

void FUN_00101100(void *this)
{
    *(void ***)this = &PTR_FUN_00402100;
}

void FUN_00102100(void *this)
{
    *(void ***)this = &PTR_FUN_00402200;
    FUN_00101100(this);
}

void FUN_00103000(void)
{
    FUN_00102000((void *)0);
}

void FUN_00104000(void *this)
{
    if (this != 0) {
        FUN_00102100(this);
    }
}

void FUN_00105000(void *this)
{
    /* A mere reference is not a vtable write. */
    consume(&PTR_FUN_00402200);
}
''',
        encoding="utf-8",
    )

    manifest = tmp_path / "manifest.json"
    _write_json(
        manifest,
        {
            "format": "SHIFT-CLASS-MANIFEST/1",
            "source_sha256": "src",
            "exe_sha256": "exe",
            "classes": [
                {
                    "name": "Base",
                    "descriptor": 1,
                    "parent_class": None,
                    "ancestry": [],
                    "unique_vtable": 0x00402100,
                },
                {
                    "name": "Child",
                    "descriptor": 2,
                    "parent_class": "Base",
                    "ancestry": ["Base"],
                    "unique_vtable": 0x00402200,
                },
            ],
        },
    )

    scorecard = tmp_path / "scorecard.json"
    _write_json(
        scorecard,
        {
            "format": "SHIFT-CLASS-EVIDENCE-SCORECARD/1",
            "source_sha256": "src",
            "exe_sha256": "exe",
            "rows": [
                {
                    "class_name": "Child",
                    "descriptor": 2,
                    "evidence_tier": "lifecycle-investigation-ready",
                    "unambiguous_initializer": "FUN_00102000",
                }
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    edges = [
        ("0x00102000", "0x00101000"),
        ("0x00102100", "0x00101100"),
        ("0x00103000", "0x00102000"),
        ("0x00104000", "0x00102100"),
    ]
    with (ghidra / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for caller, callee in edges:
            handle.write(
                json.dumps(
                    {
                        "from_function": caller,
                        "to": callee,
                        "indirect": False,
                    }
                )
                + "\n"
            )

    report = module.extract_lifecycle_evidence(
        source, manifest, scorecard, ghidra
    )
    assert report["format"] == "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"
    assert report["target_count"] == 1
    assert report["complete_target_count"] == 1
    assert report["teardown_transition_candidate_count"] == 1

    row = report["targets"][0]
    assert row["class_name"] == "Child"
    assert row["nearest_ancestor_with_unique_vtable"] == "Base"
    assert row["initializer_writes_own_vtable"] is True
    assert row["own_vtable_writer_functions"] == ["FUN_00102000", "FUN_00102100"]
    assert [item["target"] for item in row["base_initializer_candidates"]] == [
        "FUN_00101000"
    ]
    assert row["base_initializer_candidates"][0]["ghidra_direct_call"] is True
    assert [item["offset"] for item in row["literal_field_assignments"]] == [
        0x10,
        0x14,
    ]
    assert row["initializer_callers"] == [
        {"function": "FUN_00103000", "ghidra_direct_call": True}
    ]
    teardown = row["teardown_transition_candidates"][0]
    assert teardown["function"] == "FUN_00102100"
    assert teardown["ancestor_transition_calls"] == [
        {"target": "FUN_00101100", "ghidra_direct_call": True}
    ]
    assert "FUN_00105000" not in row["own_vtable_writer_functions"]
    assert report["scope"]["destructor_semantics_proven"] is False


def test_preserves_missing_initializer_and_source_identity_guard(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("void FUN_00100000(void) { return; }\n", encoding="utf-8")

    manifest = tmp_path / "manifest.json"
    _write_json(
        manifest,
        {
            "format": "SHIFT-CLASS-MANIFEST/1",
            "source_sha256": "same",
            "exe_sha256": "exe",
            "classes": [
                {
                    "name": "Missing",
                    "descriptor": 3,
                    "ancestry": [],
                    "unique_vtable": 0x00402300,
                }
            ],
        },
    )
    scorecard = tmp_path / "scorecard.json"
    _write_json(
        scorecard,
        {
            "format": "SHIFT-CLASS-EVIDENCE-SCORECARD/1",
            "source_sha256": "same",
            "exe_sha256": "exe",
            "rows": [
                {
                    "class_name": "Missing",
                    "descriptor": 3,
                    "evidence_tier": "lifecycle-investigation-ready",
                    "unambiguous_initializer": "FUN_00109999",
                }
            ],
        },
    )

    report = module.extract_lifecycle_evidence(source, manifest, scorecard)
    row = report["targets"][0]
    assert row["complete"] is False
    assert "initializer_body" in row["missing"]
    assert "initializer_own_vtable_write" in row["missing"]

    mismatched = json.loads(scorecard.read_text(encoding="utf-8"))
    mismatched["source_sha256"] = "different"
    _write_json(scorecard, mismatched)
    try:
        module.extract_lifecycle_evidence(source, manifest, scorecard)
    except ValueError as exc:
        assert "source identity mismatch" in str(exc)
    else:
        raise AssertionError("expected source identity mismatch")
