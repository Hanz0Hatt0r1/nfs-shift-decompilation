import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_bmw_body0_bind_initialization_frontier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_bmw_body0_bind_initialization_frontier", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _function(address, *, external=False, thunk=False):
    return {
        "address": address,
        "name": "FUN_" + address[2:],
        "calling_convention": "__thiscall",
        "signature": f"void FUN_{address[2:]}(void)",
        "size": 64,
        "external": external,
        "thunk": thunk,
    }


def _call(source, instruction, target, *, indirect=False):
    return {
        "from_function": source,
        "from_name": "FUN_" + source[2:],
        "instruction": instruction,
        "to": target,
        "to_name": "FUN_" + target[2:],
        "indirect": indirect,
    }


def _fixture(tmp_path):
    module = _load_module()
    setup = "0x007b3000"
    unrelated = "0x00712000"
    functions = [
        _function(module.SDF_LOADER),
        _function(module.BODY_BUILDER),
        _function(module.POSE_WRITER_CANDIDATE),
        _function(setup),
        _function(unrelated),
    ]
    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": module.PE_MD5,
                "language_id": "x86:LE:32:default",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(tmp_path / "functions.jsonl", functions)
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call(module.SDF_LOADER, "0x007b6910", module.BODY_BUILDER),
            _call(module.BODY_BUILDER, "0x007b3690", setup),
            _call(setup, "0x007b3030", module.POSE_WRITER_CANDIDATE),
            _call(unrelated, "0x00712030", module.POSE_WRITER_CANDIDATE),
        ],
    )
    return module, setup, unrelated


def test_builds_finite_bind_initialization_worklist(tmp_path):
    module, setup, unrelated = _fixture(tmp_path)

    report = module.build_bmw_body0_bind_initialization_frontier(tmp_path)

    assert report["format"] == "SHIFT.BMWBody0BindInitializationFrontier/1"
    assert report["source"]["executable_md5"] == module.PE_MD5
    assert report["directed_reachability"]["SDF_loader_to_BODY_builder"]["reachable"] is True
    assert report["directed_reachability"]["SDF_loader_to_BODY_builder"]["depth"] == 1
    assert report["directed_reachability"]["BODY_builder_to_pose_writer_candidate"]["depth"] == 2
    assert report["directed_reachability"]["SDF_loader_to_pose_writer_candidate"]["depth"] == 3

    callers = report["pose_writer_candidate"]["direct_callers"]
    assert report["pose_writer_candidate"]["direct_caller_count"] == 2
    assert callers[0]["caller"] == setup
    assert callers[0]["candidate_class"] == "builder-reachable-pose-writer-caller"
    assert callers[0]["from_BODY_builder"]["depth"] == 1
    assert callers[0]["bind_initializer_semantics_proven"] is False
    assert callers[0]["BODY0_pointer_proven"] is False
    assert callers[1]["caller"] == unrelated
    assert callers[1]["candidate_class"] == "unjoined-direct-pose-writer-caller"

    targets = report["targeted_proof_worklist"]["function_targets"]
    assert targets == sorted(
        {
            module.SDF_LOADER,
            module.BODY_BUILDER,
            module.POSE_WRITER_CANDIDATE,
            setup,
            unrelated,
        },
        key=lambda value: int(value, 0),
    )
    assert report["targeted_proof_worklist"]["callsites"] == sorted(
        ["0x00712030", "0x007b3030", "0x007b3690", "0x007b6910"],
        key=lambda value: int(value, 0),
    )
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert blocker_ids == {
        "BODY0-bind-origin-basis-value-provenance-unproven",
        "pose-writer-candidate-bind-role-unproven",
    }
    assert report["scope"]["callgraph_reachability_is_semantic_proof"] is False
    assert report["scope"]["pose_writer_candidate_promoted_to_initializer"] is False
    assert report["scope"]["BODY0_bind_matrix_proven"] is False


def test_indirect_edges_do_not_create_bind_initialization_path(tmp_path):
    module, setup, unrelated = _fixture(tmp_path)
    rows = [
        _call(module.SDF_LOADER, "0x007b6910", module.BODY_BUILDER),
        _call(module.BODY_BUILDER, "0x007b3690", setup, indirect=True),
        _call(setup, "0x007b3030", module.POSE_WRITER_CANDIDATE),
        _call(unrelated, "0x00712030", module.POSE_WRITER_CANDIDATE),
    ]
    _write_jsonl(tmp_path / "callgraph.jsonl", rows)

    report = module.build_bmw_body0_bind_initialization_frontier(tmp_path)
    assert report["directed_reachability"]["BODY_builder_to_pose_writer_candidate"]["reachable"] is False
    callers = report["pose_writer_candidate"]["direct_callers"]
    assert all(row["candidate_class"] == "unjoined-direct-pose-writer-caller" for row in callers)


def test_max_depth_is_fail_closed_for_longer_path(tmp_path):
    module, *_ = _fixture(tmp_path)

    report = module.build_bmw_body0_bind_initialization_frontier(tmp_path, max_depth=1)

    assert report["directed_reachability"]["SDF_loader_to_BODY_builder"]["reachable"] is True
    assert report["directed_reachability"]["BODY_builder_to_pose_writer_candidate"]["reachable"] is False
    assert report["directed_reachability"]["SDF_loader_to_pose_writer_candidate"]["reachable"] is False


def test_empty_pose_writer_caller_set_stays_blocked(tmp_path):
    module, *_ = _fixture(tmp_path)
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [_call(module.SDF_LOADER, "0x007b6910", module.BODY_BUILDER)],
    )

    report = module.build_bmw_body0_bind_initialization_frontier(tmp_path)

    assert report["pose_writer_candidate"]["direct_caller_count"] == 0
    assert report["pose_writer_candidate"]["direct_callers"] == []
    assert "pose-writer-direct-caller-set-empty" in {
        row["id"] for row in report["blockers"]
    }
    assert report["targeted_proof_worklist"]["function_targets"] == sorted(
        [module.SDF_LOADER, module.BODY_BUILDER, module.POSE_WRITER_CANDIDATE],
        key=lambda value: int(value, 0),
    )


def test_rejects_wrong_retail_binary(tmp_path):
    module, *_ = _fixture(tmp_path)
    value = json.loads((tmp_path / "binary.json").read_text(encoding="utf-8"))
    value["executable_md5"] = "0" * 32
    (tmp_path / "binary.json").write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected executable MD5"):
        module.build_bmw_body0_bind_initialization_frontier(tmp_path)


def test_rejects_missing_required_anchor(tmp_path):
    module, *_ = _fixture(tmp_path)
    rows = [
        row
        for row in module._read_jsonl(tmp_path / "functions.jsonl")
        if row["address"] != module.POSE_WRITER_CANDIDATE
    ]
    _write_jsonl(tmp_path / "functions.jsonl", rows)

    with pytest.raises(ValueError, match="required function"):
        module.build_bmw_body0_bind_initialization_frontier(tmp_path)


def test_invalid_depth_is_rejected(tmp_path):
    module, *_ = _fixture(tmp_path)
    with pytest.raises(ValueError, match="max_depth"):
        module.build_bmw_body0_bind_initialization_frontier(tmp_path, max_depth=0)
