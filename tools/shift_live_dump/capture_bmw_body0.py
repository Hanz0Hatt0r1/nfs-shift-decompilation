#!/usr/bin/env python3
"""Collect a bounded Wine/Proton SHIFT runtime evidence bundle for BMW BODY0 work.

The collector deliberately records raw, timestamped process/module/memory-map evidence
without assigning BODY0 semantics to numeric values.  It is intended to be run while
SHIFT.exe is already in a Silverstone + BMW session and to provide a small artifact for
subsequent targeted provenance analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Iterable

FORMAT = "SHIFT.BMWBody0TargetedRuntimeCapture/1"
DEFAULT_PROCESS_NAMES = ("SHIFT.exe", "shift.exe")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _find_pid(explicit_pid: int | None) -> int:
    if explicit_pid is not None:
        proc = Path("/proc") / str(explicit_pid)
        if not proc.exists():
            raise SystemExit(f"PID {explicit_pid} does not exist")
        return explicit_pid

    candidates: list[tuple[int, str]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = _read_text(entry / "comm").strip()
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except (OSError, PermissionError):
            continue
        haystack = f"{comm} {cmdline}".lower()
        if any(name.lower() in haystack for name in DEFAULT_PROCESS_NAMES):
            candidates.append((int(entry.name), f"{comm} {cmdline}".strip()))

    if not candidates:
        raise SystemExit("SHIFT.exe process not found; start the retail game first or pass --pid")
    candidates.sort()
    if len(candidates) > 1:
        rendered = ", ".join(f"{pid}:{desc[:80]}" for pid, desc in candidates)
        raise SystemExit(f"multiple SHIFT.exe candidates found ({rendered}); pass --pid")
    return candidates[0][0]


def _module_identity(pid: int) -> dict[str, object]:
    maps = _read_text(Path("/proc") / str(pid) / "maps").splitlines()
    shift_rows = [line for line in maps if "shift.exe" in line.lower()]
    module_paths: list[str] = []
    for line in shift_rows:
        parts = line.split(maxsplit=5)
        if len(parts) >= 6 and parts[5].startswith("/") and parts[5] not in module_paths:
            module_paths.append(parts[5])

    files = []
    for raw_path in module_paths:
        path = Path(raw_path)
        record: dict[str, object] = {"path": raw_path}
        try:
            stat = path.stat()
            record.update({"size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
            digest = hashlib.md5()
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
            record["md5"] = digest.hexdigest()
        except OSError as exc:
            record["error"] = str(exc)
        files.append(record)

    return {"map_rows": shift_rows, "module_files": files}


def _status(pid: int) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(Path("/proc") / str(pid) / "status").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key in {"Name", "State", "TracerPid", "Threads", "VmRSS", "VmSize"}:
                result[key] = value.strip()
    return result


def _maps_digest(pid: int) -> tuple[str, list[str]]:
    lines = _read_text(Path("/proc") / str(pid) / "maps").splitlines()
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, lines


def _parse_regions(values: Iterable[str]) -> list[tuple[int, int, str]]:
    regions: list[tuple[int, int, str]] = []
    for value in values:
        try:
            address_text, size_text, *name = value.split(":")
            address = int(address_text, 0)
            size = int(size_text, 0)
        except ValueError as exc:
            raise SystemExit(f"invalid --region {value!r}; expected ADDRESS:SIZE[:NAME]") from exc
        if size <= 0 or size > 1024 * 1024:
            raise SystemExit(f"invalid --region size {size}; must be 1..1048576 bytes")
        regions.append((address, size, name[0] if name else f"0x{address:x}"))
    return regions


def _read_region(pid: int, address: int, size: int) -> tuple[bytes | None, str | None]:
    mem_path = Path("/proc") / str(pid) / "mem"
    try:
        with mem_path.open("rb", buffering=0) as fh:
            fh.seek(address)
            data = fh.read(size)
        if len(data) != size:
            return None, f"short read: requested {size}, got {len(data)}"
        return data, None
    except OSError as exc:
        return None, str(exc)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--sample-ms", type=float, default=50.0)
    parser.add_argument(
        "--region",
        action="append",
        default=[],
        metavar="ADDRESS:SIZE[:NAME]",
        help="sample one known virtual-memory region; repeatable; no semantic interpretation is applied",
    )
    parser.add_argument(
        "--mark",
        action="append",
        default=[],
        help="operator phase label recorded in metadata, e.g. idle, throttle, steer",
    )
    args = parser.parse_args()

    if args.duration <= 0 or args.duration > 300:
        parser.error("--duration must be >0 and <=300 seconds")
    if args.sample_ms < 10 or args.sample_ms > 5000:
        parser.error("--sample-ms must be between 10 and 5000 ms")

    pid = _find_pid(args.pid)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    regions = _parse_regions(args.region)

    maps_hash, maps = _maps_digest(pid)
    started_wall = time.time()
    started_mono = time.monotonic_ns()
    metadata = {
        "format": FORMAT,
        "status": "capturing",
        "pid": pid,
        "started_unix": started_wall,
        "started_monotonic_ns": started_mono,
        "duration_seconds": args.duration,
        "sample_interval_ms": args.sample_ms,
        "operator_marks": args.mark,
        "process_status": _status(pid),
        "module_identity": _module_identity(pid),
        "maps_sha256": maps_hash,
        "requested_regions": [
            {"address": f"0x{address:08x}", "size": size, "name": name}
            for address, size, name in regions
        ],
        "semantics": "raw-observation-only",
        "limits": [
            "capture does not prove BODY0 identity or bind-frame provenance by itself",
            "raw virtual addresses are process-session-local unless separately joined to a module/static identity",
            "host sample timing is observational and is not retail scheduler ownership proof",
        ],
    }
    _write_json(out / "capture_metadata.json", metadata)
    (out / "maps.txt").write_text("\n".join(maps) + "\n", encoding="utf-8")

    stop = False

    def _stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    samples_path = out / "samples.jsonl"
    deadline = time.monotonic() + args.duration
    sequence = 0
    read_failures = 0
    with samples_path.open("w", encoding="utf-8") as stream:
        while not stop and time.monotonic() < deadline:
            now_mono = time.monotonic_ns()
            sample: dict[str, object] = {
                "sequence": sequence,
                "monotonic_ns": now_mono,
                "elapsed_ns": now_mono - started_mono,
                "process_status": _status(pid),
                "regions": [],
            }
            if not (Path("/proc") / str(pid)).exists():
                sample["process_exited"] = True
                stream.write(json.dumps(sample, sort_keys=True) + "\n")
                break

            sampled_regions: list[dict[str, object]] = []
            for address, size, name in regions:
                data, error = _read_region(pid, address, size)
                record: dict[str, object] = {
                    "address": f"0x{address:08x}",
                    "size": size,
                    "name": name,
                }
                if data is None:
                    record["error"] = error
                    read_failures += 1
                else:
                    record["sha256"] = hashlib.sha256(data).hexdigest()
                    record["bytes_hex"] = data.hex()
                sampled_regions.append(record)
            sample["regions"] = sampled_regions
            stream.write(json.dumps(sample, sort_keys=True) + "\n")
            stream.flush()
            sequence += 1
            sleep_seconds = args.sample_ms / 1000.0
            time.sleep(sleep_seconds)

    metadata.update(
        {
            "status": "complete",
            "ended_unix": time.time(),
            "samples": sequence,
            "region_read_failures": read_failures,
        }
    )
    _write_json(out / "capture_metadata.json", metadata)

    print(f"capture: {out}")
    print(f"pid: {pid}")
    print(f"samples: {sequence}")
    print(f"region read failures: {read_failures}")
    if not regions:
        print("note: no --region was supplied; process/module/maps timing evidence only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
