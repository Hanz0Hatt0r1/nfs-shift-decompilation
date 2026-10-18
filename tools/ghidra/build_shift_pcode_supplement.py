#!/usr/bin/env python3
"""Compile found SHIFT Ghidra instruction exports as a supplemental P-code ELF."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Callable


SHIFT_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
FUNCTION = re.compile(r"\bint rvi_([0-9a-f]{8})\(RviPcodeContext \*ctx\)")
EXPORT = re.compile(r"\b[TtWw]\s+(rvi_[0-9a-f]{8})$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def adapt_row(row: dict, corpus_format: str) -> dict:
    if row.get("format") != SHIFT_FORMAT or row.get("program") != "SHIFT.exe" or row.get("found") is not True:
        raise ValueError("expected a found SHIFT.exe GhidraFunctionInstructions/2 row")
    function = row.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("address"), str):
        raise ValueError("function address is missing")
    adapted = dict(row)
    adapted["format"] = corpus_format
    adapted["resolved_address"] = function["address"]
    return adapted


def runtime_header(runtime_source: str, address: str) -> str:
    marker = f"int rvi_{int(address, 16):08x}(RviPcodeContext *ctx) {{"
    first_line = runtime_source.find("\n") + 1
    function_start = runtime_source.find(marker, first_line)
    if first_line == 0 or function_start < 0:
        raise ValueError("shared lowerer output has no runtime/function boundary")
    return runtime_source[first_line:function_start]


def emit_source(instructions_path: Path, spaces: dict, source_path: Path,
                compile_function: Callable, corpus_format: str,
                lowering_error: type[Exception]) -> dict:
    seen: set[int] = set()
    rejected: Counter[str] = Counter()
    lowered = instruction_count = operation_count = records = 0
    first_address = last_address = None
    source_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = source_path.with_suffix(source_path.suffix + ".tmp")
    with instructions_path.open(encoding="utf-8") as rows, temporary.open("w", encoding="utf-8") as output:
        for line_number, line in enumerate(rows, 1):
            row = json.loads(line)
            records += 1
            try:
                adapted = adapt_row(row, corpus_format)
                address = adapted["function"]["address"]
                numeric_address = int(address, 16)
                if numeric_address in seen:
                    raise ValueError(f"duplicate function address {address}")
                seen.add(numeric_address)
                function_source, operations = compile_function(adapted, spaces, include_runtime=False)
            except lowering_error as error:
                rejected[str(error)] += 1
                continue
            except ValueError as error:
                raise ValueError(f"{instructions_path}:{line_number}: {error}") from error

            if lowered == 0:
                shared_source, _ = compile_function(adapted, spaces)
                output.write(runtime_header(shared_source, address))
            output.write(function_source)
            lowered += 1
            instruction_count += row["instruction_count"]
            operation_count += operations
            first_address = first_address or address
            last_address = address
    temporary.replace(source_path)
    if lowered == 0:
        raise ValueError("no functions could be lowered")
    return {
        "records": records,
        "lowered_functions": lowered,
        "first_function": first_address,
        "last_function": last_address,
        "instructions": instruction_count,
        "pcode_operations": operation_count,
        "rejected_functions": sum(rejected.values()),
        "rejection_reasons": [{"functions": count, "reason": reason}
                              for reason, count in sorted(rejected.items())],
        "source_bytes": source_path.stat().st_size,
        "source_sha256": digest(source_path),
    }


def build(instructions_path: Path, spaces_path: Path, output_dir: Path,
          revision: str, compiler: str) -> dict:
    from revenginstr.pcode.c_lowering import CORPUS_FORMAT, PcodeLoweringError, compile_function

    spaces = json.loads(spaces_path.read_text(encoding="utf-8"))
    if spaces.get("language_id") != "x86:LE:32:default":
        raise ValueError("address spaces are not for SHIFT x86:LE:32:default")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source = output_dir / "supplement.c"
    lowering = emit_source(instructions_path, spaces, source, compile_function,
                           CORPUS_FORMAT, PcodeLoweringError)
    library = output_dir / "libnfs_shift_pcode_supplement.so"
    compiler_path = shutil.which(compiler) or compiler
    subprocess.run([
        compiler_path, "-std=c11", "-O0", "-fPIC", "-shared", "-Wl,-z,defs",
        "-Wl,-soname,libnfs_shift_pcode_supplement.so", "-o", str(library), str(source), "-lm",
    ], check=True)
    nm = shutil.which("nm")
    if nm is None:
        raise ValueError("nm is required to verify the ELF export inventory")
    symbols = subprocess.run([nm, "-D", "--defined-only", str(library)], check=True,
                             capture_output=True, text=True).stdout
    exports = {match.group(1) for line in symbols.splitlines() if (match := EXPORT.search(line))}
    expected = {f"rvi_{match.group(1)}" for match in FUNCTION.finditer(source.read_text(encoding="utf-8"))}
    if exports != expected or len(exports) != lowering["lowered_functions"]:
        raise ValueError(f"ELF exports {len(exports)} P-code functions; expected {lowering['lowered_functions']}")

    version = subprocess.run([compiler_path, "--version"], check=True,
                             capture_output=True, text=True).stdout.splitlines()[0]
    report = {
        "format": "NFSShift.GhidraPcodeSupplementBuild/1",
        "revenginstr_revision": revision,
        "source_inputs": {
            "instructions_sha256": digest(instructions_path),
            "address_spaces_sha256": digest(spaces_path),
        },
        "lowering": lowering,
        "compiler": {"path": compiler_path, "version": version,
                     "arguments": ["-std=c11", "-O0", "-fPIC", "-shared", "-Wl,-z,defs"]},
        "library": {"path": str(library.resolve()), "bytes": library.stat().st_size,
                    "sha256": digest(library), "exported_pcode_functions": len(exports)},
    }
    (output_dir / "build-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("address_spaces", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--revenginstr-revision", required=True)
    parser.add_argument("--cc", default="clang")
    args = parser.parse_args()
    report = build(args.instructions, args.address_spaces, args.output_dir,
                   args.revenginstr_revision, args.cc)
    print(f"lowered {report['lowering']['lowered_functions']} / {report['lowering']['records']} functions")
    print(f"rejected {report['lowering']['rejected_functions']}; ELF exports {report['library']['exported_pcode_functions']}")
    print(report["library"]["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
