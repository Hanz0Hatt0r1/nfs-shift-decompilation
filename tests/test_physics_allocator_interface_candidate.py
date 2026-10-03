import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_physics_allocator_interface_candidate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_physics_allocator_interface_candidate", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _boundary(confirmed=True):
    return {
        "format": "SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1",
        "physics_allocator_boundary_confirmed": confirmed,
        "members": [
            {
                "role": "malloc-method-anchor",
                "address": "0x0079cd90",
                "member_confirmed": True,
            },
            {
                "role": "free-method-anchor",
                "address": "0x0079ce30",
                "member_confirmed": True,
            },
        ],
    }


def _table(address="0x00b0bb50"):
    return {
        "address": address,
        "block": ".rdata",
        "slot_count": 6,
        "slots": [
            {"slot": 0, "target": "0x0079cd90", "name": "FUN_0079cd90"},
            {"slot": 1, "target": "0x008cb240", "name": "FUN_008cb240"},
            {"slot": 2, "target": "0x0079d130", "name": "FUN_0079d130"},
            {"slot": 3, "target": "0x0079ce30", "name": "FUN_0079ce30"},
            {"slot": 4, "target": "0x008f3df0", "name": "GetHashSize"},
            {"slot": 5, "target": "0x0079db20", "name": "FUN_0079db20"},
        ],
        "function_xrefs": [],
    }


def _write_vtables(root, tables, status="heuristic-candidates"):
    root.mkdir()
    _write(
        root / "vtables.json",
        {
            "format": "SHIFT.GhidraVtableCandidates/1",
            "status": status,
            "vtables": tables,
        },
    )


def test_unique_shared_candidate_inherits_only_malloc_free_semantics(tmp_path):
    module = _load_module()
    boundary_path = tmp_path / "boundary.json"
    _write(boundary_path, _boundary())
    root = tmp_path / "ghidra"
    _write_vtables(root, [_table()])

    report = module.build_physics_allocator_interface_candidate(boundary_path, root)

    assert report["format"] == "SHIFT-PHYSICS-ALLOCATOR-INTERFACE-CANDIDATE/1"
    assert report["boundary_confirmed"] is True
    assert report["shared_vtable_candidate_count"] == 1
    assert report["unique_shared_vtable_candidate"] is True
    assert report["physics_allocator_interface_candidate"] is True
    candidate = report["candidate"]
    assert candidate["address"] == "0x00b0bb50"
    assert candidate["malloc_slots"] == [0]
    assert candidate["free_slots"] == [3]
    assert candidate["unknown_slot_count"] == 4
    assert candidate["slots"][0]["semantic_role"] == "PhysicsAllocator::malloc"
    assert candidate["slots"][3]["semantic_role"] == "PhysicsAllocator::free"
    assert candidate["slots"][1]["semantic_role"] is None
    assert candidate["slots"][4]["ghidra_name"] == "GetHashSize"
    assert candidate["slots"][4]["unknown_member"] is True
    assert report["scope"]["generic_vtable_inventory_is_heuristic"] is True
    assert report["scope"]["unknown_slot_semantics_proven"] is False
    assert report["scope"]["class_identity_proven_by_vtable"] is False


def test_multiple_shared_tables_stay_ambiguous(tmp_path):
    module = _load_module()
    boundary_path = tmp_path / "boundary.json"
    _write(boundary_path, _boundary())
    root = tmp_path / "ghidra"
    second = _table("0x00b0cc00")
    _write_vtables(root, [_table(), second])

    report = module.build_physics_allocator_interface_candidate(boundary_path, root)
    assert report["shared_vtable_candidate_count"] == 2
    assert report["unique_shared_vtable_candidate"] is False
    assert report["physics_allocator_interface_candidate"] is False
    assert report["candidate"] is None


def test_unconfirmed_exact_boundary_prevents_interface_promotion(tmp_path):
    module = _load_module()
    boundary_path = tmp_path / "boundary.json"
    _write(boundary_path, _boundary(confirmed=False))
    root = tmp_path / "ghidra"
    _write_vtables(root, [_table()])

    report = module.build_physics_allocator_interface_candidate(boundary_path, root)
    assert report["shared_vtable_candidate_count"] == 1
    assert report["unique_shared_vtable_candidate"] is True
    assert report["boundary_confirmed"] is False
    assert report["physics_allocator_interface_candidate"] is False


def test_table_with_only_one_exact_member_is_not_shared_candidate(tmp_path):
    module = _load_module()
    boundary_path = tmp_path / "boundary.json"
    _write(boundary_path, _boundary())
    root = tmp_path / "ghidra"
    table = _table()
    table["slots"][3] = {"slot": 3, "target": "0x00111111", "name": "FUN_00111111"}
    _write_vtables(root, [table])

    report = module.build_physics_allocator_interface_candidate(boundary_path, root)
    assert report["shared_vtable_candidate_count"] == 0
    assert report["unique_shared_vtable_candidate"] is False
    assert report["physics_allocator_interface_candidate"] is False


def test_rejects_nonheuristic_vtable_inventory(tmp_path):
    module = _load_module()
    boundary_path = tmp_path / "boundary.json"
    _write(boundary_path, _boundary())
    root = tmp_path / "ghidra"
    _write_vtables(root, [_table()], status="proven")

    try:
        module.build_physics_allocator_interface_candidate(boundary_path, root)
    except ValueError as exc:
        assert "heuristic-candidates" in str(exc)
    else:
        raise AssertionError("unexpected vtable inventory status must fail")
