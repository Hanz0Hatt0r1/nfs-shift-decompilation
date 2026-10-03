import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "summarize_memory_wrapper_argument_patterns.py"
        spec = importlib.util.spec_from_file_location("summarize_memory_wrapper_argument_patterns", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _arg(index, expression, exact=None):
    return {
        "index": index,
        "expression": expression,
        "integer_literals": [] if exact is None else [exact],
        "is_exact_integer_literal": exact is not None,
        "exact_integer_value": exact,
        "is_simple_identifier": expression.isidentifier(),
    }


def _backend_arg(storage, source, *, index=None, mapped=False, internal=False):
    return {
        "backend_storage": storage,
        "forwarding_source": source,
        "forwarding_source_kind": "input" if mapped else "constant",
        "forwarding_resolved": mapped or internal,
        "wrapper_input_storages": [],
        "source_argument_indices": [] if index is None else [index],
        "source_argument_index": index,
        "source_argument_expression": None,
        "source_argument_mapped": mapped,
        "wrapper_internal_source": internal,
    }


def _row(caller, literal, second_expression, *, crosschecked=True):
    return {
        "caller": caller,
        "wrapper": "FUN_00886900",
        "occurrence": 0,
        "arguments_parse_complete": True,
        "argument_count": 3,
        "arguments": [
            _arg(0, hex(literal), exact=literal),
            _arg(1, second_expression),
            _arg(2, "flags"),
        ],
        "ghidra_direct_edge": crosschecked,
        "forwarding_record_present": True,
        "forwarding_join_ready": True,
        "ghidra_crosschecked_join": crosschecked,
        "backend_calls": [
            {
                "instruction": "0x00886911",
                "target": "0x00638020",
                "target_name": "FUN_00638020",
                "target_calling_convention": "__fastcall",
                "arguments": [
                    _backend_arg("ECX:4", "input:Stack[0x4]:4", index=0, mapped=True),
                    _backend_arg("EDX:4", "input:Stack[0x8]:4", index=1, mapped=True),
                    _backend_arg("Stack[0x4]:4", "input:Stack[0xc]:4", index=2, mapped=True),
                ],
            },
            {
                "instruction": "0x0088691f",
                "target": "0x006382b0",
                "target_name": "FUN_006382b0",
                "target_calling_convention": "__fastcall",
                "arguments": [
                    _backend_arg("ECX:4", "input:Stack[0x4]:4", index=0, mapped=True),
                    _backend_arg("EDX:4", "constant:0x4", internal=True),
                ],
            },
        ],
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _pattern(report, target, storage):
    return next(
        row
        for row in report["patterns"]
        if row["backend_target"] == target and row["backend_storage"] == storage
    )


def test_summarizes_recurrent_stable_source_and_internal_patterns(tmp_path):
    module = _load_module()
    path = tmp_path / "join.json"
    _write(
        path,
        {
            "format": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1",
            "rows": [
                _row("FUN_00100000", 0x38, "pool_a"),
                _row("FUN_00110000", 0x40, "pool_b"),
            ],
        },
    )

    report = module.summarize_memory_wrapper_argument_patterns(path)
    assert report["format"] == "SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1"
    assert report["pattern_count"] == 5
    assert report["recurrent_pattern_count"] == 5
    assert report["crosschecked_stable_pattern_count"] == 5
    assert report["mixed_or_unresolved_pattern_count"] == 0

    ecx = _pattern(report, "0x00638020", "ECX:4")
    assert ecx["mapping_kind"] == "stable-source-argument"
    assert ecx["stable_source_argument_index"] == 0
    assert ecx["occurrence_count"] == 2
    assert ecx["caller_count"] == 2
    assert ecx["fully_ghidra_crosschecked"] is True
    assert ecx["exact_source_integer_literal_histogram"] == [
        {"value": 0x38, "occurrence_count": 1},
        {"value": 0x40, "occurrence_count": 1},
    ]

    internal = _pattern(report, "0x006382b0", "EDX:4")
    assert internal["mapping_kind"] == "stable-wrapper-internal"
    assert internal["stable_wrapper_internal_source"] == "constant:0x4"
    assert internal["wrapper_internal_source_histogram"] == [
        {"forwarding_source": "constant:0x4", "occurrence_count": 2}
    ]
    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["allocation_size_role_proven"] is False


def test_non_crosschecked_occurrence_keeps_stability_but_not_crosschecked_pattern(tmp_path):
    module = _load_module()
    path = tmp_path / "join.json"
    _write(
        path,
        {
            "format": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1",
            "rows": [
                _row("FUN_00100000", 0x38, "pool_a", crosschecked=True),
                _row("FUN_00110000", 0x40, "pool_b", crosschecked=False),
            ],
        },
    )

    report = module.summarize_memory_wrapper_argument_patterns(path)
    ecx = _pattern(report, "0x00638020", "ECX:4")
    assert ecx["mapping_kind"] == "stable-source-argument"
    assert ecx["recurrent_pattern"] is True
    assert ecx["fully_ghidra_crosschecked"] is False
    assert ecx["crosschecked_stable_pattern"] is False
    assert report["crosschecked_stable_pattern_count"] == 0


def test_mixed_and_unresolved_sources_are_not_promoted_stable(tmp_path):
    module = _load_module()
    first = _row("FUN_00100000", 0x38, "pool_a")
    second = _row("FUN_00110000", 0x40, "pool_b")
    # Make the same backend/storage receive a different source argument index.
    second["backend_calls"][0]["arguments"][0] = _backend_arg(
        "ECX:4", "input:Stack[0x8]:4", index=1, mapped=True
    )
    # Make another backend/storage unresolved on one occurrence.
    second["backend_calls"][0]["arguments"][2] = _backend_arg(
        "Stack[0x4]:4", "unresolved"
    )
    path = tmp_path / "join.json"
    _write(
        path,
        {"format": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1", "rows": [first, second]},
    )

    report = module.summarize_memory_wrapper_argument_patterns(path)
    mixed = _pattern(report, "0x00638020", "ECX:4")
    assert mixed["mapping_kind"] == "mixed"
    assert mixed["stable_source_argument_index"] is None
    assert mixed["source_argument_index_histogram"] == [
        {"source_argument_index": 0, "occurrence_count": 1},
        {"source_argument_index": 1, "occurrence_count": 1},
    ]

    unresolved = _pattern(report, "0x00638020", "Stack[0x4]:4")
    assert unresolved["mapping_kind"] == "mixed"
    assert unresolved["unresolved_occurrence_count"] == 1
    assert unresolved["crosschecked_stable_pattern"] is False
    assert report["mixed_or_unresolved_pattern_count"] >= 2


def test_rejects_wrong_input_format(tmp_path):
    module = _load_module()
    path = tmp_path / "join.json"
    _write(path, {"format": "wrong", "rows": []})

    try:
        module.summarize_memory_wrapper_argument_patterns(path)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1" in str(exc)
    else:
        raise AssertionError("wrong input format must fail")
