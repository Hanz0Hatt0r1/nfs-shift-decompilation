import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_blocker_graph_is_fail_closed_and_partitioned():
    p = json.loads((ROOT / "coordination/decomp_blockers.json").read_text(encoding="utf-8"))
    assert p["format"] == "SHIFT.DecompBlockerGraph/1"
    assert p["rules"]["pc_retail_semantic_authority"] is True
    assert p["rules"]["numeric_offset_equality_is_identity"] is False
    assert p["rules"]["external_provider_count"] == 7
    streams = {row["id"]: row for row in p["workstreams"]}
    assert streams["P1.3"]["owner"] == "Process 1B"
    children = {row["id"]: row for row in streams["P1.3"]["children"]}
    manager2a0 = children["P1.3.manager2a0"]
    assert manager2a0["status"] == "candidate-rejected-remaining-paths-open"
    assert "0x00469b1d" in manager2a0["rejected_candidate"]
    assert "0x0045daa3" in manager2a0["next"]
    assert streams["P2.3"]["blocked_by"] == ["P1.1"]


def test_scaffold_generator_defaults_fail_closed(tmp_path):
    script = ROOT / "tools/research/scaffold_proof.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(tmp_path),
            "--contract",
            "SHIFT.TestProof/1",
            "--title",
            "Test proof",
            "--blocker",
            "Need exact provenance.",
            "--next-step",
            "Trace the exact writer.",
            "--slug",
            "test_proof",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads((tmp_path / "evidence/test_proof.json").read_text(encoding="utf-8"))
    assert evidence["ready"] is False
    assert evidence["adjudication"]["proof_complete"] is False
    assert evidence["adjudication"]["external_provider_count"] == 7
    assert (tmp_path / "docs/PROCESS_TEST_PROOF.md").is_file()
    assert (tmp_path / "tests/test_test_proof.py").is_file()


def test_sqlite_builder_indexes_core_export_layers(tmp_path):
    export = tmp_path / "export"
    export.mkdir()
    (export / "functions.jsonl").write_text(
        json.dumps({"address": "0x1000", "name": "FUN_00001000", "end": "0x1010"}) + "\n",
        encoding="utf-8",
    )
    (export / "callgraph.jsonl").write_text(
        json.dumps({"caller": "FUN_00001000", "callee": "FUN_00002000", "callsite": "0x1005"}) + "\n",
        encoding="utf-8",
    )
    (export / "strings_xrefs.jsonl").write_text(
        json.dumps({"string": "WedgeRange", "address": "0x3000", "containing_functions": ["FUN_00001000"]}) + "\n",
        encoding="utf-8",
    )
    (export / "globals.jsonl").write_text(
        json.dumps({"address": "0x4000", "name": "DAT_00004000", "xref_count": 2}) + "\n",
        encoding="utf-8",
    )

    module = _load(ROOT / "tools/ghidra/build_shift_sqlite_index.py", "shift_sqlite_index")
    db_path = tmp_path / "shift.sqlite"
    counts = module.build(export, db_path)
    assert counts == {"functions": 1, "calls": 1, "strings": 1, "globals": 1}

    db = sqlite3.connect(db_path)
    try:
        assert db.execute("SELECT name FROM functions WHERE address='0x1000'").fetchone()[0] == "FUN_00001000"
        assert db.execute("SELECT callee FROM calls WHERE caller='FUN_00001000'").fetchone()[0] == "FUN_00002000"
        assert db.execute("SELECT value FROM strings WHERE containing_function='FUN_00001000'").fetchone()[0] == "WedgeRange"
        assert db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()[0] == "SHIFT.GhidraSQLiteIndex/1"
    finally:
        db.close()
