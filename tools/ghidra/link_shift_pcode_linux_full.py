#!/usr/bin/env python3
"""Verify and link the complete frozen SHIFT P-code corpus on Linux."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


BUILD_FORMAT = "REVENGINSTR.PcodeCFunctionShardBuild/1"
REPORT_FORMAT = "NFSShift.NativeLinuxPcodeFullLink/1"
EXPECTED_FUNCTIONS = 41538


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify_inputs(
    build_dir: Path, corpus_manifest_path: Path, address_spaces_path: Path,
    expected_functions: int = EXPECTED_FUNCTIONS,
) -> tuple[dict[str, Any], list[Path]]:
    report_path = build_dir / "build-report.json"
    build_report = _json(report_path)
    manifest = _json(corpus_manifest_path)
    address_spaces = _json(address_spaces_path)
    if build_report.get("format") != BUILD_FORMAT:
        raise ValueError("P-code build report has an unexpected format")
    if manifest.get("format") != "REVENGINSTR.GhidraFunctionInstructionCorpus/1":
        raise ValueError("corpus manifest has an unexpected format")
    if address_spaces.get("format") != "REVENGINSTR.GhidraLanguageAddressSpaces/1":
        raise ValueError("address-space table has an unexpected format")
    if manifest.get("complete") is not True:
        raise ValueError("corpus manifest does not mark the instruction corpus complete")
    source = build_report.get("source")
    if not isinstance(source, dict):
        raise ValueError("P-code build report is missing source identity")
    expected_source = {
        "program": manifest.get("program"),
        "language_id": manifest.get("language_id"),
        "corpus_sha256": manifest.get("output_sha256"),
        "manifest_sha256": _sha256(corpus_manifest_path),
        "address_spaces_sha256": _sha256(address_spaces_path),
    }
    for name, expected in expected_source.items():
        if source.get(name) != expected:
            raise ValueError(f"P-code build source mismatch for {name}")
    if address_spaces.get("language_id") != manifest.get("language_id"):
        raise ValueError("corpus manifest and address-space table language ids differ")
    if manifest.get("exported_function_count") != expected_functions:
        raise ValueError("corpus manifest function count does not match the expected full corpus")
    functions = build_report.get("functions")
    if not isinstance(functions, dict):
        raise ValueError("P-code build report is missing function counts")
    lowerable = functions.get("lowerable")
    if lowerable != expected_functions or functions.get("rejected") != 0:
        raise ValueError(
            f"expected {expected_functions} lowerable functions and no rejects; "
            f"got lowerable={lowerable}, rejected={functions.get('rejected')}"
        )
    compiler = build_report.get("compiler")
    compiler_arguments = compiler.get("arguments") if isinstance(compiler, dict) else None
    if not isinstance(compiler_arguments, list) or "-fPIC" not in compiler_arguments:
        raise ValueError("P-code objects were not built with -fPIC")
    shards = build_report.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("P-code build report has no object shards")
    objects: list[Path] = []
    shard_functions = 0
    for index, shard in enumerate(shards):
        if not isinstance(shard, dict) or shard.get("index") != index:
            raise ValueError("P-code shard inventory is malformed or unordered")
        object_name = shard.get("object_file")
        if not isinstance(object_name, str):
            raise ValueError("P-code shard has no object-file name")
        object_relative_path = Path(object_name)
        if object_relative_path.is_absolute() or ".." in object_relative_path.parts:
            raise ValueError("P-code shard object path must stay inside the build directory")
        object_path = build_dir / object_relative_path
        if not object_path.is_file() or _sha256(object_path) != shard.get("object_sha256"):
            raise ValueError(f"P-code object is missing or has the wrong hash: {object_path}")
        objects.append(object_path)
        shard_functions += shard.get("functions", 0)
    if shard_functions != expected_functions:
        raise ValueError(f"shard inventory covers {shard_functions} functions, expected {expected_functions}")
    return build_report, objects


def link(
    build_dir: Path, corpus_manifest_path: Path, address_spaces_path: Path,
    output_library: Path, compiler: str = "gcc", expected_functions: int = EXPECTED_FUNCTIONS,
) -> dict[str, Any]:
    build_report, objects = verify_inputs(
        build_dir, corpus_manifest_path, address_spaces_path, expected_functions
    )
    compiler_path = shutil.which(compiler)
    nm_path = shutil.which("nm")
    if compiler_path is None or nm_path is None:
        raise ValueError("a C compiler and nm are required")
    if output_library.exists():
        raise ValueError(f"output library already exists: {output_library}")
    output_library.parent.mkdir(parents=True, exist_ok=True)
    temporary_library = output_library.with_name(output_library.name + ".tmp")
    if temporary_library.exists():
        raise ValueError(f"temporary output already exists: {temporary_library}")
    arguments = [
        compiler_path, "-shared", "-Wl,-z,defs", "-Wl,-soname," + output_library.name,
        "-o", str(temporary_library), *(str(path) for path in objects), "-lm",
    ]
    try:
        subprocess.run(arguments, check=True)
        symbols = subprocess.run(
            [nm_path, "-D", "--defined-only", str(temporary_library)],
            check=True, capture_output=True, text=True,
        ).stdout
        exported = sum(
            1 for line in symbols.splitlines()
            if re.search(r"\brvi_[0-9a-f]{8}$", line)
        )
        if exported != expected_functions:
            raise ValueError(f"ELF exports {exported} P-code functions, expected {expected_functions}")
        version = subprocess.run(
            [compiler_path, "--version"], check=True, capture_output=True, text=True,
        ).stdout.splitlines()[0]
        temporary_library.replace(output_library)
    except BaseException:
        temporary_library.unlink(missing_ok=True)
        raise

    return {
        "format": REPORT_FORMAT,
        "build_report_sha256": _sha256(build_dir / "build-report.json"),
        "corpus_manifest_sha256": _sha256(corpus_manifest_path),
        "address_spaces_sha256": _sha256(address_spaces_path),
        "compiler": {"path": compiler_path, "version": version},
        "link_arguments": arguments,
        "object_shards": len(objects),
        "lowerable_functions": build_report["functions"]["lowerable"],
        "library": {
            "path": str(output_library.resolve()),
            "format": "ELF64 shared object",
            "machine": "x86-64",
            "bytes": output_library.stat().st_size,
            "sha256": _sha256(output_library),
            "exported_pcode_functions": exported,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dir", type=Path)
    parser.add_argument("corpus_manifest", type=Path)
    parser.add_argument("address_spaces", type=Path)
    parser.add_argument("output_library", type=Path)
    parser.add_argument("--cc", default="gcc")
    parser.add_argument("--expected-functions", type=int, default=EXPECTED_FUNCTIONS)
    args = parser.parse_args()
    report = link(
        args.build_dir, args.corpus_manifest, args.address_spaces,
        args.output_library, args.cc, args.expected_functions,
    )
    report_path = args.output_library.with_suffix(args.output_library.suffix + ".build-report.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P-code exports:", report["library"]["exported_pcode_functions"])
    print("ELF:", report["library"]["path"])
    print("SHA-256:", report["library"]["sha256"])
    print("report:", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
