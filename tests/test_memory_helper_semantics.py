import importlib.util
import json
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "ghidra"
    path = tool_dir / "build_memory_helper_semantics.py"
    spec = importlib.util.spec_from_file_location("build_memory_helper_semantics", path)
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


def test_proves_bounded_pool_allocation_and_free_paths(tmp_path):
    module = _load_module()
    families = tmp_path / "families.json"
    _write_json(
        families,
        {
            "format": "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1",
            "families": [
                {
                    "create_helper": "FUN_00886900",
                    "release_helper": "FUN_00886930",
                    "class_count": 2,
                    "classes": ["A", "B"],
                    "descriptors": [1, 2],
                    "recurrent_helper_pair": True,
                    "crosschecked_recurrent_helper_family_candidate": True,
                },
                {
                    "create_helper": "FUN_00900000",
                    "release_helper": "FUN_00900030",
                    "class_count": 1,
                    "classes": ["Other"],
                    "descriptors": [3],
                    "recurrent_helper_pair": False,
                    "crosschecked_recurrent_helper_family_candidate": False,
                },
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {
                "from_function": "0x00886900",
                "instruction": "0x00886911",
                "to": "0x00638020",
                "to_name": "FUN_00638020",
                "indirect": False,
            },
            {
                "from_function": "0x00886930",
                "instruction": "0x0088693b",
                "to": "0x0064f4c0",
                "to_name": "thunk_FUN_0064f3a0",
                "indirect": False,
            },
            {
                "from_function": "0x0064f4c0",
                "instruction": "0x0064f4c2",
                "to": "0x0064f3a0",
                "to_name": "FUN_0064f3a0",
                "indirect": False,
            },
            {
                "from_function": "0x0064f3a0",
                "instruction": "0x0064f44c",
                "to": "0x00657c30",
                "to_name": "FUN_00657c30",
                "indirect": False,
            },
            {
                "from_function": "0x00900000",
                "instruction": "0x00900010",
                "to": "0x00900100",
                "to_name": "FUN_00900100",
                "indirect": False,
            },
        ],
    )
    _write_jsonl(
        ghidra / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00aec0e8",
                "value": "Unable to allocate %d bytes of memory from the pool (%s)",
                "xrefs": ["0x006381b1"],
                "functions": ["0x00638020"],
            },
            {
                "address": "0x00aee94c",
                "value": "Error freeing small alloc (no head) '0x%p' from pool: '%s'\n",
                "xrefs": ["0x00657cb1"],
                "functions": ["0x00657c30"],
            },
            {
                "address": "0x00dead00",
                "value": "Unable to allocate EntitlementEntry",
                "xrefs": ["0x00900110"],
                "functions": ["0x00900100"],
            },
        ],
    )

    report = module.build_memory_helper_semantics(families, ghidra, max_depth=4)
    assert report["format"] == "SHIFT-MEMORY-HELPER-SEMANTICS/1"
    assert report["family_count"] == 2
    assert report["allocation_path_family_count"] == 1
    assert report["free_path_family_count"] == 1
    assert report["diagnostic_backed_pool_lifetime_family_count"] == 1
    assert len(report["diagnostic_inventory"]) == 2

    row = report["families"][0]
    assert row["create_helper"] == "FUN_00886900"
    assert row["release_helper"] == "FUN_00886930"
    assert row["pool_allocation_path_evidence"] is True
    assert row["pool_free_path_evidence"] is True
    assert row["diagnostic_backed_pool_lifetime_family"] is True

    allocation = row["allocation_diagnostic_paths"][0]
    assert allocation["depth"] == 1
    assert allocation["function_path"] == ["0x00886900", "0x00638020"]
    assert allocation["diagnostic"]["kind"] == "pool-allocation-diagnostic"

    freeing = row["free_diagnostic_paths"][0]
    assert freeing["depth"] == 3
    assert freeing["function_path"] == [
        "0x00886930",
        "0x0064f4c0",
        "0x0064f3a0",
        "0x00657c30",
    ]
    assert freeing["diagnostic"]["kind"] == "pool-free-diagnostic"

    other = report["families"][1]
    assert other["diagnostic_backed_pool_lifetime_family"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_depth_bound_keeps_partial_evidence_explicit(tmp_path):
    module = _load_module()
    families = tmp_path / "families.json"
    _write_json(
        families,
        {
            "format": "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1",
            "families": [
                {
                    "create_helper": "FUN_00886900",
                    "release_helper": "FUN_00886930",
                    "class_count": 2,
                    "classes": ["A", "B"],
                    "descriptors": [1, 2],
                    "recurrent_helper_pair": True,
                    "crosschecked_recurrent_helper_family_candidate": True,
                }
            ],
        },
    )
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {"from_function": "0x00886900", "to": "0x00638020", "indirect": False},
            {"from_function": "0x00886930", "to": "0x0064f4c0", "indirect": False},
            {"from_function": "0x0064f4c0", "to": "0x0064f3a0", "indirect": False},
            {"from_function": "0x0064f3a0", "to": "0x00657c30", "indirect": False},
        ],
    )
    _write_jsonl(
        ghidra / "strings_xrefs.jsonl",
        [
            {
                "address": "0x1",
                "value": "Unable to allocate 12 bytes of memory from the pool (x)",
                "functions": ["0x00638020"],
            },
            {
                "address": "0x2",
                "value": "Error freeing small alloc (no head) '0x0' from pool: 'x'",
                "functions": ["0x00657c30"],
            },
        ],
    )

    report = module.build_memory_helper_semantics(families, ghidra, max_depth=2)
    row = report["families"][0]
    assert row["pool_allocation_path_evidence"] is True
    assert row["pool_free_path_evidence"] is False
    assert row["diagnostic_backed_pool_lifetime_family"] is False
