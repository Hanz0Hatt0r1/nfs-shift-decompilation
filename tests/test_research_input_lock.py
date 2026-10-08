import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "coordination/research_inputs.lock.json"


def _load():
    return json.loads(LOCK.read_text(encoding="utf-8"))


def test_research_input_lock_has_known_authoritative_retail_hash():
    payload = _load()
    assert payload["format"] == "SHIFT.ResearchInputLock/1"
    rows = {row["logical_name"]: row for row in payload["locked_inputs"]}
    assert rows["SHIFT.exe"]["sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert rows["SHIFT.exe"]["semantic_authority"] is True


def test_decompiler_source_is_hash_locked_but_not_machine_authority():
    payload = _load()
    rows = {row["logical_name"]: row for row in payload["locked_inputs"]}
    source = rows["SHIFT.exe.c"]
    assert source["sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert source["semantic_authority"] is False
    assert source["machine_transfer_must_adjudicate"] is True


def test_unhashed_navigation_indexes_cannot_be_semantic_authority():
    payload = _load()
    for row in payload["navigation_inputs"]:
        if not row["hash_locked"]:
            assert row["semantic_authority"] is False


def test_storage_hints_are_never_authority():
    payload = _load()
    assert payload["storage_hints"]
    assert all(row["authoritative"] is False for row in payload["storage_hints"])
