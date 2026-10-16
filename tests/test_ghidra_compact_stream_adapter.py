from __future__ import annotations

import gzip
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools/ghidra/adapt_revenginstr_compact_instruction_stream.py"


def test_adapter_preserves_compressed_stream_rows_except_format(tmp_path: Path) -> None:
    source = tmp_path / "generic.jsonl.gz"
    destination = tmp_path / "shift.jsonl.gz"
    rows = [
        {
            "format": "REVENGINSTR.GhidraCompactInstructionStream/1",
            "kind": "header",
            "program": "sample",
            "executable_md5": None,
            "language_id": "x86:LE:64:default",
            "image_base": "0x00400000",
            "pointer_size": 8,
        },
        {
            "format": "REVENGINSTR.GhidraCompactInstructionStream/1",
            "kind": "instruction",
            "address": "0x00401000",
            "mnemonic": "RET",
            "operands": [],
            "flow_type": "TERMINATOR",
            "flows": [],
        },
    ]
    with gzip.open(source, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")

    subprocess.run(["python3", str(ADAPTER), str(source), str(destination)], check=True)

    with gzip.open(destination, "rt", encoding="utf-8") as stream:
        adapted = [json.loads(line) for line in stream if line.strip()]
    assert adapted == [
        {**rows[0], "format": "SHIFT.GhidraCompactInstructionStream/1"},
        {**rows[1], "format": "SHIFT.GhidraCompactInstructionStream/1"},
    ]
