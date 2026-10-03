import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_memory_wrapper_family.py"
    spec = importlib.util.spec_from_file_location("build_memory_wrapper_family", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _function(address, name, cc, storages, types=None, size=16):
    if types is None:
        types = ["undefined4"] * len(storages)
    return {
        "address": address,
        "name": name,
        "size": size,
        "thunk": False,
        "calling_convention": cc,
        "signature": f"auto-typed {name}",
        "parameters": [
            {"name": f"param_{index + 1}", "type": type_name, "storage": storage}
            for index, (type_name, storage) in enumerate(zip(types, storages))
        ],
    }


def _edge(source, target, instruction):
    return {
        "from_function": source,
        "instruction": instruction,
        "to": target,
        "to_name": "target",
        "indirect": False,
    }


def _fixture(tmp_path):
    memory = tmp_path / "memory.json"
    _write_json(
        memory,
        {
            "format": "SHIFT-MEMORY-HELPER-SEMANTICS/1",
            "families": [
                {
                    "create_helper": "FUN_00886900",
                    "release_helper": "FUN_00886930",
                    "pool_allocation_path_evidence": True,
                    "pool_free_path_evidence": True,
                    "diagnostic_backed_pool_lifetime_family": True,
                }
            ],
        },
    )
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    functions = [
        _function("0x008868c0", "FUN_008868c0", "__cdecl", ["Stack[0x4]:4"]),
        _function(
            "0x008868d0",
            "FUN_008868d0",
            "__cdecl",
            ["Stack[0x4]:4", "Stack[0x8]:4"],
            ["uint", "AptFrameStack *"],
        ),
        _function(
            "0x00886900",
            "FUN_00886900",
            "__cdecl",
            ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
            ["uint", "AptFrameStack *", "uint"],
        ),
        _function(
            "0x00886930",
            "FUN_00886930",
            "__fastcall",
            ["ECX:4", "DL:1", "Stack[0x4]:4"],
            ["undefined4", "char", "uint"],
        ),
        _function(
            "0x00886950",
            "FUN_00886950",
            "__fastcall",
            ["ECX:4", "DL:1", "Stack[0x4]:4", "Stack[0x8]:4"],
            ["undefined4", "char", "uint", "void *"],
        ),
    ]
    _write_jsonl(ghidra / "functions.jsonl", functions)
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            _edge("0x008868c0", "0x006382b0", "0x008868c9"),
            _edge("0x008868d0", "0x00638020", "0x008868df"),
            _edge("0x008868d0", "0x006382b0", "0x008868ec"),
            _edge("0x00886900", "0x00638020", "0x00886911"),
            _edge("0x00886900", "0x006382b0", "0x0088691f"),
            _edge("0x00886930", "0x0064f4c0", "0x0088693b"),
            _edge("0x00886950", "0x0064f260", "0x00886966"),
            _edge("0x00886950", "0x0064f4c0", "0x0088696c"),
        ],
    )
    return memory, ghidra


def test_confirms_retail_wrapper_family_from_storage_and_direct_edges(tmp_path):
    module = _load_module()
    memory, ghidra = _fixture(tmp_path)
    report = module.build_memory_wrapper_family(memory, ghidra)

    assert report["format"] == "SHIFT-MEMORY-WRAPPER-FAMILY/1"
    assert report["wrapper_count"] == 5
    assert report["confirmed_wrapper_shape_count"] == 5
    assert report["diagnostic_anchor_pair_confirmed"] is True
    assert report["memory_wrapper_family_candidate"] is True
    assert report["progressions"]["create"]["parameter_counts"] == [1, 2, 3]
    assert report["progressions"]["release"]["parameter_counts"] == [3, 4]
    assert report["progressions"]["create"]["storage_prefix_growth"] is True
    assert report["progressions"]["release"]["storage_prefix_growth"] is True

    create_anchor = next(row for row in report["wrappers"] if row["name"] == "FUN_00886900")
    assert create_anchor["diagnostic_anchor_confirmed"] is True
    assert create_anchor["parameter_storage"] == [
        "Stack[0x4]:4",
        "Stack[0x8]:4",
        "Stack[0xc]:4",
    ]
    assert create_anchor["semantic_parameter_types_used_for_promotion"] is False
    assert "AptFrameStack *" in create_anchor["reported_parameter_types"]

    scope = report["scope"]
    assert scope["ghidra_semantic_parameter_types_trusted"] is False
    assert scope["argument_roles_proven"] is False
    assert scope["allocator_abi_proven"] is False
    assert scope["operator_new_identity_proven"] is False


def test_auto_types_do_not_affect_promotion(tmp_path):
    module = _load_module()
    memory, ghidra = _fixture(tmp_path)
    rows = [json.loads(line) for line in (ghidra / "functions.jsonl").read_text().splitlines()]
    for row in rows:
        for parameter in row["parameters"]:
            parameter["type"] = "COMPLETELY_WRONG_AUTO_TYPE *"
    _write_jsonl(ghidra / "functions.jsonl", rows)

    report = module.build_memory_wrapper_family(memory, ghidra)
    assert report["memory_wrapper_family_candidate"] is True
    assert report["confirmed_wrapper_shape_count"] == 5


def test_calling_convention_mismatch_fails_closed(tmp_path):
    module = _load_module()
    memory, ghidra = _fixture(tmp_path)
    rows = [json.loads(line) for line in (ghidra / "functions.jsonl").read_text().splitlines()]
    for row in rows:
        if row["address"] == "0x00886930":
            row["calling_convention"] = "__cdecl"
    _write_jsonl(ghidra / "functions.jsonl", rows)

    report = module.build_memory_wrapper_family(memory, ghidra)
    release = next(row for row in report["wrappers"] if row["name"] == "FUN_00886930")
    assert release["calling_convention_match"] is False
    assert release["abi_shape_confirmed"] is False
    assert release["wrapper_shape_confirmed"] is False
    assert report["memory_wrapper_family_candidate"] is False


def test_missing_backend_edge_preserves_partial_abi_evidence(tmp_path):
    module = _load_module()
    memory, ghidra = _fixture(tmp_path)
    edges = [json.loads(line) for line in (ghidra / "callgraph.jsonl").read_text().splitlines()]
    edges = [
        row
        for row in edges
        if not (
            row["from_function"] == "0x00886950"
            and row["to"] == "0x0064f260"
        )
    ]
    _write_jsonl(ghidra / "callgraph.jsonl", edges)

    report = module.build_memory_wrapper_family(memory, ghidra)
    extended_release = next(row for row in report["wrappers"] if row["name"] == "FUN_00886950")
    assert extended_release["abi_shape_confirmed"] is True
    assert extended_release["backend_shape_confirmed"] is False
    assert extended_release["wrapper_shape_confirmed"] is False
    assert report["confirmed_wrapper_shape_count"] == 4
    assert report["memory_wrapper_family_candidate"] is False


def test_diagnostic_anchor_pair_is_required_for_family_candidate(tmp_path):
    module = _load_module()
    memory, ghidra = _fixture(tmp_path)
    payload = json.loads(memory.read_text())
    payload["families"][0]["pool_free_path_evidence"] = False
    payload["families"][0]["diagnostic_backed_pool_lifetime_family"] = False
    _write_json(memory, payload)

    report = module.build_memory_wrapper_family(memory, ghidra)
    assert report["confirmed_wrapper_shape_count"] == 5
    assert report["diagnostic_anchor_pair_confirmed"] is False
    assert report["memory_wrapper_family_candidate"] is False
