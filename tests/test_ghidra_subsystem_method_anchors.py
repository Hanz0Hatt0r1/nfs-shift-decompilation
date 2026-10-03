import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "join_method_anchors_to_subsystems.py"
        spec = importlib.util.spec_from_file_location(
            "join_method_anchors_to_subsystems", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_jsonl(path: Path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _string(address: int, value: str, function: str):
    return {
        "address": f"0x{address:08x}",
        "value": value,
        "length": len(value) + 1,
        "xrefs": [f"0x{address + 0x100:08x}"],
        "functions": [function],
    }


def test_promotes_only_unique_namespace_and_slice_intersection(tmp_path):
    module = _load_module()
    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": "abc",
                "language_id": "x86:LE:32:default",
                "image_base": "0x00400000",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"program": "SHIFT.exe", "counts": {"functions": 6}}),
        encoding="utf-8",
    )

    functions = [
        "0x00854e70",  # renderer: existing promoted alias + exact method anchor
        "0x00750080",  # physics: existing promoted alias + exact method anchor
        "0x00710870",  # physics namespace only, outside established slice
        "0x0074ddc3",  # existing physics alias but multiple method anchors
        "0x0068ba9e",  # scene graph: existing promoted alias + exact method anchor
        "0x00660000",  # unique generic MWL::Core method, intentionally unclassified
    ]
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            {
                "address": address,
                "name": "FUN_" + address[2:],
                "calling_convention": "__cdecl",
                "size": 32,
                "mnemonic_sha256": address[2:] * 8,
            }
            for address in functions
        ],
    )

    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x00854e70",
                "instruction": "0x00854e80",
                "to": "0x00830f80",
                "indirect": False,
            },
            {
                "from_function": "0x00854e70",
                "instruction": "0x00854e90",
                "to": "0x00853c40",
                "indirect": False,
            },
        ],
    )

    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [
            _string(
                0x00B00000,
                "MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers",
                "0x00854e70",
            ),
            _string(
                0x00B00100,
                "MWL::Core::LoadCollisionStream",
                "0x00750080",
            ),
            _string(
                0x00B00200,
                "MWL::Core::cPhysicsManager::GetAssetDatabase",
                "0x00710870",
            ),
            _string(
                0x00B00300,
                "MWL::Core::PhysicsParticipant::Restart",
                "0x0074ddc3",
            ),
            _string(
                0x00B00400,
                "MWL::Core::PhysicsParticipant::Tick",
                "0x0074ddc3",
            ),
            _string(
                0x00B00500,
                "MWL::GraphicsEngine::CSceneGraph::AddUpdate",
                "0x0068ba9e",
            ),
            _string(
                0x00B00600,
                "MWL::Core::GenericManager::Update",
                "0x00660000",
            ),
        ],
    )

    report = module.join_method_anchors_to_subsystems(tmp_path)
    assert report["format"] == "SHIFT.GhidraSubsystemMethodAnchors/1"

    by_address = {row["address"]: row for row in report["unique_candidates"]}

    renderer = by_address["0x00854e70"]
    assert renderer["namespace_subsystem"] == "renderer"
    assert renderer["slice_memberships"] == ["renderer"]
    assert renderer["promoted_subsystem"] == "renderer"
    assert renderer["promoted"] is True

    physics = by_address["0x00750080"]
    assert physics["namespace_subsystem"] == "physics"
    assert physics["slice_memberships"] == ["physics"]
    assert physics["promoted"] is True

    namespace_only = by_address["0x00710870"]
    assert namespace_only["namespace_subsystem"] == "physics"
    assert namespace_only["slice_memberships"] == []
    assert namespace_only["promoted"] is False
    assert namespace_only["status"] == "namespace-only-method-name-candidate"

    scene = by_address["0x0068ba9e"]
    assert scene["namespace_subsystem"] == "scene_graph"
    assert scene["slice_memberships"] == ["scene_graph"]
    assert scene["promoted"] is True

    generic = by_address["0x00660000"]
    assert generic["namespace_subsystem"] is None
    assert generic["slice_memberships"] == []
    assert generic["promoted"] is False
    assert generic["status"] == "unclassified-method-name-candidate"

    ambiguous = next(
        row
        for row in report["ambiguous_functions"]
        if row["address"] == "0x0074ddc3"
    )
    assert ambiguous["promoted"] is False
    assert ambiguous["namespace_subsystems"] == ["physics"]
    assert ambiguous["slice_memberships"] == ["physics"]
    assert ambiguous["method_anchors"] == [
        "MWL::Core::PhysicsParticipant::Restart",
        "MWL::Core::PhysicsParticipant::Tick",
    ]

    assert report["promoted_method_name_candidate_count"] == 3
    assert report["namespace_only_candidate_count"] == 1
    assert report["ambiguous_method_anchor_function_count"] == 1
    assert report["scope"]["automatic_function_renaming_performed"] is False
    assert report["scope"]["method_behavior_proven"] is False


def test_namespace_rules_do_not_assign_broad_core_names():
    module = _load_module()
    assert module._namespace_subsystem("MWL::Core::GenericManager::Update") is None
    assert module._namespace_subsystem("MWL::Core::cPhysicsManager::GetAssetDatabase") == "physics"
    assert module._namespace_subsystem("MWL::Renderer::WinRenderer::Draw") == "renderer"
    assert module._namespace_subsystem("MWL::GraphicsEngine::CSceneGraph::AddUpdate") == "scene_graph"
