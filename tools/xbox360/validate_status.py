#!/usr/bin/env python3
"""Validate Xbox 360 migration milestone claims without requiring retail data."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "coordination" / "xbox360_rexglue_status.json"
EXPECTED_GATES = {f"X{i}" for i in range(7)}
STATES = {"not_started", "blocked", "in_progress", "verified"}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "shift.xbox360.rexglue.status.v1":
        errors.append("Unexpected status schema")
    if data.get("strategy") != "xbox360-rexglue-primary":
        errors.append("Primary Xbox strategy is missing")
    if data.get("required_vulkan") != "1.1":
        errors.append("Vulkan 1.1 gate changed without a recorded design decision")

    xex = data.get("input", {})
    xex_hash = xex.get("sha256")
    if xex_hash is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(xex_hash)):
        errors.append("XEX SHA-256 must be a 64-hex-digit hash or null")
    commit = data.get("sdk", {}).get("commit_sha")
    if commit is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", str(commit)):
        errors.append("ReXGlue commit must be a full 40-hex-digit SHA or null")

    gates = data.get("gates", {})
    if set(gates) != EXPECTED_GATES:
        errors.append(f"Expected gates {sorted(EXPECTED_GATES)}, got {sorted(gates)}")
    for key, gate in gates.items():
        state = gate.get("status")
        evidence = gate.get("evidence")
        if state not in STATES:
            errors.append(f"{key}: unsupported status {state!r}")
        if not isinstance(evidence, list) or any(not isinstance(e, str) or not e.strip() for e in evidence):
            errors.append(f"{key}: evidence must be a list of nonempty paths/URLs")
            continue
        if state == "verified" and not evidence:
            errors.append(f"{key}: verified requires evidence")
        if state == "verified" and key == "X0" and (not xex_hash or not xex.get("title_id")):
            errors.append("X0: verified input requires SHA-256 and title ID")
        if state == "verified" and key == "X1" and not commit:
            errors.append("X1: verified recompilation requires a pinned SDK commit")
        if state == "verified" and key not in {"X0", "X1"} and gates.get("X0", {}).get("status") != "verified":
            errors.append(f"{key}: cannot verify Xbox execution without verified retail input")

    return errors


def main() -> int:
    data = json.loads(STATUS.read_text(encoding="utf-8"))
    errors = validate(data)
    for error in errors:
        print("ERROR:", error)
    if errors:
        return 1
    print("Xbox 360/ReXGlue migration ledger valid; no unverified milestone promoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
