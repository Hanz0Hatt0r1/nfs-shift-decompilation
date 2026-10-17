#!/usr/bin/env python3
"""Compile and link a supplemental P-code delta with the pinned Linux shards."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


GENERATED = "/* Generated from raw P-code "
REPORT_FORMAT = "NFSShift.NativeLinuxPcodePartialBuild/1"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def split_delta_source(source: Path, output_dir: Path, shard_size: int) -> list[dict]:
    if shard_size < 1:
        raise ValueError("shard size must be positive")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    header: list[str] = []
    shards: list[dict] = []
    writer = None
    current_functions = 0
    total_functions = 0
    try:
        with source.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.startswith(GENERATED):
                    if writer is None:
                        header.append(line)
                    else:
                        writer.write(line)
                    continue
                if writer is None or current_functions == shard_size:
                    if writer is not None:
                        writer.close()
                        shards[-1]["functions"] = current_functions
                    if not header:
                        raise ValueError("delta source has no shared runtime header")
                    index = len(shards)
                    path = output_dir / f"delta-shard-{index:05d}.c"
                    writer = path.open("w", encoding="utf-8")
                    writer.writelines(header)
                    shards.append({"source_file": path.name, "path": str(path), "functions": 0})
                    current_functions = 0
                writer.write(line)
                current_functions += 1
                total_functions += 1
    finally:
        if writer is not None:
            writer.close()
            shards[-1]["functions"] = current_functions
    if total_functions == 0:
        raise ValueError("delta source contains no generated functions")
    return shards


def _compile(compiler: str, source: Path, output: Path) -> None:
    subprocess.run(
        [compiler, "-std=c11", "-O0", "-fPIC", "-c", str(source), "-o", str(output)],
        check=True,
    )


def build(base_dir: Path, delta_source: Path, output_dir: Path, revision: str,
          compiler: str, jobs: int, shard_size: int) -> dict:
    base_report_path = base_dir / "build-report.json"
    base_report = json.loads(base_report_path.read_text(encoding="utf-8"))
    if base_report.get("format") != "REVENGINSTR.PcodeCFunctionShardBuild/1":
        raise ValueError("base build report has an unexpected format")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    base_objects = []
    for shard in base_report.get("shards", []):
        path = base_dir / shard["object_file"]
        if not path.is_file() or digest(path) != shard["object_sha256"]:
            raise ValueError(f"base object does not match its build report: {path}")
        base_objects.append(path)
    base_functions = base_report.get("functions", {}).get("lowerable")
    if not base_objects or type(base_functions) is not int:
        raise ValueError("base build report is missing its shard inventory")

    shard_dir = output_dir / "delta-shards"
    delta_shards = split_delta_source(delta_source, shard_dir, shard_size)
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = []
        for shard in delta_shards:
            source = Path(shard["path"])
            output = source.with_suffix(".o")
            futures.append(pool.submit(_compile, compiler, source, output))
            shard["object_file"] = str(output)
            shard["object_bytes"] = 0
            shard["object_sha256"] = ""
        for future in futures:
            future.result()
    for shard in delta_shards:
        object_path = Path(shard["object_file"])
        shard["object_bytes"] = object_path.stat().st_size
        shard["object_sha256"] = digest(object_path)

    library = output_dir / "libnfs_shift_pcode_partial.so"
    link_arguments = [
        "-shared", "-Wl,-z,defs", "-Wl,-soname,libnfs_shift_pcode_partial.so",
        "-o", str(library), *(str(path) for path in base_objects),
        *(shard["object_file"] for shard in delta_shards), "-lm",
    ]
    subprocess.run([compiler, *link_arguments], check=True)
    nm = shutil.which("nm")
    if nm is None:
        raise ValueError("nm is required to verify the ELF export inventory")
    symbols = subprocess.run([nm, "-D", "--defined-only", str(library)], check=True,
                             capture_output=True, text=True).stdout
    exported = sum(1 for line in symbols.splitlines() if re.search(r"\brvi_[0-9a-f]{8}$", line))
    delta_functions = sum(shard["functions"] for shard in delta_shards)
    expected_exports = base_functions + delta_functions
    if exported != expected_exports:
        raise ValueError(f"ELF exports {exported} P-code functions; expected {expected_exports}")
    compiler_version = subprocess.run([compiler, "--version"], check=True,
                                      capture_output=True, text=True).stdout.splitlines()[0]
    report = {
        "format": REPORT_FORMAT,
        "revenginstr_revision": revision,
        "jobs": jobs,
        "shard_size_limit": shard_size,
        "compiler": {"path": shutil.which(compiler) or compiler, "version": compiler_version,
                     "arguments": ["-std=c11", "-O0", "-fPIC"]},
        "base": {"build_report_sha256": digest(base_report_path),
                 "object_shards": len(base_objects), "lowerable_functions": base_functions},
        "delta": {"source_sha256": digest(delta_source), "source_bytes": delta_source.stat().st_size,
                  "object_shards": len(delta_shards), "functions": delta_functions,
                  "shards": delta_shards},
        "link": {"arguments": link_arguments, "undefined_references": 0},
        "library": {"path": str(library.resolve()), "format": "ELF64 shared object",
                    "machine": "x86-64", "bytes": library.stat().st_size,
                    "sha256": digest(library), "exported_pcode_functions": exported},
    }
    (output_dir / "build-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_shards", type=Path)
    parser.add_argument("delta_source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--revenginstr-revision", required=True)
    parser.add_argument("--cc", default=shutil.which("gcc") or "gcc")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--shard-size", type=int, default=500)
    args = parser.parse_args()
    report = build(args.base_shards, args.delta_source, args.output_dir,
                   args.revenginstr_revision, args.cc, args.jobs, args.shard_size)
    print("base functions:", report["base"]["lowerable_functions"])
    print("delta functions:", report["delta"]["functions"])
    print("ELF exports:", report["library"]["exported_pcode_functions"])
    print("output:", report["library"]["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
