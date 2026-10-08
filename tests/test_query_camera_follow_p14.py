import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _create_index(path: Path, *, legacy: bool = False) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE functions(
                address TEXT PRIMARY KEY,
                name TEXT,
                end_address TEXT,
                signature TEXT,
                mnemonic_fingerprint TEXT,
                raw_json TEXT NOT NULL
            );
            """
        )
        if legacy:
            db.executescript(
                """
                CREATE TABLE calls(
                    caller TEXT,
                    callee TEXT,
                    callsite TEXT,
                    kind TEXT,
                    raw_json TEXT NOT NULL
                );
                """
            )
            db.execute("INSERT INTO metadata VALUES(?,?)", ("format", "SHIFT.GhidraSQLiteIndex/1"))
        else:
            db.executescript(
                """
                CREATE TABLE calls(
                    caller TEXT,
                    callee TEXT,
                    caller_address TEXT,
                    callee_address TEXT,
                    callsite TEXT,
                    kind TEXT,
                    indirect INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT NOT NULL
                );
                """
            )
            db.execute("INSERT INTO metadata VALUES(?,?)", ("format", "SHIFT.GhidraSQLiteIndex/2"))

        functions = [
            ("0x0080e0d0", "FUN_0080e0d0"),
            ("0x0080e1b0", "FUN_0080e1b0"),
            ("0x0080d300", "FUN_0080d300"),
            ("0x00900000", "FUN_00900000"),
        ]
        for address, name in functions:
            db.execute(
                "INSERT INTO functions VALUES(?,?,?,?,?,?)",
                (address, name, "", "", "", "{}"),
            )

        if legacy:
            raw_mode2 = json.dumps({
                "from_function": "0x0080e1b0",
                "from_name": "FUN_0080e1b0",
                "indirect": False,
                "instruction": "0x0080e236",
                "to": "0x0080e0d0",
                "to_name": "FUN_0080e0d0",
            })
            raw_selector = json.dumps({
                "from_function": "0x00900000",
                "from_name": "FUN_00900000",
                "indirect": False,
                "instruction": "0x00900042",
                "to": "0x0080e1b0",
                "to_name": "FUN_0080e1b0",
            })
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?)", ("0x0080e1b0", "", "0x0080e236", "direct", raw_mode2))
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?)", ("0x00900000", "", "0x00900042", "direct", raw_selector))
        else:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)",
                ("FUN_0080e1b0", "FUN_0080e0d0", "0x0080e1b0", "0x0080e0d0", "0x0080e236", "direct", 0, "{}"),
            )
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)",
                ("FUN_00900000", "FUN_0080e1b0", "0x00900000", "0x0080e1b0", "0x00900042", "direct", 0, "{}"),
            )
        db.commit()
    finally:
        db.close()


def _assert_inventory(result):
    assert result["format"] == "SHIFT.CameraFollowP14CallerInventory/1"
    assert result["authority"]["semantic_authority"] == "PC retail machine code"
    assert result["authority"]["sqlite_index_is_semantic_proof"] is False
    assert result["bounded_findings"]["mode2_direct_caller_count"] == 1
    assert result["bounded_findings"]["selector_to_mode2_edge_count"] == 1
    edge = result["bounded_findings"]["selector_to_mode2_edges"][0]
    assert edge["caller"] == "FUN_0080e1b0"
    assert edge["callee"] == "FUN_0080e0d0"
    assert edge["callsite"] == "0x0080e236"
    assert result["ready"] is False
    assert "p14:runtime-argument-machine-value-flow-unproven" in result["blocking_reasons"]


def test_p14_inventory_finds_selector_mode2_edge_but_stays_fail_closed(tmp_path):
    module = _load(ROOT / "tools/research/query_camera_follow_p14.py", "query_camera_follow_p14")
    db_path = tmp_path / "shift.sqlite"
    _create_index(db_path)
    _assert_inventory(module.build(db_path))


def test_p14_inventory_supports_current_legacy_sqlite_shape(tmp_path):
    module = _load(ROOT / "tools/research/query_camera_follow_p14.py", "query_camera_follow_p14_legacy")
    db_path = tmp_path / "shift-v1.sqlite"
    _create_index(db_path, legacy=True)
    result = module.build(db_path)
    _assert_inventory(result)
    assert result["index"]["metadata"]["format"] == "SHIFT.GhidraSQLiteIndex/1"


def test_runtime_argument_identity_contract_closes_request_one_without_camera_admission():
    evidence = json.loads(
        (ROOT / "evidence/camera_follow_p14_runtime_argument_identity.json").read_text(encoding="utf-8")
    )
    assert evidence["format"] == "SHIFT.CameraFollowP14RuntimeArgumentIdentity/1"
    assert evidence["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert evidence["callgraph_bound"]["direct_retail_callers_of_FUN_0080e0d0"] == 1
    assert evidence["callgraph_bound"]["only_direct_callsite"] == "0x0080e236"
    adjudication = evidence["adjudication"]
    assert adjudication["mode2_runtime_argument_identity_resolved"] is True
    assert adjudication["runtime_argument_is_camera_object"] is True
    assert adjudication["runtime_argument_is_selected_retail_vehicle"] is False
    assert adjudication["runtime_argument_is_vehicle_world_matrix"] is False
    assert adjudication["phase651_request_1_closed"] is True
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
