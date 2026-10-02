import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "extract_deleting_wrapper_evidence.py"
        spec = importlib.util.spec_from_file_location(
            "extract_deleting_wrapper_evidence", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_detects_conditional_release_wrapper_and_ghidra_edges(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        r'''
void FUN_00102100(void *this)
{
    *(void ***)this = &PTR_FUN_00402200;
    FUN_00101100(this);
}

void FUN_00102200(void *this,uint param_2)
{
    FUN_00102100(this);
    if ((param_2 & 1) != 0) {
        FUN_00886930(this);
    }
}

void FUN_00102300(void *this)
{
    FUN_00102100(this);
    FUN_00886930(this);
}

void FUN_00102400(void *this,uint flags)
{
    FUN_00886930(this);
    if ((flags & 1) != 0) {
        FUN_00102100(this);
    }
}
''',
        encoding="utf-8",
    )
    sha = hashlib.sha256(source.read_bytes()).hexdigest()

    lifecycle = tmp_path / "lifecycle.json"
    _write_json(
        lifecycle,
        {
            "format": "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1",
            "source_sha256": sha,
            "targets": [
                {
                    "class_name": "Child",
                    "descriptor": 2,
                    "teardown_transition_candidates": [
                        {"function": "FUN_00102100"}
                    ],
                }
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    with (ghidra / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for caller, callee in (
            ("0x00102200", "0x00102100"),
            ("0x00102200", "0x00886930"),
            ("0x00102300", "0x00102100"),
            ("0x00102300", "0x00886930"),
            ("0x00102400", "0x00102100"),
            ("0x00102400", "0x00886930"),
        ):
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

    report = module.extract_deleting_wrappers(source, lifecycle, ghidra)
    assert report["format"] == "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1"
    assert report["wrapper_candidate_count"] == 3
    assert report["deleting_wrapper_shape_count"] == 1
    assert report["ghidra_confirmed_shape_count"] == 1

    rows = {row["wrapper_function"]: row for row in report["wrappers"]}
    strong = rows["FUN_00102200"]
    assert strong["teardown_before_release"] is True
    assert strong["bit0_delete_guard"] is True
    assert strong["deleting_wrapper_shape"] is True
    assert strong["ghidra_teardown_edge"] is True
    assert strong["ghidra_release_edge"] is True

    unconditional = rows["FUN_00102300"]
    assert unconditional["teardown_before_release"] is True
    assert unconditional["bit0_delete_guard"] is False
    assert unconditional["deleting_wrapper_shape"] is False

    reversed_order = rows["FUN_00102400"]
    assert reversed_order["teardown_before_release"] is False
    assert reversed_order["bit0_delete_guard"] is True
    assert reversed_order["deleting_wrapper_shape"] is False
    assert report["scope"]["deleting_destructor_semantics_proven"] is False


def test_rejects_wrong_source_and_supports_custom_release_helper(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        "void FUN_00102100(void) {}\n"
        "void FUN_00102200(uint param_2) { FUN_00102100(); "
        "if ((param_2 & 1) != 0) FUN_00999999(); }\n",
        encoding="utf-8",
    )
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    lifecycle = tmp_path / "lifecycle.json"
    _write_json(
        lifecycle,
        {
            "format": "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1",
            "source_sha256": sha,
            "targets": [
                {
                    "class_name": "Custom",
                    "descriptor": 4,
                    "teardown_transition_candidates": [
                        {"function": "FUN_00102100"}
                    ],
                }
            ],
        },
    )

    report = module.extract_deleting_wrappers(
        source,
        lifecycle,
        release_helpers=("FUN_00999999",),
    )
    assert report["deleting_wrapper_shape_count"] == 1
    assert report["wrappers"][0]["release_helper"] == "FUN_00999999"

    broken = json.loads(lifecycle.read_text(encoding="utf-8"))
    broken["source_sha256"] = "0" * 64
    _write_json(lifecycle, broken)
    try:
        module.extract_deleting_wrappers(source, lifecycle)
    except ValueError as exc:
        assert "source identity mismatch" in str(exc)
    else:
        raise AssertionError("expected source identity mismatch")
