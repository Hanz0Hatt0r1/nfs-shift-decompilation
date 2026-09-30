import pytest

from sgb_multimatrix import matrix_from_record, matrix_multiply
from sgb_object_render_handoff import (
    build_sgb_object_render_handoff_set,
)


def _record(index, *, parent, offset=(0.0, 0.0, 0.0)):
    return {
        "index": index,
        "offset_xyz": list(offset),
        "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
        "scale": 1.0,
        "parent": parent,
    }


def _object(matrix_number, resource):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "matrix_number": matrix_number,
        "resource_filename": {"text": resource},
    }


def _runtime(owner):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": "SUMM",
            "records": [{
                "index": 7,
                "offset": 100,
                "name": {"text": "wrapper"},
                "resource": {"text": ""},
                "object_payload": {
                    "decoded": True,
                    "report": owner,
                },
            }],
        }],
    }


def _consensus(root, *, owner_path=None, ready=True):
    owner_path = list(owner_path or [])
    return {
        "format": "SHIFT.SGBMultiMatrixRootConsensus/1",
        "ready": ready,
        "consensus": [
            {
                "wrapper": {
                    "chunk": "SUMM",
                    "source_record_index": 7,
                },
                "owner_path": owner_path,
                "status": "ready" if ready else "blocked",
                "ready": ready,
                "blocking_reasons": [],
                "authorizes_current_multimatrix_owner_root": ready,
                "authorizes_current_wrapper_root": (
                    ready and not owner_path
                ),
                "root_float32_hex": "00" * 64,
                "root_world_matrix": list(root),
                "support_resource_count": 2,
                "distinct_cumulative_local_count": 2,
                "witness_count": 2,
            }
        ],
    }


def test_ready_owner_root_recomputes_all_matrixnumber_children():
    records = [
        _record(0, parent=-1),
        _record(1, parent=0, offset=(1.0, 0.0, 0.0)),
        _record(2, parent=0, offset=(0.0, 2.0, 0.0)),
    ]
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
        "subobject_references": [
            {
                "index": 0,
                "decoded": True,
                "report": _object(1, "tracks/test/a.imb"),
            },
            {
                "index": 1,
                "decoded": True,
                "report": _object(2, "tracks/test/b.imb"),
            },
        ],
    }
    root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]

    report = build_sgb_object_render_handoff_set(
        _runtime(owner),
        root_consensus=_consensus(root),
    )

    assert report["ready"] is True
    assert report["numeric_world_matrix_ready_count"] == 2
    assert report["runtime_root_consensus_available_count"] == 1
    assert report["runtime_root_consensus_applied_object_count"] == 2

    by_path = {
        tuple(row["object_path"]): row["handoff"]
        for row in report["objects"]
    }
    assert by_path[(0,)]["transform"]["world_matrix"] == pytest.approx(
        matrix_multiply(matrix_from_record(records[1]), root)
    )
    assert by_path[(1,)]["transform"]["world_matrix"] == pytest.approx(
        matrix_multiply(matrix_from_record(records[2]), root)
    )
    for handoff in by_path.values():
        root_state = (
            handoff["transform"]["multimatrix_evaluation"][
                "root_transform_state"
            ]
        )
        assert root_state["current_root_source"] == (
            "phase596-runtime-root-consensus"
        )
        assert root_state["runtime_root_consensus"]["owner_path"] == []


def test_nested_owner_root_does_not_leak_to_wrapper_root_owner():
    top_records = [
        _record(0, parent=-1),
        _record(1, parent=0, offset=(9.0, 0.0, 0.0)),
    ]
    nested_records = [
        _record(0, parent=-1),
        _record(1, parent=0, offset=(0.0, 3.0, 0.0)),
    ]
    nested = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": nested_records,
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": _object(1, "tracks/test/nested.imb"),
        }],
    }
    wrapper_owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "HIERARCHY"},
        "matrix_number": -1,
        "matrix_records": top_records,
        "subobject_references": [
            {"index": 0, "decoded": True, "report": nested},
            {
                "index": 1,
                "decoded": True,
                "report": _object(1, "tracks/test/top.imb"),
            },
        ],
    }
    nested_root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        5.0, 6.0, 7.0, 1.0,
    ]

    report = build_sgb_object_render_handoff_set(
        _runtime(wrapper_owner),
        root_consensus=_consensus(
            nested_root,
            owner_path=[0],
        ),
    )

    by_path = {
        tuple(row["object_path"]): row["handoff"]
        for row in report["objects"]
    }
    nested_handoff = by_path[(0, 0)]
    top_handoff = by_path[(1,)]

    assert nested_handoff["transform"]["world_matrix_ready"] is True
    assert nested_handoff["transform"]["world_matrix"] == pytest.approx(
        matrix_multiply(
            matrix_from_record(nested_records[1]),
            nested_root,
        )
    )
    assert top_handoff["transform"]["world_matrix_ready"] is False
    assert top_handoff["transform"]["world_matrix"] is None
    assert report["runtime_root_consensus_applied_object_count"] == 1


def test_blocked_consensus_fails_set_application_closed():
    records = [
        _record(0, parent=-1),
        _record(1, parent=0, offset=(1.0, 0.0, 0.0)),
    ]
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": _object(1, "tracks/test/a.imb"),
        }],
    }
    root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]

    report = build_sgb_object_render_handoff_set(
        _runtime(owner),
        root_consensus=_consensus(root, ready=False),
    )

    assert report["ready"] is False
    assert (
        "object-render:root-consensus-not-ready"
        in report["blocking_reasons"]
    )
    assert report["runtime_root_consensus_available_count"] == 0
    assert report["runtime_root_consensus_applied_object_count"] == 0


def test_wrong_consensus_format_is_rejected():
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": [_record(0, parent=-1)],
        "subobject_references": [],
    }
    with pytest.raises(ValueError, match="SGBMultiMatrixRootConsensus"):
        build_sgb_object_render_handoff_set(
            _runtime(owner),
            root_consensus={"format": "wrong"},
        )
