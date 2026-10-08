import importlib.util
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _create_index(path: Path) -> None:
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
        db.execute(
            "INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)",
            (
                "FUN_0080e1b0",
                "FUN_0080e0d0",
                "0x0080e1b0",
                "0x0080e0d0",
                "0x0080e250",
                "direct",
                0,
                "{}",
            ),
        )
        db.execute(
            "INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)",
            (
                "FUN_00900000",
                "FUN_0080e1b0",
                "0x00900000",
                "0x0080e1b0",
                "0x00900042",
                "direct",
                0,
                "{}",
            ),
        )
        db.commit()
    finally:
        db.close()


def test_p14_inventory_finds_selector_mode2_edge_but_stays_fail_closed(tmp_path):
    module = _load(
        ROOT / "tools/research/query_camera_follow_p14.py",
        "query_camera_follow_p14",
    )
    db_path = tmp_path / "shift.sqlite"
    _create_index(db_path)

    result = module.build(db_path)

    assert result["format"] == "SHIFT.CameraFollowP14CallerInventory/1"
    assert result["authority"]["semantic_authority"] == "PC retail machine code"
    assert result["authority"]["sqlite_index_is_semantic_proof"] is False
    assert result["bounded_findings"]["mode2_direct_caller_count"] == 1
    assert result["bounded_findings"]["selector_to_mode2_edge_count"] == 1
    assert result["ready"] is False
    assert "p14:runtime-argument-machine-value-flow-unproven" in result["blocking_reasons"]
    requests = {row["id"]: row for row in result["proof_requests"]}
    assert requests["mode2_runtime_argument_identity"]["status"] == "requires-machine-body-trace"
    assert requests["mode2_source_vtable_identity"]["status"] == "not-promoted"
