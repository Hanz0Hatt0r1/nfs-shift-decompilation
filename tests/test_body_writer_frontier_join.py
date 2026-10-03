import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "join_body_writer_candidates_to_frontier.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("join_body_writer_candidates_to_frontier", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _candidate(function, kind="accumulator-to-motion", base="ECX"):
    return {
        "kind": kind,
        "function": function,
        "function_name": f"FUN_{function[2:]}",
        "base_register": base,
        "read_offsets": [0x48],
        "write_offsets": [0x78],
    }


def _bridge(candidates):
    return {
        "format": "SHIFT.BodyWriterBridgeCandidates/1",
        "candidates": candidates,
    }


def _frontier():
    return {
        "format": "SHIFT.GhidraProvenCallgraphFrontier/1",
        "selected_subsystems": ["physics", "vehicle"],
        "subsystems": {
            "physics": {
                "proven_slice_addresses": ["0x007b4110"],
            },
            "vehicle": {
                "proven_slice_addresses": ["0x00770e80"],
            },
        },
        "frontier_candidates": [
            {
                "address": "0x0076d100",
                "name": "FUN_0076d100",
                "min_depth": 1,
                "connected_subsystems": ["vehicle"],
                "adjacent_proven_slice_addresses": ["0x00770e80"],
                "ordered_slice_calls": [
                    {
                        "from_function": "0x0076d100",
                        "to": "0x00770e80",
                        "instruction": "0x0076d200",
                    }
                ],
                "slice_callers": [],
                "multi_anchor_caller_candidate": False,
                "direct_outgoing_count": 3,
                "direct_incoming_count": 2,
            },
            {
                "address": "0x00700000",
                "name": "FUN_00700000",
                "min_depth": 2,
                "connected_subsystems": ["physics", "vehicle"],
                "adjacent_proven_slice_addresses": [],
                "ordered_slice_calls": [],
                "slice_callers": [],
                "multi_anchor_caller_candidate": True,
                "direct_outgoing_count": 7,
                "direct_incoming_count": 1,
            },
        ],
        "indirect_blockers": [
            {
                "from_function": "0x0076d100",
                "instruction": "0x0076d250",
                "status": "unresolved-indirect-call-target",
            },
            {
                "from_function": "0x007b4110",
                "instruction": "0x007b4200",
                "status": "unresolved-indirect-call-target",
            },
        ],
    }


def test_joins_proven_slice_root_without_promoting_writer():
    module = _load_module()
    report = module.join_body_writer_candidates_to_frontier(
        _bridge([_candidate("0x007b4110")]),
        _frontier(),
    )
    row = report["candidates"][0]
    assert row["frontier_relation"] == "proven-slice-root"
    assert row["min_depth"] == 0
    assert row["connected_subsystems"] == ["physics"]
    assert row["proven_slice_root"] is True
    assert row["frontier_candidate"] is False
    assert row["indirect_call_sites"][0]["instruction"] == "0x007b4200"
    assert row["body_writer_proven"] is False


def test_joins_direct_frontier_context_and_edges():
    module = _load_module()
    report = module.join_body_writer_candidates_to_frontier(
        _bridge([_candidate("0x0076d100")]),
        _frontier(),
    )
    row = report["candidates"][0]
    assert row["frontier_relation"] == "callgraph-frontier"
    assert row["min_depth"] == 1
    assert row["connected_subsystems"] == ["vehicle"]
    assert row["adjacent_proven_slice_addresses"] == ["0x00770e80"]
    assert row["direct_outgoing_count"] == 3
    assert row["indirect_call_sites"][0]["instruction"] == "0x0076d250"
    assert report["direct_frontier_candidate_count"] == 1


def test_preserves_multi_anchor_candidate_without_calling_it_integrator():
    module = _load_module()
    report = module.join_body_writer_candidates_to_frontier(
        _bridge([_candidate("0x00700000", kind="motion-to-pose", base="ESI")]),
        _frontier(),
    )
    row = report["candidates"][0]
    assert row["min_depth"] == 2
    assert row["multi_anchor_caller_candidate"] is True
    assert report["multi_anchor_bridge_candidate_count"] == 1
    assert report["scope"]["multi_anchor_caller_is_integrator_proof"] is False


def test_candidate_outside_selected_frontier_remains_visible():
    module = _load_module()
    report = module.join_body_writer_candidates_to_frontier(
        _bridge([_candidate("0x00999999")]),
        _frontier(),
    )
    row = report["candidates"][0]
    assert row["frontier_relation"] == "outside-selected-frontier"
    assert row["min_depth"] is None
    assert row["connected_subsystems"] == []
    assert report["outside_frontier_candidate_count"] == 1


def test_duplicate_frontier_address_is_reported():
    module = _load_module()
    frontier = _frontier()
    frontier["frontier_candidates"].append(dict(frontier["frontier_candidates"][0]))
    report = module.join_body_writer_candidates_to_frontier(
        _bridge([_candidate("0x0076d100")]),
        frontier,
    )
    assert report["duplicate_frontier_address_count"] == 1
    assert report["duplicate_frontier_addresses"] == ["0x0076d100"]


def test_rejects_wrong_formats():
    module = _load_module()
    try:
        module.join_body_writer_candidates_to_frontier(
            {"format": "WRONG", "candidates": []},
            _frontier(),
        )
    except ValueError as exc:
        assert "SHIFT.BodyWriterBridgeCandidates/1" in str(exc)
    else:
        raise AssertionError("wrong bridge format must fail closed")

    try:
        module.join_body_writer_candidates_to_frontier(
            _bridge([]),
            {"format": "WRONG"},
        )
    except ValueError as exc:
        assert "SHIFT.GhidraProvenCallgraphFrontier/1" in str(exc)
    else:
        raise AssertionError("wrong frontier format must fail closed")
