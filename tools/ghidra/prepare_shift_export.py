#!/usr/bin/env python3
"""Prepare a Ghidra-version-compatible copy of ShiftEvidenceExporter.java.

Ghidra 12.1 removed DefinedDataIterator.definedStrings(Program).  The exporter
only needs defined string data, so use the stable Listing.getDefinedData()
iterator and Data.hasStringValue() filter instead.
"""
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: prepare_shift_export.py <source.java> <output.java>", file=sys.stderr)
        return 2

    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    text = source_path.read_text(encoding="utf-8")

    old = """            Iterator<Data> it = DefinedDataIterator.definedStrings(currentProgram);\n            while (it.hasNext() && !monitor.isCancelled()) {\n                Data data = it.next();\n"""
    new = """            DataIterator it = listing.getDefinedData(true);\n            while (it.hasNext() && !monitor.isCancelled()) {\n                Data data = it.next();\n                if (!data.hasStringValue()) continue;\n"""

    if old not in text:
        print(
            "error: expected legacy definedStrings() block was not found; "
            "the exporter may already have changed",
            file=sys.stderr,
        )
        return 1

    text = text.replace(old, new, 1)
    text = text.replace("import ghidra.program.util.DefinedDataIterator;\n", "")
    text = text.replace("import java.util.Iterator;\n", "")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
