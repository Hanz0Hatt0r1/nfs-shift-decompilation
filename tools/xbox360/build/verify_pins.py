#!/usr/bin/env python3
"""Verify the Xbox 360 SHIFT ReXGlue build pin ledger.

Reads tools/xbox360/build/pins.json, locates each recorded artifact on this
host, recomputes its SHA-256 and compares it with the recorded value.

Exit codes:
    0  every artifact that could be located matched its pin
       (missing artifacts are reported as "unavailable" and do NOT fail)
    1  at least one located artifact did not match its pin
    2  the ledger itself could not be read or failed schema validation

Usage:
    python3 tools/xbox360/build/verify_pins.py
    python3 tools/xbox360/build/verify_pins.py --json
    python3 tools/xbox360/build/verify_pins.py --explain plugin_native_vulkan
    python3 tools/xbox360/build/verify_pins.py --require runtime,plugin_native_vulkan

The point of the tool is that "which SDK commit and which plugin source commit
produced this .so" is answerable from the ledger plus one hash check, instead
of from 96 run directories that all share one unlabelled sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "pins.json"

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STATUS_VALUES = {"verified", "unverified", "unavailable", "mismatch"}
# Keys whose value must be a 64-char lowercase hex digest when non-null.
SHA_KEYS = ("sha256", "xex_sha256")
# Artifacts that live in the run-dir bin/ tree; searched by these glob names.
SEARCH_NAMES = {
    "runtime": ("librexruntime.so",),
    "host": ("nfs_shift",),
    "plugin_native_vulkan": ("librexgpu-shift-native.so",),
    "plugin_xenos": ("librexgpu-xenos.so",),
}


class LedgerError(Exception):
    """The ledger is unreadable or violates the documented schema."""


def load_ledger(path: Path | None = None) -> dict:
    path = path or LEDGER
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"pin ledger not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"pin ledger is not valid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise LedgerError("pin ledger must be a JSON object")
    for key in ("_schema_version", "title", "sdk", "artifacts", "recipe"):
        if key not in data:
            raise LedgerError(f"pin ledger is missing required key {key!r}")
    if not isinstance(data["artifacts"], dict) or not data["artifacts"]:
        raise LedgerError("pin ledger 'artifacts' must be a non-empty object")

    _validate_artifact_entry("title", data["title"])
    for key in ("fork_commit_status", "fork_commit"):
        if key not in data["sdk"]:
            raise LedgerError(f"pin ledger 'sdk' is missing required key {key!r}")
    for name, entry in data["artifacts"].items():
        if not isinstance(entry, dict):
            raise LedgerError(f"artifact {name!r} must be an object")
        for key in ("name", "kind", "sha256", "status"):
            if key not in entry:
                raise LedgerError(f"artifact {name!r} is missing required key {key!r}")
        _validate_artifact_entry(name, entry)
    return data


def _validate_artifact_entry(name: str, entry: dict) -> None:
    for key in SHA_KEYS:
        value = entry.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not SHA_RE.match(value):
            raise LedgerError(
                f"{name!r}.{key} is not a 64-character lowercase hex digest: {value!r}"
            )
    status = entry.get("status")
    if status is not None and status not in STATUS_VALUES:
        raise LedgerError(
            f"{name!r}.status is {status!r}, expected one of {sorted(STATUS_VALUES)}"
        )


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def find_artifact(name: str, entry: dict, search_root: Path | None) -> Path | None:
    """Locate one artifact. Explicit paths win; otherwise search run dirs."""
    for key in ("path", "producer_path", "sample_path"):
        raw = entry.get(key)
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_file():
                return candidate
    if search_root is None or not search_root.is_dir():
        return None
    for candidate_name in SEARCH_NAMES.get(name, (entry.get("name") or name,)):
        for candidate in sorted(search_root.glob(f"*/bin/{candidate_name}")):
            if candidate.is_file():
                return candidate
    return None


def check_artifact(
    name: str, entry: dict, search_root: Path | None = None
) -> dict:
    """Return a result dict; never raises for a missing or unreadable file."""
    pinned = entry.get("sha256")
    result = {
        "artifact": name,
        "name": entry.get("name"),
        "kind": entry.get("kind"),
        "pinned_sha256": pinned,
        "path": None,
        "observed_sha256": None,
        "result": "unavailable",
        "message": "",
    }
    try:
        located = find_artifact(name, entry, search_root)
    except OSError as exc:  # pragma: no cover - defensive
        result["message"] = f"lookup failed: {exc}"
        return result

    if located is None:
        result["message"] = (
            "artifact not present on this host; pin not re-checked "
            "(reported unavailable, not a failure)"
        )
        return result

    result["path"] = str(located)
    try:
        observed = sha256_file(located)
    except OSError as exc:
        result["message"] = f"could not read artifact: {exc}"
        return result

    result["observed_sha256"] = observed
    if observed == pinned:
        result["result"] = "match"
        result["message"] = "sha256 matches the pin"
    else:
        result["result"] = "mismatch"
        result["message"] = "sha256 DOES NOT match the pin"
    return result


def verify(ledger: dict, search_root: Path | None = None,
           require: list[str] | None = None) -> dict:
    results = [
        check_artifact(name, entry, search_root)
        for name, entry in ledger["artifacts"].items()
    ]

    failures = [r for r in results if r["result"] == "mismatch"]
    unavailable = [r for r in results if r["result"] == "unavailable"]
    required_missing = []
    for name in require or []:
        match = next((r for r in results if r["artifact"] == name), None)
        if match is None:
            required_missing.append(name)
        elif match["result"] != "match":
            failures.append(
                {
                    "artifact": name,
                    "result": "mismatch",
                    "message": "required artifact did not verify",
                    "pinned_sha256": match["pinned_sha256"],
                    "observed_sha256": match["observed_sha256"],
                    "path": match["path"],
                    "name": match["name"],
                    "kind": match["kind"],
                }
            )

    # Pins that are asserted but explicitly unverified stay visible.
    unverified_pins = []
    sdk = ledger["sdk"]
    if sdk.get("fork_commit_status") != "verified":
        unverified_pins.append(
            f"sdk.fork_commit={sdk.get('fork_commit')} ({sdk.get('fork_commit_status')})"
        )
    for name, entry in ledger["artifacts"].items():
        if entry.get("status") != "verified":
            unverified_pins.append(
                f"{name}.sha256 status={entry.get('status')}"
            )
        if entry.get("built_from_commit_status") not in (None, "verified"):
            unverified_pins.append(
                f"{name}.built_from_commit={entry.get('built_from_commit')} "
                f"({entry.get('built_from_commit_status')})"
            )
    if ledger["title"].get("xex_status") != "verified":
        unverified_pins.append(
            f"title.xex_sha256 status={ledger['title'].get('xex_status')}"
        )

    ok = not failures
    return {
        "ledger": str(LEDGER),
        "exit_code": 0 if ok else 1,
        "ok": ok,
        "checked": len(results),
        "matched": sum(1 for r in results if r["result"] == "match"),
        "unavailable": len(unavailable),
        "mismatched": sum(1 for r in results if r["result"] == "mismatch"),
        "results": results,
        "unverified_pins": unverified_pins,
        "required_missing": required_missing,
    }


def explain(ledger: dict, artifact: str) -> str:
    entry = ledger["artifacts"].get(artifact)
    if entry is None:
        known = ", ".join(sorted(ledger["artifacts"]))
        return f"unknown artifact {artifact!r}; known artifacts: {known}"
    lines = [
        f"artifact     : {artifact} ({entry.get('name')})",
        f"kind         : {entry.get('kind')}",
        f"sha256       : {entry.get('sha256')} [{entry.get('status')}]",
        f"produced by  : {entry.get('built_from_commit') or 'unknown'} "
        f"[{entry.get('built_from_commit_status')}]",
    ]
    if entry.get("plugin_source_commit") or entry.get("plugin_source_commit_status"):
        lines.append(
            f"plugin source: {entry.get('plugin_source_commit') or 'unknown'} "
            f"[{entry.get('plugin_source_commit_status')}]"
        )
    sdk = ledger["sdk"]
    lines.append(f"sdk fork     : {sdk.get('fork_repository')} @ {sdk.get('fork_commit')} "
                 f"[{sdk.get('fork_commit_status')}]")
    for key in ("path", "producer_path", "sample_path", "second_sample_path"):
        if entry.get(key):
            lines.append(f"{key:13s}: {entry[key]}")
    if entry.get("note"):
        lines.append(f"note         : {entry['note']}")
    return "\n".join(lines)


def _human(report: dict) -> str:
    lines = [
        f"pin ledger: {report['ledger']}",
        f"checked {report['checked']} artifact(s): "
        f"{report['matched']} matched, "
        f"{report['unavailable']} unavailable, "
        f"{report['mismatched']} mismatched",
        "",
    ]
    width = max((len(r["artifact"]) for r in report["results"]), default=8)
    for r in report["results"]:
        icon = {"match": "OK  ", "mismatch": "FAIL", "unavailable": "--  "}[r["result"]]
        lines.append(f"  [{icon}] {r['artifact']:<{width}}  {r['message']}")
        if r["path"]:
            lines.append(f"           path     : {r['path']}")
            lines.append(f"           pinned   : {r['pinned_sha256']}")
            lines.append(f"           observed : {r['observed_sha256']}")
    if report["unverified_pins"]:
        lines.append("")
        lines.append("Explicitly UNVERIFIED pins (do not cite as fact):")
        for item in report["unverified_pins"]:
            lines.append(f"  ? {item}")
    if report["required_missing"]:
        lines.append("")
        lines.append(f"Required artifacts absent from the ledger: "
                     f"{', '.join(report['required_missing'])}")
    lines.append("")
    lines.append(
        "RESULT: PASS - every located artifact matched its pin"
        if report["ok"]
        else "RESULT: FAIL - a located artifact did not match its pin"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Xbox 360 SHIFT ReXGlue build pins."
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--ledger", type=Path, default=None,
                        help=f"pin ledger path (default {LEDGER})")
    parser.add_argument("--search-root", type=Path, default=None,
                        help="root whose */bin/ directories are searched for "
                             "missing artifacts (e.g. /home/pes/work)")
    parser.add_argument("--require", default="",
                        help="comma-separated artifact names that MUST verify")
    parser.add_argument("--explain", metavar="ARTIFACT", default=None,
                        help="print provenance for one artifact and exit")
    args = parser.parse_args(argv)

    try:
        ledger = load_ledger(args.ledger)
    except LedgerError as exc:
        if args.json:
            print(json.dumps({"ok": False, "exit_code": 2,
                              "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.explain:
        print(explain(ledger, args.explain))
        return 0

    require = [part.strip() for part in args.require.split(",") if part.strip()]
    report = verify(ledger, search_root=args.search_root, require=require)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_human(report))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
