import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_physics_allocator_boundary.py"
    )
    spec = importlib.util.spec_from_file_location("build_physics_allocator_boundary", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _function(address, name, types=("void *", "uint")):
    return {
        "address": address,
        "name": name,
        "size": 116 if address.endswith("cd90") else 133,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined {name}(...) ",
        "parameters": [
            {"name": "this", "type": types[0], "storage": "ECX:4 (auto)"},
            {"name": "param_1", "type": types[1], "storage": "Stack[0x4]:4"},
        ],
        "mnemonic_sha256": address,
    }


def _string(address, value, functions):
    return {
        "address": address,
        "value": value,
        "xrefs": [address],
        "functions": functions,
    }


def _edge(source, instruction, target, name):
    return {
        "from_function": source,
        "from_name": source,
        "instruction": instruction,
        "to": target,
        "to_name": name,
        "indirect": False,
    }


def _write_retail_shape(root, *, bogus_types=False, shared_malloc=False, omit_free_pool_error=False):
    root.mkdir()
    types = ("BogusThis *", "BogusArg") if bogus_types else ("void *", "uint")
    _write_jsonl(
        root / "functions.jsonl",
        [
            _function("0x0079cd90", "FUN_0079cd90", types),
            _function("0x0079ce30", "FUN_0079ce30", types),
            _function("0x00123450", "FUN_00123450"),
        ],
    )
    malloc_functions = ["0x0079cd90", "0x00123450"] if shared_malloc else ["0x0079cd90"]
    strings = [
        _string("0x00b0b8d0", "pPool", ["0x0079cd90", "0x0079ce30"]),
        _string(
            "0x00b0b8d8",
            ".\\Source\\System\\PhysXSupport.cpp",
            ["0x0079cd90", "0x0079ce30"],
        ),
        _string(
            "0x00b0b8fc",
            "MWL::Core::PhysicsAllocator::malloc",
            malloc_functions,
        ),
        _string(
            "0x00b0b938",
            "MWL::Core::PhysicsAllocator::free",
            ["0x0079ce30"],
        ),
    ]
    pool_functions = ["0x0079cd90"] if omit_free_pool_error else ["0x0079cd90", "0x0079ce30"]
    strings.append(_string("0x00b0b920", "No BMemPool available", pool_functions))
    _write_jsonl(root / "strings_xrefs.jsonl", strings)
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            _edge("0x0079cd90", "0x0079cdab", "0x0063ba50", "FUN_0063ba50"),
            _edge("0x0079cd90", "0x0079cdb5", "0x00710860", "FUN_00710860"),
            _edge("0x0079cd90", "0x0079cdf9", "0x00638300", "FUN_00638300"),
            _edge("0x0079ce30", "0x0079ce3f", "0x0063bce0", "FUN_0063bce0"),
            _edge("0x0079ce30", "0x0079ce60", "0x00710860", "FUN_00710860"),
            _edge("0x0079ce30", "0x0079ceaa", "0x0064f250", "FUN_0064f250"),
        ],
    )


def test_confirms_paired_physics_allocator_boundary(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    _write_retail_shape(root)

    report = module.build_physics_allocator_boundary(root)

    assert report["format"] == "SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1"
    assert report["member_count"] == 2
    assert report["confirmed_member_count"] == 2
    assert report["physics_allocator_boundary_confirmed"] is True
    assert report["same_entry_storage_shape"] is True
    assert report["shared_required_strings"] == [
        ".\\Source\\System\\PhysXSupport.cpp",
        "No BMemPool available",
        "pPool",
    ]

    malloc, free = report["members"]
    assert malloc["method_anchor"] == "MWL::Core::PhysicsAllocator::malloc"
    assert free["method_anchor"] == "MWL::Core::PhysicsAllocator::free"
    assert malloc["parameter_storage"] == ["ECX:4 (auto)", "Stack[0x4]:4"]
    assert free["parameter_storage"] == ["ECX:4 (auto)", "Stack[0x4]:4"]
    assert malloc["direct_call_targets"] == ["0x00638300", "0x0063ba50", "0x00710860"]
    assert free["direct_call_targets"] == ["0x0063bce0", "0x0064f250", "0x00710860"]
    assert all(member["blockers"] == [] for member in report["members"])
    assert report["scope"]["explicit_stack_parameter_role_proven"] is False
    assert report["scope"]["return_value_abi_proven"] is False
    assert report["scope"]["pool_ownership_semantics_proven"] is False


def test_semantic_auto_types_do_not_affect_boundary_promotion(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    _write_retail_shape(root, bogus_types=True)

    report = module.build_physics_allocator_boundary(root)
    assert report["physics_allocator_boundary_confirmed"] is True
    assert report["members"][0]["reported_parameter_types"] == ["BogusThis *", "BogusArg"]
    assert report["members"][0]["semantic_parameter_types_used_for_promotion"] is False


def test_shared_malloc_method_anchor_fails_closed(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    _write_retail_shape(root, shared_malloc=True)

    report = module.build_physics_allocator_boundary(root)
    malloc = report["members"][0]
    assert malloc["method_anchor_exact_once"] is True
    assert malloc["method_anchor_unique_to_function"] is False
    assert malloc["member_confirmed"] is False
    assert "method_anchor_not_unique_to_function" in malloc["blockers"]
    assert report["physics_allocator_boundary_confirmed"] is False


def test_missing_shared_pool_diagnostic_fails_only_affected_member(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    _write_retail_shape(root, omit_free_pool_error=True)

    report = module.build_physics_allocator_boundary(root)
    malloc, free = report["members"]
    assert malloc["member_confirmed"] is True
    assert free["member_confirmed"] is False
    assert "missing_shared_string:No BMemPool available" in free["blockers"]
    assert report["confirmed_member_count"] == 1
    assert report["physics_allocator_boundary_confirmed"] is False


def test_requires_direct_ghidra_datasets(tmp_path):
    module = _load_module()
    root = tmp_path / "ghidra"
    root.mkdir()
    _write_jsonl(root / "functions.jsonl", [])

    try:
        module.build_physics_allocator_boundary(root)
    except FileNotFoundError as exc:
        assert "strings_xrefs.jsonl" in str(exc)
        assert "callgraph.jsonl" in str(exc)
    else:
        raise AssertionError("missing direct Ghidra datasets must fail")
