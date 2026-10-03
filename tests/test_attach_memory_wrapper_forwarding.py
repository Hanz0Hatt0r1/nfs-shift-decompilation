import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "attach_memory_wrapper_forwarding.py"
        spec = importlib.util.spec_from_file_location("attach_memory_wrapper_forwarding", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write(path: Path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _callsites():
    return {
        "format": "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1",
        "source": "SHIFT.exe.c",
        "source_sha256": "source-sha",
        "callsites": [
            {
                "caller": "FUN_00100000",
                "wrapper": "FUN_008868c0",
                "occurrence": 0,
                "arguments_parse_complete": True,
                "argument_count": 1,
                "arguments": [{"index": 0, "expression": "0xe4"}],
                "ghidra_direct_edge": True,
            }
        ],
    }


def _forwarding():
    return {
        "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
        "wrappers": [
            {
                "name": "FUN_008868c0",
                "input_storage": ["Stack[0x4]:4"],
                "forwarding_confirmed": True,
                "call_sites": [
                    {
                        "instruction": "0x008868c9",
                        "target": "0x006382b0",
                        "target_name": "FUN_006382b0",
                        "target_calling_convention": "__fastcall",
                        "arguments_resolved": True,
                        "incoming_state_uncertain": False,
                        "arguments": [
                            {
                                "storage": "ECX:4",
                                "source": "input:Stack[0x4]:4",
                                "source_kind": "input",
                                "resolved": True,
                            },
                            {
                                "storage": "EDX:4",
                                "source": "constant:0x4",
                                "source_kind": "constant",
                                "resolved": True,
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_attach_writes_join_and_updates_manifest_atomically(tmp_path):
    module = _load_module()
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    _write(pipeline / "memory_wrapper_callsites.json", _callsites())
    _write(
        pipeline / "pipeline_manifest.json",
        {
            "format": "SHIFT-CLASS-EVIDENCE-PIPELINE/1",
            "artifacts": {"memory_wrapper_callsites": "memory_wrapper_callsites.json"},
            "counts": {"registered_classes": 315},
            "scope": {
                "argument_roles_proven": False,
                "allocator_abi_proven": False,
                "release_abi_proven": False,
                "ownership_semantics_proven": False,
                "note": "base evidence boundary.",
            },
        },
    )
    forwarding = tmp_path / "forwarding.json"
    _write(forwarding, _forwarding())

    report = module.attach_memory_wrapper_forwarding(pipeline, forwarding)

    assert report["artifacts"]["memory_wrapper_argument_join"] == "memory_wrapper_argument_join.json"
    assert report["counts"]["memory_wrapper_argument_join_callsites"] == 1
    assert report["counts"]["memory_wrapper_forwarding_join_ready_callsites"] == 1
    assert report["counts"]["memory_wrapper_forwarding_ghidra_crosschecked_joins"] == 1
    assert report["counts"]["memory_wrapper_backend_arguments"] == 2
    assert report["counts"]["memory_wrapper_source_mapped_backend_arguments"] == 1
    assert report["counts"]["memory_wrapper_internal_backend_arguments"] == 1
    assert report["counts"]["memory_wrapper_unresolved_backend_arguments"] == 0
    assert report["scope"]["memory_wrapper_instruction_forwarding_used"] is True
    assert report["scope"]["memory_wrapper_argument_provenance_joined"] is True
    assert report["scope"]["argument_roles_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False
    assert report["scope"]["release_abi_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False

    join = json.loads((pipeline / "memory_wrapper_argument_join.json").read_text(encoding="utf-8"))
    assert join["format"] == "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1"
    backend = join["rows"][0]["backend_calls"][0]["arguments"]
    assert backend[0]["source_argument_expression"] == "0xe4"
    assert backend[1]["wrapper_internal_source"] is True

    saved = json.loads((pipeline / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert saved == report
    assert "mechanical value provenance" in saved["scope"]["note"]


def test_attach_requires_pipeline_callsite_artifact(tmp_path):
    module = _load_module()
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    _write(
        pipeline / "pipeline_manifest.json",
        {
            "format": "SHIFT-CLASS-EVIDENCE-PIPELINE/1",
            "artifacts": {},
            "counts": {},
            "scope": {},
        },
    )
    forwarding = tmp_path / "forwarding.json"
    _write(forwarding, _forwarding())

    try:
        module.attach_memory_wrapper_forwarding(pipeline, forwarding)
    except ValueError as exc:
        assert "memory_wrapper_callsites artifact missing" in str(exc)
    else:
        raise AssertionError("missing pipeline callsite artifact must fail")


def test_attach_rejects_wrong_forwarding_format(tmp_path):
    module = _load_module()
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    _write(pipeline / "memory_wrapper_callsites.json", _callsites())
    _write(
        pipeline / "pipeline_manifest.json",
        {
            "format": "SHIFT-CLASS-EVIDENCE-PIPELINE/1",
            "artifacts": {"memory_wrapper_callsites": "memory_wrapper_callsites.json"},
            "counts": {},
            "scope": {},
        },
    )
    forwarding = tmp_path / "forwarding.json"
    _write(forwarding, {"format": "wrong"})

    try:
        module.attach_memory_wrapper_forwarding(pipeline, forwarding)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-FORWARDING/1" in str(exc)
    else:
        raise AssertionError("wrong forwarding format must fail")
