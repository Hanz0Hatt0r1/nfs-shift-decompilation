import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/ghidra/build_retail_outer_update_scheduler_frontier.py"


def _module():
    spec = importlib.util.spec_from_file_location("retail_scheduler_frontier", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _pointer(address: str, raw_hex: str) -> dict:
    return {
        "address": address,
        "block": ".rdata",
        "data_type": "undefined *",
        "length": 4,
        "raw_hex": raw_hex,
        "raw_truncated": False,
    }


def _fixture(tmp_path: Path) -> dict[str, Path]:
    binary = tmp_path / "binary.json"
    functions = tmp_path / "functions.jsonl"
    callgraph = tmp_path / "callgraph.jsonl"
    tables = tmp_path / "static_tables.jsonl"
    globals_path = tmp_path / "globals.jsonl"
    runtime = tmp_path / "physics_system_runtime.py"

    binary.write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraEvidenceDatabase/1",
                "program_name": "SHIFT.exe",
                "executable_format": "Portable Executable (PE)",
                "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        functions,
        [
            {
                "address": "0x00711b50",
                "name": "FUN_00711b50",
                "mnemonic_sha256": "d4fdc3eb2a9e34f05e756d927bfe2177a0ba416173a54d84ff516a0fed0029d8",
            },
            {
                "address": "0x007119c0",
                "name": "FUN_007119c0",
                "mnemonic_sha256": "59d4eb983ba1644078fed51800755cdceebf6fc7dacda6390cd587319e176dc2",
            },
            {
                "address": "0x007117e0",
                "name": "FUN_007117e0",
                "mnemonic_sha256": "499d7057f793b98ea406aa8d4e7df827f138763d2624a5dd48a29290deca576f",
            },
        ],
    )

    edges = [
        ("0x00711b50", "0x007119c0", "0x00711b76"),
        ("0x007119c0", "0x007117e0", "0x00711a6c"),
        ("0x007117e0", "0x0070f940", "0x0071196b"),
        ("0x0070f940", "0x007155e0", "0x0070f95b"),
        ("0x0070f940", "0x007155e0", "0x0070f977"),
        ("0x0070f940", "0x007155e0", "0x0070f993"),
        ("0x0070f940", "0x007155e0", "0x0070f9af"),
        ("0x007155e0", "0x0048ed52", "0x007155e3"),
        ("0x0048ed52", "0x007155e9", "0x0048ed58"),
        ("0x007155e9", "0x00715380", "0x00715602"),
        ("0x00715380", "0x00713050", "0x00715434"),
        ("0x00710870", "0x0070fe90", "0x00710871"),
    ]
    _write_jsonl(
        callgraph,
        [
            {
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "indirect": False,
            }
            for source, target, instruction in edges
        ],
    )
    _write_jsonl(
        tables,
        [
            _pointer("0x00b0453c", "501b7100"),
            _pointer("0x00b04540", "b0ff7000"),
        ],
    )
    _write_jsonl(
        globals_path,
        [
            {
                "address": "0x00b04524",
                "name": "PTR_FUN_00b04524",
                "data_type": "undefined *",
                "length": 4,
                "reference_count": 2,
            }
        ],
    )
    runtime.write_text(
        'MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"\n'
        'MANAGER_VTABLE = "PTR_FUN_00b04524"\n'
        'MANAGER_SOURCE_FILE = "Source/Manager/cPhysicsManager.hpp"\n'
        'MANAGER_LAYOUT = {"functions": ["FUN_0070fae0", "FUN_0070f580"], '
        '"named_object": "Physics Manager"}\n',
        encoding="utf-8",
    )
    return {
        "binary": binary,
        "functions": functions,
        "callgraph": callgraph,
        "tables": tables,
        "globals": globals_path,
        "runtime": runtime,
    }


def _build(module, fx: dict[str, Path]):
    return module.build_frontier(
        fx["binary"],
        fx["functions"],
        fx["callgraph"],
        fx["tables"],
        fx["globals"],
        fx["runtime"],
    )


