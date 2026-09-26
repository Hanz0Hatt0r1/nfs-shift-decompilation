#!/usr/bin/env python3
"""Build and optionally trim an apitrace callset that preserves BMW VB/IB uploads.

The Phase 348 geometry report already contains the exact BMW resource creation
instances. This tool reuses that report, adds the Lock/Unlock/GetDesc calls
belonging to the active creation lifetime, and can call the locally installed
apitrace trim command. It therefore avoids another 74-million-line dump pass.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

FORMAT = "SHIFT.APITRACEBMWBufferPayloadTrim/1"
LOCK_RE = re.compile(
    r"^(?P<call>\d+)\s+(?P<iface>IDirect3D(?:VertexBuffer9|IndexBuffer9))::"
    r"(?P<method>Lock|Unlock|GetDesc)\("
)
THIS_RE = re.compile(r"\bthis\s*=\s*(0x[0-9a-fA-F]+)")
FAKE_MEMCPY_RE = re.compile(r"^(?P<call>\d+)\s+memcpy\s*\(")
CREATE_RE = re.compile(r"^\s*(\d+)\s+IDirect3D(?:VertexBuffer9|IndexBuffer9)::")
PTR_RE = r"(?:NULL|0x[0-9a-fA-F]+)"


def _json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "SHIFT.APITRACEUniqueBMWGeometry/1":
        raise ValueError(
            f"unsupported geometry report format: {data.get('format')!r}"
        )
    return data


def _active_lifecycle_calls(resource: dict) -> list[int]:
    creation = (resource.get("creation") or {}).get("call")
    if not isinstance(creation, int):
        return []
    lifecycle = resource.get("lifecycle") or {}
    values = []
    for key in ("lock_calls", "unlock_calls", "getdesc_calls"):
        for call in lifecycle.get(key) or []:
            if isinstance(call, int) and call > creation:
                values.append(call)
    releases = [
        call for call in lifecycle.get("release_calls") or []
        if isinstance(call, int) and call > creation
    ]
    stop = min(releases) if releases else None
    if stop is not None:
        values = [call for call in values if call < stop]
    return sorted(set(values))


def _resource_rows(report: dict) -> Iterable[tuple[str, dict]]:
    for kind in ("vertex_buffers", "index_buffers"):
        for resource in report.get("resources", {}).get(kind, []):
            yield kind, resource


def _dump_calls(
    trace: Path,
    apitrace: str,
    first: int,
    last: int,
) -> str:
    result = subprocess.run(
        [
            apitrace,
            "dump",
            f"--calls={first}-{last}",
            "--call-nos=true",
            "--arg-names=true",
            str(trace),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def _fake_memcpy_calls_near_unlock(
    trace: Path,
    apitrace: str,
    unlock_call: int,
    window: int = 4,
) -> list[int]:
    first = max(0, unlock_call - max(1, window))
    last = unlock_call + max(1, window)
    text = _dump_calls(trace, apitrace, first, last)
    calls: list[int] = []
    for line in text.splitlines():
        match = FAKE_MEMCPY_RE.match(line)
        if match:
            call = int(match.group("call"))
            if call < unlock_call:
                calls.append(call)
    # D3D9's generated wrapper emits trace::fakeMemcpy immediately before
    # serializing the real Unlock call. Prefer that exact predecessor over
    # unrelated memcpy calls in the bounded window.
    predecessors = [call for call in calls if call == unlock_call - 1]
    return predecessors or ([max(calls)] if calls else [])


def _fallback_lifecycle_calls(
    trace: Path,
    apitrace: str,
    pointer: str,
    creation_call: int,
    window: int,
) -> list[int]:
    text = _dump_calls(
        trace,
        apitrace,
        creation_call,
        creation_call + max(1, window),
    )
    candidates: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = LOCK_RE.match(line)
        if not m:
            continue
        pointer_m = THIS_RE.search(line)
        if not pointer_m or pointer_m.group(1).lower() != pointer.lower():
            continue
        candidates.append((int(m.group("call")), m.group("method")))
    calls = [call for call, _ in candidates]
    if not any(method == "Lock" for _, method in candidates):
        return []
    if not any(method == "Unlock" for _, method in candidates):
        return []
    return sorted(set(calls))


def build_callset(
    report: dict,
    *,
    trace: Path | None = None,
    apitrace: str = "apitrace",
    lock_window: int = 64,
) -> dict:
    callset: set[int] = {
        int(call) for call in report.get("callset", []) if isinstance(call, int)
    }

    resources = []
    fallback_queries = []
    missing_payload_pairs = []
    missing_fake_memcpy = []

    for kind, resource in _resource_rows(report):
        creation = (resource.get("creation") or {}).get("call")
        pointer = resource.get("pointer")
        if not isinstance(creation, int) or not pointer:
            continue

        active = _active_lifecycle_calls(resource)
        if not any(
            call in set(active)
            for call in (resource.get("lifecycle") or {}).get("lock_calls") or []
        ):
            if trace is None:
                fallback_queries.append(
                    {
                        "kind": kind,
                        "pointer": pointer,
                        "creation_call": creation,
                        "reason": "lifecycle-missing-in-report",
                    }
                )
            else:
                active = _fallback_lifecycle_calls(
                    trace, apitrace, str(pointer), creation, lock_window
                )
                if not active:
                    fallback_queries.append(
                        {
                            "kind": kind,
                            "pointer": pointer,
                            "creation_call": creation,
                            "reason": "bounded-lifecycle-lookup-found-no-lock-unlock",
                        }
                    )

        locks = []
        unlocks = []
        lifecycle = resource.get("lifecycle") or {}
        for call in lifecycle.get("lock_calls") or []:
            if isinstance(call, int) and call in active:
                locks.append(call)
        for call in lifecycle.get("unlock_calls") or []:
            if isinstance(call, int) and call in active:
                unlocks.append(call)

        # A fallback query returns only raw call numbers, so classify it by a
        # second bounded mapping over the same call range only when the report
        # lacked lifecycle records entirely.
        if not locks and trace is not None and active:
            text = _dump_calls(
                trace,
                apitrace,
                min(active),
                max(active),
            )
            by_method = {}
            for line in text.splitlines():
                m = LOCK_RE.match(line)
                pointer_m = THIS_RE.search(line)
                if not m or not pointer_m:
                    continue
                if pointer_m.group(1).lower() != str(pointer).lower():
                    continue
                by_method[int(m.group("call"))] = m.group("method")
            locks = [call for call in active if by_method.get(call) == "Lock"]
            unlocks = [
                call for call in active if by_method.get(call) == "Unlock"
            ]

        payload_pair_ok = bool(locks and unlocks)
        if not payload_pair_ok:
            missing_payload_pairs.append(
                {
                    "kind": kind,
                    "pointer": pointer,
                    "creation_call": creation,
                    "lock_calls": sorted(locks),
                    "unlock_calls": sorted(unlocks),
                }
            )

        fake_memcpy_calls: dict[int, list[int]] = {}
        for unlock_call in unlocks:
            if trace is None:
                candidates: list[int] = []
            else:
                candidates = _fake_memcpy_calls_near_unlock(
                    trace, apitrace, unlock_call
                )
            fake_memcpy_calls[unlock_call] = candidates
            if not candidates:
                missing_fake_memcpy.append(
                    {
                        "kind": kind,
                        "pointer": pointer,
                        "creation_call": creation,
                        "unlock_call": unlock_call,
                    }
                )
            callset.update(candidates)

        callset.add(creation)
        callset.update(active)
        resources.append(
            {
                "kind": kind,
                "pointer": pointer,
                "creation_call": creation,
                "lock_calls": sorted(locks),
                "unlock_calls": sorted(unlocks),
                "fake_memcpy_calls_by_unlock": {
                    str(k): sorted(v) for k, v in sorted(fake_memcpy_calls.items())
                },
                "active_lifecycle_calls": sorted(active),
                "payload_pair_observed": payload_pair_ok,
            }
        )

    return {
        "format": FORMAT,
        "resource_count": len(resources),
        "resources": resources,
        "callset": sorted(callset),
        "callset_count": len(callset),
        "fallback_queries": fallback_queries,
        "missing_payload_pairs": missing_payload_pairs,
        "missing_fake_memcpy": missing_fake_memcpy,
        "ready_for_payload_trim": (
            len(resources) == 7
            and not fallback_queries
            and not missing_payload_pairs
            and not missing_fake_memcpy
        ),
    }


def write_plan(report: dict, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    plan = build_callset(report)
    (output / "bmw_buffer_payload_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "bmw_buffer_payload_callset.txt").write_text(
        "\n".join(str(call) for call in plan["callset"]) + "\n",
        encoding="utf-8",
    )
    return plan


def trim(
    trace: Path,
    output: Path,
    callset: list[int],
    apitrace: str,
) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    callset_file = output.parent / "bmw_buffer_payload_callset.txt"
    callset_file.write_text(
        "\n".join(str(call) for call in callset) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            apitrace,
            "trim",
            f"--calls=@{callset_file}",
            "-o",
            str(output),
            str(trace),
        ],
        check=True,
    )
    return str(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("geometry_report", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--apitrace", default="apitrace")
    parser.add_argument("--lock-window", type=int, default=64)
    parser.add_argument("--trim", action="store_true")
    parser.add_argument(
        "--allow-missing-payload-pairs",
        action="store_true",
        help="write the plan even if a target resource has no bounded Lock/Unlock pair",
    )
    args = parser.parse_args(argv)

    trace = args.trace.expanduser().resolve()
    report = _json(args.geometry_report.expanduser().resolve())
    output = args.output_dir.expanduser().resolve()

    plan = build_callset(
        report,
        trace=trace,
        apitrace=args.apitrace,
        lock_window=max(1, args.lock_window),
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "bmw_buffer_payload_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    callset_file = output / "bmw_buffer_payload_callset.txt"
    callset_file.write_text(
        "\n".join(str(call) for call in plan["callset"]) + "\n",
        encoding="utf-8",
    )

    if plan["fallback_queries"]:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "could-not-resolve-lifecycle-calls",
                    "fallback_queries": plan["fallback_queries"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    if (plan["missing_payload_pairs"] or plan["missing_fake_memcpy"]) and not args.allow_missing_payload_pairs:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "missing-active-lock-unlock-pair",
                    "missing_payload_pairs": plan["missing_payload_pairs"],
                    "missing_fake_memcpy": plan["missing_fake_memcpy"],
                    "callset": str(callset_file),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    trim_output = None
    if args.trim:
        trim_path = output / "bmw_buffer_payload.trace"
        trim_output = trim(trace, trim_path, plan["callset"], args.apitrace)

    result = {
        "format": FORMAT,
        "status": "ready" if plan["ready_for_payload_trim"] else "partial",
        "trace": str(trace),
        "geometry_report": str(args.geometry_report.expanduser().resolve()),
        "output_dir": str(output),
        "callset_count": plan["callset_count"],
        "trim_output": trim_output,
        "resources": plan["resources"],
    }
    (output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
