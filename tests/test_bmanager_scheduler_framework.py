import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/ghidra/build_bmanager_scheduler_framework.py"


def _module():
    spec = importlib.util.spec_from_file_location("bmanager_scheduler_framework", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, Path]:
    binary = tmp_path / "binary.json"
    functions = tmp_path / "functions.jsonl"
    callgraph = tmp_path / "callgraph.jsonl"
    strings = tmp_path / "strings_xrefs.jsonl"
    runtime = tmp_path / "physics_system_runtime.py"

    binary.write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraEvidenceDatabase/1",
                "program_name": "SHIFT.exe",
                "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
            }
        ),
        encoding="utf-8",
    )

    hashes = {
        "0x0070fae0": ("FUN_0070fae0", "24c183bd4ed6f53a7f44ecf6c7b3403a812310fecff8049ae6b0faa92dc30bfc"),
        "0x00647a10": ("FUN_00647a10", "02623d464525cc356f76666acacbefbe1d55c404516f4cf2aff80b077cdfa4dd"),
        "0x0065bf80": ("FUN_0065bf80", "07f419bf72d7295ba073b55e824e3cf31d940956d68d523947b53fd964774450"),
        "0x0065bd70": ("FUN_0065bd70", "53ac6e78ad78956e0e66a64a66246c1d18319e379ecba592438ed01f43de45a8"),
        "0x0065b430": ("FUN_0065b430", "1333c50e294bacce0ef4616997162176235900395005594aa5cef7fec926d59a"),
    }
    _write_jsonl(
        functions,
        [
            {"address": address, "name": name, "mnemonic_sha256": digest}
            for address, (name, digest) in hashes.items()
        ],
    )

    edges = [
        ("0x0070fae0", "0x00647a10", "0x0070fb03"),
        ("0x00647a10", "0x0065bf80", "0x00647b07"),
        ("0x0065bf80", "0x0065bd70", "0x0065bf98"),
        ("0x0065bf80", "0x00900fb3", "0x0065bfa2"),
        ("0x0065bd70", "0x0067cbc0", "0x0065bd85"),
        ("0x0065bd70", "0x0067cbc0", "0x0065bda5"),
        ("0x0065bd70", "0x0040cb40", "0x0065bdc6"),
        ("0x0065bd70", "0x0067cbc0", "0x0065bdd3"),
        ("0x0065bd70", "0x0067cbc0", "0x0065be12"),
        ("0x0065bd70", "0x00669b00", "0x0065be48"),
        ("0x0065bd70", "0x0064f500", "0x0065be53"),
        ("0x0065bd70", "0x008f3df0", "0x0065be71"),
        ("0x0065bd70", "0x00657d90", "0x0065be76"),
        ("0x0065bd70", "0x00657d70", "0x0065be81"),
        ("0x0065bd70", "0x00657d90", "0x0065be86"),
        ("0x0065bd70", "0x00657d70", "0x0065be91"),
        ("0x0065bd70", "0x00657d90", "0x0065be96"),
        ("0x0065bd70", "0x00657d70", "0x0065bea1"),
        ("0x0065bd70", "0x004f5e10", "0x0065beb2"),
        ("0x0065bd70", "0x004f5e10", "0x0065bec3"),
        ("0x0065bd70", "0x0046f7e0", "0x0065bed4"),
        ("0x0065bd70", "0x0064f570", "0x0065bee7"),
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

    string_rows = [
        ("0x00aefc50", ", Delta( %d ms )", "0x0065b516", "0x0065b430"),
        ("0x00aefc64", ", Manual Sync, Avg. Freq = %2.2f Hz", "0x0065b4db", "0x0065b430"),
        ("0x00aefc88", ", Desired Freq = %2.2f Hz, Avg. Freq = %2.2f Hz", "0x0065b4c2", "0x0065b430"),
        ("0x00aefcb8", "Manual Update", "0x0065b496", "0x0065b430"),
        ("0x00aefcc8", "Auto Update", "0x0065b48f", "0x0065b430"),
        ("0x00aefcfc", "BManager Tick", "0x0065bedc", "0x0065bd70"),
        ("0x00aefd0c", "_BManagerSys Critical", "0x0065be64", "0x0065bd70"),
    ]
    _write_jsonl(
        strings,
        [
            {"address": address, "value": value, "xrefs": [xref], "functions": [function]}
            for address, value, xref, function in string_rows
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
        "strings": strings,
        "runtime": runtime,
    }


def _build(module, fx: dict[str, Path]):
    return module.build_framework(
        fx["binary"], fx["functions"], fx["callgraph"], fx["strings"], fx["runtime"]
    )


def test_bmanager_policy_and_static_association_are_positive_but_dispatch_stays_closed(tmp_path: Path) -> None:
    module = _module()
    report = _build(module, _fixture(tmp_path))

    assert report["format"] == "SHIFT.BManagerSchedulerFramework/1"
    assert report["status"] == "blocked-runtime-dispatch-proof"
    assert report["ready"] is False
    assert report["cadence_policy_evidence"]["auto_manual_update_strings_observed"] is True
    assert report["cadence_policy_evidence"]["desired_average_frequency_strings_observed"] is True
    assert report["cadence_policy_evidence"]["delta_ms_string_observed"] is True
    assert report["bmanager_tick_anchor"]["outgoing_call_count"] == 18
    assert report["bmanager_tick_anchor"]["indirect_outgoing_call_count"] == 0
    assert report["physics_manager_bmanager_association"]["path"] == [
        "0x0070fae0",
        "0x00647a10",
        "0x0065bf80",
        "0x0065bd70",
    ]
    assert report["physics_manager_bmanager_association"]["inheritance_claimed"] is False
    assert report["runtime_dispatch"]["bmanager_tick_to_physics_manager_vtable_plus_0x18_proven"] is False
    assert report["cadence"]["retail_cadence_admitted"] is False
    assert report["cadence"]["host_1_60_is_retail_evidence"] is False


def test_policy_string_xref_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["strings"].read_text(encoding="utf-8").splitlines()]
    rows[4]["xrefs"] = ["0x0065b490"]
    _write_jsonl(fx["strings"], rows)
    with pytest.raises(ValueError, match="string xref/function drift"):
        _build(module, fx)


def test_physics_manager_to_bmanager_association_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["callgraph"].read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row.get("instruction") != "0x00647b07"]
    _write_jsonl(fx["callgraph"], rows)
    with pytest.raises(ValueError, match="BManager association edge"):
        _build(module, fx)


def test_bmanager_tick_indirect_call_requires_reaudit(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["callgraph"].read_text(encoding="utf-8").splitlines()]
    rows.append(
        {
            "from_function": "0x0065bd70",
            "instruction": "0x0065be00",
            "to": None,
            "indirect": True,
        }
    )
    _write_jsonl(fx["callgraph"], rows)
    with pytest.raises(ValueError, match="acquired indirect outgoing calls"):
        _build(module, fx)


def test_bmanager_tick_direct_shape_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["callgraph"].read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row.get("instruction") != "0x0065be53"]
    _write_jsonl(fx["callgraph"], rows)
    with pytest.raises(ValueError, match="direct outgoing shape drift"):
        _build(module, fx)


def test_bmanager_function_hash_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["functions"].read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["address"] == "0x0065bd70":
            row["mnemonic_sha256"] = "0" * 64
    _write_jsonl(fx["functions"], rows)
    with pytest.raises(ValueError, match="function hash drift"):
        _build(module, fx)
