#!/usr/bin/env python3
"""Acquire the merged P1B helper-setter frontier from a pinned Ghidra instruction stream."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1"
INPUT_FORMAT = "SHIFT.GhidraCompactInstructionStream/1"
PROGRAM = "SHIFT.exe"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
LANGUAGE_ID = "x86:LE:32:default"
IMAGE_BASE = "0x00400000"
POINTER_SIZE = 4
REGISTERS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
RUNNER = ROOT / "tools/ghidra/run_p1b_manager374_helper_setter_retail_frontier.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def load_runner():
    spec = importlib.util.spec_from_file_location("_p1b_helper_setter_retail_runner", RUNNER)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load merged helper-setter runner: {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def parse_address(value: object, *, context: str) -> int:
    require(isinstance(value, str), f"{context}: address must be a string")
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    require(bool(text), f"{context}: empty address")
    try:
        return int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{context}: invalid address {value!r}") from exc


def validate_header(header: dict) -> None:
    require(header.get("format") == INPUT_FORMAT, "instruction stream format drift")
    require(header.get("kind") == "header", "first row is not an instruction stream header")
    require(header.get("program") == PROGRAM, "unexpected Ghidra program")
    require(str(header.get("executable_md5", "")).lower() == RETAIL_MD5, "unexpected executable MD5")
    require(header.get("language_id") == LANGUAGE_ID, "unexpected Ghidra language")
    require(str(header.get("image_base", "")).lower() == IMAGE_BASE, "unexpected image base")
    require(header.get("pointer_size") == POINTER_SIZE, "unexpected pointer size")


def is_indirect_call_operand(operand: str) -> bool:
    text = operand.strip().lower()
    if "[" in text or "]" in text or "*" in text:
        return True
    return text in REGISTERS


def canonical_operands(mnemonic: str, operands: list[str], flows: list[str]) -> str:
    rendered = ",".join(str(item).strip() for item in operands)
    if mnemonic == "call" and len(operands) == 1 and len(flows) == 1:
        if not is_indirect_call_operand(str(operands[0])):
            # Ghidra often renders a direct target as FUN_XXXXXXXX.  The merged
            # probes consume a numeric direct target, so use the exact flow
            # address rather than attempting to parse a symbol name.
            return str(flows[0]).strip()
    return rendered


def read_stream(path: Path) -> tuple[dict, list[tuple[int, str, str]], str]:
    rows: list[tuple[int, str, str]] = []
    canonical_hash = hashlib.sha256()
    previous_address: int | None = None
    header: dict | None = None

    with open_text(path) as stream:
        for line_no, raw in enumerate(stream, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            require(isinstance(obj, dict), f"{path}:{line_no}: row must be an object")
            require(obj.get("format") == INPUT_FORMAT, f"{path}:{line_no}: format drift")

            if header is None:
                validate_header(obj)
                header = obj
                continue

            require(obj.get("kind") == "instruction", f"{path}:{line_no}: unexpected row kind")
            address = parse_address(obj.get("address"), context=f"{path}:{line_no}")
            require(previous_address is None or address > previous_address,
                    f"{path}:{line_no}: instruction addresses are not strictly increasing")
            previous_address = address

            mnemonic_raw = obj.get("mnemonic")
            require(isinstance(mnemonic_raw, str) and mnemonic_raw.strip(),
                    f"{path}:{line_no}: missing mnemonic")
            mnemonic = mnemonic_raw.strip().lower()

            operands = obj.get("operands")
            flows = obj.get("flows")
            require(isinstance(operands, list) and all(isinstance(x, str) for x in operands),
                    f"{path}:{line_no}: operands must be a string list")
            require(isinstance(flows, list) and all(isinstance(x, str) for x in flows),
                    f"{path}:{line_no}: flows must be a string list")
            operand_text = canonical_operands(mnemonic, operands, flows)
            rows.append((address, mnemonic, operand_text))
            canonical_hash.update(f"{address:08x}|{mnemonic}|{operand_text}\n".encode("utf-8"))

    require(header is not None, "instruction stream header missing")
    require(bool(rows), "instruction stream contains no instructions")
    return header, rows, canonical_hash.hexdigest()


def acquire(path: Path) -> tuple[dict, dict, dict[str, dict]]:
    header, rows, canonical_sha256 = read_stream(path)
    runner = load_runner()
    require(getattr(runner, "FORMAT", None) == "SHIFT.P1B.Manager374HelperSetterRetailFrontier/1",
            "merged helper-setter runner format drift")
    aggregate, results = runner.run_rows(rows)

    # The shared probe composition is useful on the pinned Ghidra listing, but
    # it is not the raw-PE objdump execution path.  Rewrite only the acquisition
    # authority/gates that would otherwise overstate what happened in this run.
    authority = dict(aggregate.get("authority", {}))
    authority.update({
        "acquisition_source": INPUT_FORMAT,
        "ghidra_program": header["program"],
        "ghidra_executable_md5": header["executable_md5"].lower(),
        "ghidra_language_id": header["language_id"],
        "ghidra_image_base": header["image_base"].lower(),
        "ghidra_pointer_size": header["pointer_size"],
        "known_retail_sha256_cross_pin": RETAIL_SHA256,
        "raw_executable_sha256_verified_in_this_run": False,
        "canonical_instruction_stream_sha256": canonical_sha256,
        "decoded_instruction_count": len(rows),
        "single_shared_instruction_stream": True,
    })
    aggregate["authority"] = authority
    adjudication = dict(aggregate.get("adjudication", {}))
    adjudication["retail_helper_setter_probe_bundle_execution_complete"] = False
    adjudication["retail_helper_setter_candidate_frontier_composed"] = False
    adjudication["ghidra_helper_setter_probe_bundle_execution_complete"] = True
    adjudication["ghidra_helper_setter_candidate_frontier_composed"] = True
    aggregate["adjudication"] = adjudication

    wrapper = {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": authority,
        "source_stream": {
            "path_name": path.name,
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "canonical_instruction_stream_sha256": canonical_sha256,
            "instruction_count": len(rows),
        },
        "frontier_format": aggregate["format"],
        "surface": aggregate["surface"],
        "adjudication": adjudication,
        "limits": [
            "This is a Ghidra-listing acquisition of the merged helper-setter probes, not a raw-PE objdump execution of the retail frontier runner.",
            "The Ghidra executable MD5 is pinned to the known PC retail 1.02 image and cross-referenced to its known SHA-256, but raw executable bytes are not re-hashed in this run.",
            "Ghidra flow metadata is used only to normalize direct CALL symbol operands to numeric target addresses; register/memory indirect calls remain indirect.",
            "All global helper/root identity and final P1.3 gates remain fail-closed until authoritative candidate/open-boundary adjudication."
        ],
        "next_step": "Compare this Ghidra frontier with a raw-retail bundle run when SHIFT.exe is available; classify every positive candidate/open boundary before promoting any helper/non-vtable setter or final identity gate."
    }
    return wrapper, aggregate, results


def write_output(out_dir: Path, wrapper: dict, aggregate: dict, results: dict[str, dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ghidra_acquisition.json").write_text(
        json.dumps(wrapper, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "frontier.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    component_authority = wrapper["authority"]
    for name, payload in results.items():
        enriched = dict(payload)
        enriched["authority"] = component_authority
        (out_dir / f"{name}.json").write_text(
            json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_stream", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    try:
        wrapper, aggregate, results = acquire(args.instruction_stream)
    except ValueError as exc:
        parser.error(str(exc))
    if args.out_dir:
        write_output(args.out_dir, wrapper, aggregate, results)
        print(args.out_dir / "ghidra_acquisition.json")
    else:
        print(json.dumps(wrapper, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
