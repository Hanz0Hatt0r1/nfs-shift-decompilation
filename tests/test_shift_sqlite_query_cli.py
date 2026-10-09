import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ghidra/query_shift_sqlite.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _database(path: Path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/2');
        CREATE TABLE functions(address TEXT PRIMARY KEY,name TEXT,end_address TEXT,signature TEXT,mnemonic_fingerprint TEXT,raw_json TEXT NOT NULL);
        CREATE TABLE calls(caller TEXT,callee TEXT,caller_address TEXT,callee_address TEXT,callsite TEXT,kind TEXT,indirect INTEGER NOT NULL DEFAULT 0,raw_json TEXT NOT NULL);
        CREATE TABLE strings(value TEXT,address TEXT,containing_function TEXT,raw_json TEXT NOT NULL);
        CREATE TABLE globals(address TEXT,name TEXT,data_type TEXT,xref_count INTEGER,raw_json TEXT NOT NULL);
        """
    )
    db.execute("INSERT INTO functions VALUES(?,?,?,?,?,?)", ("0x1000", "FUN_00001000", "0x1010", "void f(void)", "abc", "{}"))
    db.execute("INSERT INTO functions VALUES(?,?,?,?,?,?)", ("0x2000", "FUN_00002000", "0x2010", "void g(void)", "def", "{}"))
    db.execute("INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)", ("FUN_00001000", "FUN_00002000", "0x1000", "0x2000", "0x1005", "direct", 0, "{}"))
    db.execute("INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)", ("FUN_00002000", "", "0x2000", "", "0x2007", "indirect", 1, "{}"))
    db.execute("INSERT INTO strings VALUES(?,?,?,?)", ("WedgeRange", "0x3000", "FUN_00001000", "{}"))
    db.execute("INSERT INTO globals VALUES(?,?,?,?,?)", ("0x4000", "DAT_00004000", "undefined4", 2, "{}"))
    db.commit()
    db.close()


def _database_v1(path: Path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1');
        CREATE TABLE functions(address TEXT PRIMARY KEY,name TEXT,end_address TEXT,signature TEXT,mnemonic_fingerprint TEXT,raw_json TEXT NOT NULL);
        CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT NOT NULL);
        CREATE TABLE strings(value TEXT,address TEXT,containing_function TEXT,raw_json TEXT NOT NULL);
        CREATE TABLE globals(address TEXT,name TEXT,data_type TEXT,xref_count INTEGER,raw_json TEXT NOT NULL);
        """
    )
    raw = json.dumps({
        "from_function": "0x00758b50",
        "from_name": "FUN_00758b50",
        "instruction": "0x00758d6b",
        "to": "0x00755950",
        "to_name": "FUN_00755950",
        "indirect": False,
    })
    db.execute("INSERT INTO calls VALUES(?,?,?,?,?)", ("0x00758b50", "", "0x00758d6b", "direct", raw))
    db.commit()
    db.close()


def test_query_helpers_cover_common_navigation(tmp_path):
    db_path = tmp_path / "shift.sqlite"
    _database(db_path)
    module = _load(SCRIPT, "query_shift_sqlite")

    assert module.query(db_path, "function", "FUN_00001000")["rows"][0]["address"] == "0x1000"
    assert module.query(db_path, "function", "0x1000")["rows"][0]["name"] == "FUN_00001000"
    assert module.query(db_path, "callers", "FUN_00002000")["rows"][0]["caller"] == "FUN_00001000"
    assert module.query(db_path, "callers", "0x2000")["rows"][0]["callsite"] == "0x1005"
    assert module.query(db_path, "callees", "0x1000")["rows"][0]["callee"] == "FUN_00002000"
    assert module.query(db_path, "callsite", "0x2007")["rows"][0]["indirect"] == 1
    assert module.query(db_path, "strings", "Wedge")["rows"][0]["value"] == "WedgeRange"
    assert module.query(db_path, "globals", "DAT_00004000")["rows"][0]["address"] == "0x4000"


def test_cli_outputs_stable_json(tmp_path):
    db_path = tmp_path / "shift.sqlite"
    _database(db_path)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(db_path), "callers", "FUN_00002000"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["format"] == "SHIFT.GhidraSQLiteQuery/1"
    assert payload["index_format"] == "SHIFT.GhidraSQLiteIndex/2"
    assert payload["preferred_index_format"] == "SHIFT.GhidraSQLiteIndex/2"
    assert payload["command"] == "callers"
    assert payload["count"] == 1
    assert payload["rows"][0]["caller_address"] == "0x1000"


def test_v1_callers_query_recovers_target_from_raw_json(tmp_path):
    db_path = tmp_path / "old.sqlite"
    _database_v1(db_path)
    module = _load(SCRIPT, "query_shift_sqlite_v1")

    by_address = module.query(db_path, "callers", "0x00755950")
    assert by_address["index_format"] == "SHIFT.GhidraSQLiteIndex/1"
    assert by_address["count"] == 1
    row = by_address["rows"][0]
    assert row["caller"] == "FUN_00758b50"
    assert row["caller_address"] == "0x00758b50"
    assert row["callee"] == "FUN_00755950"
    assert row["callee_address"] == "0x00755950"
    assert row["callsite"] == "0x00758d6b"
    assert row["indirect"] == 0

    by_name = module.query(db_path, "callers", "FUN_00755950")
    assert by_name["count"] == 1
    assert by_name["rows"][0] == row


def test_cli_supports_v1_raw_json_callers(tmp_path):
    db_path = tmp_path / "old.sqlite"
    _database_v1(db_path)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(db_path), "callers", "FUN_00755950"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["index_format"] == "SHIFT.GhidraSQLiteIndex/1"
    assert payload["count"] == 1
    assert payload["rows"][0]["callsite"] == "0x00758d6b"


def test_query_rejects_unknown_index_format(tmp_path):
    db_path = tmp_path / "unknown.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/0')")
    db.commit()
    db.close()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(db_path), "function", "FUN_00001000"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "rebuild with build_shift_sqlite_index.py" in proc.stderr


def test_limit_is_enforced(tmp_path):
    db_path = tmp_path / "shift.sqlite"
    _database(db_path)
    db = sqlite3.connect(db_path)
    db.execute("INSERT INTO strings VALUES(?,?,?,?)", ("WedgeSetting", "0x3004", "FUN_00002000", "{}"))
    db.commit()
    db.close()
    module = _load(SCRIPT, "query_shift_sqlite_limit")
    payload = module.query(db_path, "strings", "Wedge", limit=1)
    assert payload["count"] == 1
    assert len(payload["rows"]) == 1