def test_manager_owned_scheduler_entry_is_positive_but_retail_cadence_stays_closed(
    tmp_path: Path,
) -> None:
    module = _module()
    report = _build(module, _fixture(tmp_path))

    assert report["format"] == "SHIFT.RetailOuterUpdateSchedulerFrontier/1"
    assert report["status"] == "blocked-indirect-entry-proof"
    assert report["ready"] is False
    assert report["binary_identity"]["executable_md5"] == (
        "705af8b420e5eb1e3834ac43d5533c6b"
    )
    assert report["physics_manager_vtable"]["scheduler_slot_offset"] == 0x18
    assert report["physics_manager_vtable"]["scheduler_entry"] == "0x00711b50"
    assert report["physics_manager_vtable"]["release_slot_offset"] == 0x1C
    assert report["physics_manager_vtable"]["release_entry"] == "0x0070ffb0"
    assert report["physics_manager_vtable"]["scheduler_entry_owner_proven"] is True
    assert report["direct_scheduler_chain"]["verified"] is True
    assert report["direct_scheduler_chain"]["path"][0] == "0x00711b50"
    assert report["direct_scheduler_chain"]["path"][-1] == "0x00713050"
    assert report["external_dispatch"]["indirect_invocation_callsite_proven"] is False
    assert report["cadence"]["retail_cadence_admitted"] is False
    assert report["cadence"]["host_1_60_is_retail_evidence"] is False
    assert report["limits"]["manager_slot_named_update"] is False
    assert report["limits"]["callgraph_adjacency_promoted_to_cadence"] is False


def test_retail_binary_schema_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    fx["binary"].write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraEvidenceDatabase/1",
                "program_name": "SHIFT.exe",
                "executable_format": "Portable Executable (PE)",
                "md5": "705af8b420e5eb1e3834ac43d5533c6b",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="retail PE MD5 drift"):
        _build(module, fx)


def test_manager_scheduler_slot_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    _write_jsonl(
        fx["tables"],
        [
            _pointer("0x00b0453c", "901b7100"),
            _pointer("0x00b04540", "b0ff7000"),
        ],
    )
    with pytest.raises(ValueError, match=r"\+0x18 target drift"):
        _build(module, fx)


def test_release_neighbor_cross_check_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    _write_jsonl(
        fx["tables"],
        [
            _pointer("0x00b0453c", "501b7100"),
            _pointer("0x00b04540", "00000000"),
        ],
    )
    with pytest.raises(ValueError, match=r"\+0x1c release target drift"):
        _build(module, fx)


def test_direct_incoming_scheduler_call_requires_reaudit(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [
        json.loads(line)
        for line in fx["callgraph"].read_text(encoding="utf-8").splitlines()
    ]
    rows.append(
        {
            "from_function": "0x00401000",
            "instruction": "0x00401010",
            "to": "0x00711b50",
            "indirect": False,
        }
    )
    _write_jsonl(fx["callgraph"], rows)
    with pytest.raises(ValueError, match="unexpectedly acquired a direct caller"):
        _build(module, fx)


def test_four_way_dispatch_multiplicity_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [
        json.loads(line)
        for line in fx["callgraph"].read_text(encoding="utf-8").splitlines()
    ]
    rows = [row for row in rows if row.get("instruction") != "0x0070f993"]
    _write_jsonl(fx["callgraph"], rows)
    with pytest.raises(ValueError, match="direct scheduler edge"):
        _build(module, fx)


def test_runtime_contract_cannot_relabel_heuristic_vtable_start(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    fx["runtime"].write_text(
        'MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"\n'
        'MANAGER_VTABLE = "PTR_FUN_00b04534"\n'
        'MANAGER_SOURCE_FILE = "Source/Manager/cPhysicsManager.hpp"\n'
        'MANAGER_LAYOUT = {"functions": ["FUN_0070fae0", "FUN_0070f580"], '
        '"named_object": "Physics Manager"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="runtime contract drift"):
        _build(module, fx)
