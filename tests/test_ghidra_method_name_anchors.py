import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "discover_method_name_anchors.py"
    )
    spec = importlib.util.spec_from_file_location("discover_method_name_anchors", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _function(address, name):
    return {
        "address": address,
        "name": name,
        "calling_convention": "__fastcall",
        "size": 32,
        "mnemonic_sha256": address,
    }


def _string(address, value, functions):
    return {
        "address": address,
        "value": value,
        "xrefs": [address],
        "functions": functions,
    }


def test_discovers_unique_and_ambiguous_method_string_anchors(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    root.mkdir()
    _write_jsonl(
        root / "functions.jsonl",
        [
            _function("0x00710870", "FUN_00710870"),
            _function("0x0079cd90", "FUN_0079cd90"),
            _function("0x0079db50", "FUN_0079db50"),
            _function("0x00854e70", "FUN_00854e70"),
        ],
    )
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            _string(
                "0x00b044c0",
                "MWL::Core::cPhysicsManager::GetAssetDatabase",
                ["0x00710870"],
            ),
            _string(
                "0x00b10000",
                "MWL::Core::PhysicsAllocator::malloc",
                ["0x0079cd90"],
            ),
            _string(
                "0x00b20000",
                "MWL::PhysicsEvent_Impact::SetObjectType",
                ["0x0079db50"],
            ),
            _string(
                "0x00b20020",
                "MWL::PhysicsEvent_Impact::SetObjectID",
                ["0x0079db50"],
            ),
            _string(
                "0x00b30000",
                "MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers",
                ["0x00854e70"],
            ),
            # Not a method-name anchor.
            _string("0x00b40000", "Physics Manager", ["0x00710870"]),
            _string("0x00b40020", ".?AVPhysicsThing@MWL@@", []),
            _string("0x00b40040", "MWL::Core::bad method", ["0x00710870"]),
        ],
    )

    report = module.discover_method_name_anchors(root)

    assert report["format"] == "SHIFT.GhidraMethodNameAnchors/1"
    assert report["function_inventory_count"] == 4
    assert report["method_string_anchor_count"] == 5
    assert report["single_function_method_string_anchor_count"] == 5
    assert report["functions_with_method_anchors"] == 4
    assert report["unique_method_name_candidate_count"] == 3
    assert report["ambiguous_method_anchor_function_count"] == 1

    rows = {row["address"]: row for row in report["functions"]}
    assert rows["0x00710870"]["unique_method_name_candidate"] == (
        "MWL::Core::cPhysicsManager::GetAssetDatabase"
    )
    assert rows["0x0079cd90"]["unique_method_name_candidate"] == (
        "MWL::Core::PhysicsAllocator::malloc"
    )
    assert rows["0x00854e70"]["unique_method_name_candidate"] == (
        "MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers"
    )
    impact = rows["0x0079db50"]
    assert impact["unique_method_name_candidate"] is None
    assert impact["status"] == "ambiguous-method-name-anchors"
    assert impact["method_anchors"] == [
        "MWL::PhysicsEvent_Impact::SetObjectID",
        "MWL::PhysicsEvent_Impact::SetObjectType",
    ]
    assert report["scope"]["unique_string_anchor_is_automatic_rename"] is False
    assert report["scope"]["ambiguous_functions_promoted"] is False


def test_shared_string_and_unknown_function_do_not_create_unique_candidates(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    root.mkdir()
    _write_jsonl(
        root / "functions.jsonl",
        [
            _function("0x00100000", "FUN_00100000"),
            _function("0x00100010", "FUN_00100010"),
        ],
    )
    _write_jsonl(
        root / "strings_xrefs.jsonl",
        [
            _string(
                "0x00b50000",
                "MWL::Core::Shared::Method",
                ["0x00100000", "0x00100010"],
            ),
            _string(
                "0x00b50020",
                "MWL::Core::Missing::Method",
                ["0x00999999"],
            ),
        ],
    )

    report = module.discover_method_name_anchors(root)
    assert report["method_string_anchor_count"] == 2
    assert report["single_function_method_string_anchor_count"] == 0
    assert report["shared_or_unresolved_method_string_anchor_count"] == 2
    assert report["functions_with_method_anchors"] == 0
    assert report["unique_method_name_candidate_count"] == 0
    assert report["unresolved_function_reference_count"] == 1
    assert report["unresolved_function_references"] == ["0x00999999"]


def test_requires_direct_ghidra_datasets(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    root.mkdir()
    _write_jsonl(root / "functions.jsonl", [])

    try:
        module.discover_method_name_anchors(root)
    except FileNotFoundError as exc:
        assert "strings_xrefs.jsonl" in str(exc)
    else:
        raise AssertionError("missing string xrefs must fail")
