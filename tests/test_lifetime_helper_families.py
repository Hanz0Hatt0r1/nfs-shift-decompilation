import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    path = tool_dir / "build_lifetime_helper_families.py"
    spec = importlib.util.spec_from_file_location(
        "build_lifetime_helper_families", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_groups_recurrent_helper_pairs_and_attaches_ghidra_context(tmp_path):
    module = _load_module()
    pair = tmp_path / "pairs.json"
    _write_json(
        pair,
        {
            "format": "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1",
            "paired_lifetime_shape_count": 4,
            "classes": [
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": True,
                    "unambiguous_preinitializer_helper": "FUN_00886900",
                    "unambiguous_release_helper": "FUN_00886930",
                    "helper_literal_argument_sets": [[0x38, 4]],
                },
                {
                    "class_name": "B",
                    "descriptor": 2,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": True,
                    "unambiguous_preinitializer_helper": "FUN_00886900",
                    "unambiguous_release_helper": "FUN_00886930",
                    "helper_literal_argument_sets": [[0x2C, 4]],
                },
                {
                    "class_name": "C",
                    "descriptor": 3,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": True,
                    "unambiguous_preinitializer_helper": "FUN_00900000",
                    "unambiguous_release_helper": "FUN_00900030",
                    "helper_literal_argument_sets": [[0x18]],
                },
                {
                    "class_name": "Ambiguous",
                    "descriptor": 4,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": False,
                    "unambiguous_preinitializer_helper": None,
                    "unambiguous_release_helper": "FUN_00886930",
                    "preinitializer_helpers": ["FUN_00886900", "FUN_00900000"],
                    "release_helpers": ["FUN_00886930"],
                    "helper_literal_argument_sets": [],
                },
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    functions = [
        {
            "address": "0x00886900",
            "name": "FUN_00886900",
            "signature": "void * FUN_00886900(uint,int)",
            "calling_convention": "__cdecl",
            "parameters": [{"name": "size"}, {"name": "kind"}],
            "mnemonic_sha256": "create-fingerprint",
        },
        {
            "address": "0x00886930",
            "name": "FUN_00886930",
            "signature": "void FUN_00886930(void *)",
            "calling_convention": "__cdecl",
            "parameters": [{"name": "ptr"}],
            "mnemonic_sha256": "release-fingerprint",
        },
        {
            "address": "0x00900000",
            "name": "FUN_00900000",
            "signature": "void * FUN_00900000(int)",
            "calling_convention": "__cdecl",
            "parameters": [],
            "mnemonic_sha256": "other-create",
        },
        {
            "address": "0x00900030",
            "name": "FUN_00900030",
            "signature": "void FUN_00900030(void *)",
            "calling_convention": "__cdecl",
            "parameters": [],
            "mnemonic_sha256": "other-release",
        },
    ]
    with (ghidra / "functions.jsonl").open("w", encoding="utf-8") as handle:
        for row in functions:
            handle.write(json.dumps(row) + "\n")
    with (ghidra / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for caller, instruction, callee in (
            ("0x00886900", "0x00886911", "0x00638020"),
            ("0x00886900", "0x0088691f", "0x006382b0"),
            ("0x00886930", "0x0088693b", "0x0064f4c0"),
        ):
            handle.write(
                json.dumps(
                    {
                        "from_function": caller,
                        "instruction": instruction,
                        "to": callee,
                        "to_name": "callee",
                        "indirect": False,
                    }
                )
                + "\n"
            )

    report = module.build_helper_families(pair, ghidra)
    assert report["format"] == "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1"
    assert report["paired_class_count"] == 4
    assert report["unambiguous_helper_pair_class_count"] == 3
    assert report["ambiguous_helper_pair_class_count"] == 1
    assert report["helper_family_count"] == 2
    assert report["recurrent_helper_pair_count"] == 1
    assert report["crosschecked_recurrent_helper_family_candidate_count"] == 1

    family = report["families"][0]
    assert family["create_helper"] == "FUN_00886900"
    assert family["release_helper"] == "FUN_00886930"
    assert family["class_count"] == 2
    assert family["classes"] == ["A", "B"]
    assert family["descriptors"] == [1, 2]
    assert family["helper_literal_argument_sets"] == [[0x2C, 4], [0x38, 4]]
    assert family["recurrent_helper_pair"] is True
    assert family["all_classes_ghidra_paired"] is True
    assert family["ghidra_helpers_present"] is True
    assert family["crosschecked_recurrent_helper_family_candidate"] is True
    assert family["create_helper_context"]["mnemonic_sha256"] == "create-fingerprint"
    assert [
        row["target"] for row in family["create_helper_context"]["outgoing_direct_calls"]
    ] == ["0x00638020", "0x006382b0"]
    assert family["release_helper_context"]["mnemonic_sha256"] == "release-fingerprint"
    assert [
        row["target"] for row in family["release_helper_context"]["outgoing_direct_calls"]
    ] == ["0x0064f4c0"]
    assert report["ambiguous_classes"][0]["class_name"] == "Ambiguous"
    assert report["scope"]["allocator_semantics_proven"] is False


def test_without_ghidra_keeps_recurrence_but_not_crosschecked_candidate(tmp_path):
    module = _load_module()
    pair = tmp_path / "pairs.json"
    _write_json(
        pair,
        {
            "format": "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1",
            "paired_lifetime_shape_count": 2,
            "classes": [
                {
                    "class_name": "A",
                    "descriptor": 1,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": True,
                    "unambiguous_preinitializer_helper": "FUN_00886900",
                    "unambiguous_release_helper": "FUN_00886930",
                    "helper_literal_argument_sets": [[0x10]],
                },
                {
                    "class_name": "B",
                    "descriptor": 2,
                    "paired_lifetime_shape": True,
                    "ghidra_paired_lifetime_shape": True,
                    "unambiguous_preinitializer_helper": "FUN_00886900",
                    "unambiguous_release_helper": "FUN_00886930",
                    "helper_literal_argument_sets": [[0x20]],
                },
            ],
        },
    )

    report = module.build_helper_families(pair)
    assert report["recurrent_helper_pair_count"] == 1
    assert report["crosschecked_recurrent_helper_family_candidate_count"] == 0
    family = report["families"][0]
    assert family["recurrent_helper_pair"] is True
    assert family["ghidra_helpers_present"] is False
    assert family["create_helper_context"] is None
    assert family["release_helper_context"] is None
