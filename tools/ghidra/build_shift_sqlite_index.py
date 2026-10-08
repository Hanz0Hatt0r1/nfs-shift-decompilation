#!/usr/bin/env python3
"""Build a compact SQLite query index from a SHIFT Ghidra evidence export.

Operational accelerator only: this index never promotes semantics by itself.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Iterable


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSONL: {exc}") from exc


def pick(record: dict, *keys, default=None):
    for key in keys:
        if key in record:
            return record[key]
    return default


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def create_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
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
            callsite TEXT,
            kind TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE INDEX calls_caller_idx ON calls(caller);
        CREATE INDEX calls_callee_idx ON calls(callee);
        CREATE INDEX calls_callsite_idx ON calls(callsite);
        CREATE TABLE strings(
            value TEXT,
            address TEXT,
            containing_function TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE INDEX strings_value_idx ON strings(value);
        CREATE INDEX strings_function_idx ON strings(containing_function);
        CREATE TABLE globals(
            address TEXT,
            name TEXT,
            data_type TEXT,
            xref_count INTEGER,
            raw_json TEXT NOT NULL
        );
        CREATE INDEX globals_address_idx ON globals(address);
        CREATE INDEX globals_name_idx ON globals(name);
        """
    )


def insert_functions(db: sqlite3.Connection, path: Path) -> int:
    count = 0
    for rec in read_jsonl(path):
        address = as_text(pick(rec, "address", "entry", "entry_point"))
        if not address:
            continue
        db.execute(
            "INSERT OR REPLACE INTO functions VALUES(?,?,?,?,?,?)",
            (
                address,
                as_text(pick(rec, "name", "function")),
                as_text(pick(rec, "end", "end_address")),
                as_text(pick(rec, "signature")),
                as_text(pick(rec, "mnemonic_fingerprint", "fingerprint")),
                json.dumps(rec, sort_keys=True, ensure_ascii=False),
            ),
        )
        count += 1
    return count


def insert_calls(db: sqlite3.Connection, path: Path) -> int:
    count = 0
    for rec in read_jsonl(path):
        db.execute(
            "INSERT INTO calls VALUES(?,?,?,?,?)",
            (
                as_text(pick(rec, "caller", "from_function", "source_function")),
                as_text(pick(rec, "callee", "to_function", "target_function")),
                as_text(pick(rec, "callsite", "address", "instruction")),
                as_text(pick(rec, "kind", "call_kind", default="direct")),
                json.dumps(rec, sort_keys=True, ensure_ascii=False),
            ),
        )
        count += 1
    return count


def insert_strings(db: sqlite3.Connection, path: Path) -> int:
    count = 0
    for rec in read_jsonl(path):
        owners = pick(rec, "containing_functions", "functions", default=[])
        if not isinstance(owners, list):
            owners = [pick(rec, "containing_function", "function")]
        owners = owners or [None]
        for owner in owners:
            db.execute(
                "INSERT INTO strings VALUES(?,?,?,?)",
                (
                    as_text(pick(rec, "string", "value", "text")),
                    as_text(pick(rec, "address", "string_address")),
                    as_text(owner),
                    json.dumps(rec, sort_keys=True, ensure_ascii=False),
                ),
            )
            count += 1
    return count


def insert_globals(db: sqlite3.Connection, path: Path) -> int:
    count = 0
    for rec in read_jsonl(path):
        db.execute(
            "INSERT INTO globals VALUES(?,?,?,?,?)",
            (
                as_text(pick(rec, "address")),
                as_text(pick(rec, "name", "label")),
                as_text(pick(rec, "data_type", "type")),
                int(pick(rec, "xref_count", default=0) or 0),
                json.dumps(rec, sort_keys=True, ensure_ascii=False),
            ),
        )
        count += 1
    return count


def build(export_dir: Path, output: Path) -> dict:
    inputs = {
        "functions": export_dir / "functions.jsonl",
        "calls": export_dir / "callgraph.jsonl",
        "strings": export_dir / "strings_xrefs.jsonl",
        "globals": export_dir / "globals.jsonl",
    }
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing Ghidra export files: " + ", ".join(missing))

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    db = sqlite3.connect(output)
    try:
        create_schema(db)
        counts = {
            "functions": insert_functions(db, inputs["functions"]),
            "calls": insert_calls(db, inputs["calls"]),
            "strings": insert_strings(db, inputs["strings"]),
            "globals": insert_globals(db, inputs["globals"]),
        }
        db.execute("INSERT INTO metadata VALUES(?,?)", ("format", "SHIFT.GhidraSQLiteIndex/1"))
        db.execute("INSERT INTO metadata VALUES(?,?)", ("schema_version", "1"))
        db.execute("INSERT INTO metadata VALUES(?,?)", ("source_dir", str(export_dir)))
        db.commit()
    finally:
        db.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    counts = build(args.export_dir, args.output)
    print(json.dumps({"format": "SHIFT.GhidraSQLiteIndex/1", "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
