#!/usr/bin/env python3
"""Promote BODY writer-bridge candidates only with instruction-range pointer proof.

Input candidates come from ``build_body_writer_bridge_candidates.py`` and prove
only same-function/same-register access patterns. This layer adds an independent
pointer-provenance gate. It never turns an access pattern into a persistent
integrator claim: scheduling, persistence and integration semantics remain
separate evidence requirements.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BodyWriterBridgeProvenance/1"
CANDIDATE_FORMAT = "SHIFT.BodyWriterBridgeCandidates/1"
PROVENANCE_FORMAT = "SHIFT.GhidraBodyPointerProvenance/1"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _address(value: Any, *, field: str) -> int:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field}: expected hexadecimal address string")
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _validate_candidate_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("format") != CANDIDATE_FORMAT:
        raise ValueError(f"expected {CANDIDATE_FORMAT}")
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    result: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidates[{index}] must be an object")
        kind = candidate.get("kind")
        function = candidate.get("function")
        register = candidate.get("base_register")
        if kind not in {"accumulator-to-motion", "motion-to-pose"}:
            raise ValueError(f"candidates[{index}].kind unsupported")
        _address(function, field=f"candidates[{index}].function")
        if not isinstance(register, str) or not register:
            raise ValueError(f"candidates[{index}].base_register missing")
        for key in ("read_evidence", "write_evidence"):
            evidence = candidate.get(key)
            if not isinstance(evidence, list) or not evidence:
                raise ValueError(f"candidates[{index}].{key} must be a non-empty list")
            for evidence_index, row in enumerate(evidence):
                if not isinstance(row, dict):
                    raise ValueError(
                        f"candidates[{index}].{key}[{evidence_index}] must be an object"
                    )
                _address(
                    row.get("instruction"),
                    field=f"candidates[{index}].{key}[{evidence_index}].instruction",
                )
        result.append(candidate)
    return result


def _validate_provenance(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("format") != PROVENANCE_FORMAT:
        raise ValueError(f"expected {PROVENANCE_FORMAT}")
    entries = report.get("entries")
    if not isinstance(entries, list):
        raise ValueError("provenance entries must be a list")

    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entries[{index}] must be an object")
        function = _address(entry.get("function"), field=f"entries[{index}].function")
        start = _address(
            entry.get("instruction_start"), field=f"entries[{index}].instruction_start"
        )
        end = _address(
            entry.get("instruction_end"), field=f"entries[{index}].instruction_end"
        )
        if end < start:
            raise ValueError(f"entries[{index}] instruction range is reversed")
        register = entry.get("base_register")
        identity = entry.get("object_identity")
        evidence_level = entry.get("evidence_level")
        sources = entry.get("sources")
        if not isinstance(register, str) or not register:
            raise ValueError(f"entries[{index}].base_register missing")
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"entries[{index}].object_identity missing")
        if not isinstance(evidence_level, str) or not evidence_level:
            raise ValueError(f"entries[{index}].evidence_level missing")
        if not isinstance(sources, list) or not sources or any(
            not isinstance(source, str) or not source for source in sources
        ):
            raise ValueError(f"entries[{index}].sources must be non-empty strings")
        normalized.append(
            {
                "function": function,
                "instruction_start": start,
                "instruction_end": end,
                "base_register": register.upper(),
                "object_identity": identity,
                "evidence_level": evidence_level,
                "sources": list(sources),
            }
        )
    return normalized


def _candidate_instruction_addresses(candidate: dict[str, Any]) -> list[int]:
    addresses = {
        _address(row["instruction"], field="candidate evidence instruction")
        for key in ("read_evidence", "write_evidence")
        for row in candidate[key]
    }
    return sorted(addresses)


def _matches_for_instruction(
    *,
    function: int,
    register: str,
    instruction: int,
    provenance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for entry in provenance:
        if entry["function"] != function:
            continue
        if entry["base_register"] != register.upper():
            continue
        if not entry["instruction_start"] <= instruction <= entry["instruction_end"]:
            continue
        matches.append(
            {
                "object_identity": entry["object_identity"],
                "evidence_level": entry["evidence_level"],
                "sources": entry["sources"],
                "instruction_range": [
                    f"0x{entry['instruction_start']:08x}",
                    f"0x{entry['instruction_end']:08x}",
                ],
            }
        )
    return matches


def promote_body_writer_bridge_provenance(
    candidate_report: dict[str, Any],
    provenance_report: dict[str, Any],
) -> dict[str, Any]:
    candidates = _validate_candidate_report(candidate_report)
    provenance = _validate_provenance(provenance_report)

    promoted_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        function_int = _address(candidate["function"], field="candidate.function")
        register = str(candidate["base_register"]).upper()
        instruction_addresses = _candidate_instruction_addresses(candidate)
        instruction_provenance = []
        all_body = True
        for instruction in instruction_addresses:
            matches = _matches_for_instruction(
                function=function_int,
                register=register,
                instruction=instruction,
                provenance=provenance,
            )
            body_matches = [match for match in matches if match["object_identity"] == "BODY"]
            body_here = bool(body_matches)
            all_body = all_body and body_here
            instruction_provenance.append(
                {
                    "instruction": f"0x{instruction:08x}",
                    "matches": matches,
                    "body_pointer_proven": body_here,
                }
            )

        promoted = dict(candidate)
        promoted.update(
            {
                "base_register": register,
                "participating_instruction_count": len(instruction_addresses),
                "instruction_pointer_provenance": instruction_provenance,
                "body_pointer_proven": all_body,
                "body_lane_access_pattern_proven": all_body,
                "promotion_status": (
                    "body-lane-access-pattern-proven"
                    if all_body
                    else "candidate-needs-complete-body-pointer-provenance"
                ),
                "persistent_writer_proven": False,
                "integration_semantics_proven": False,
                "frame_ordering_proven": False,
            }
        )
        promoted_candidates.append(promoted)

    by_group: dict[tuple[str, str], dict[str, bool]] = defaultdict(dict)
    for candidate in promoted_candidates:
        key = (str(candidate["function"]), str(candidate["base_register"]))
        by_group[key][str(candidate["kind"])] = bool(
            candidate["body_lane_access_pattern_proven"]
        )

    combined_groups = []
    for (function, register), stages in sorted(by_group.items()):
        if not {
            "accumulator-to-motion",
            "motion-to-pose",
        }.issubset(stages):
            continue
        combined_groups.append(
            {
                "function": function,
                "base_register": register,
                "accumulator_to_motion_body_pattern_proven": stages[
                    "accumulator-to-motion"
                ],
                "motion_to_pose_body_pattern_proven": stages["motion-to-pose"],
                "combined_body_lane_access_pattern_proven": (
                    stages["accumulator-to-motion"] and stages["motion-to-pose"]
                ),
                "persistent_writer_proven": False,
            }
        )

    return {
        "format": FORMAT,
        "candidate_format": CANDIDATE_FORMAT,
        "provenance_format": PROVENANCE_FORMAT,
        "candidate_count": len(promoted_candidates),
        "body_lane_access_pattern_proven_count": sum(
            candidate["body_lane_access_pattern_proven"]
            for candidate in promoted_candidates
        ),
        "unresolved_candidate_count": sum(
            not candidate["body_lane_access_pattern_proven"]
            for candidate in promoted_candidates
        ),
        "combined_bridge_group_count": len(combined_groups),
        "combined_body_lane_access_pattern_proven_count": sum(
            group["combined_body_lane_access_pattern_proven"]
            for group in combined_groups
        ),
        "candidates": promoted_candidates,
        "combined_bridge_groups": combined_groups,
        "scope": {
            "candidate_access_pattern_source": CANDIDATE_FORMAT,
            "instruction_range_pointer_provenance_required": True,
            "all_participating_instructions_require_body_identity": True,
            "non_body_alias_promotes_candidate": False,
            "body_lane_access_pattern_proven_means": (
                "The candidate's p-code-backed lane accesses use one syntactic base register, "
                "and independent instruction-range evidence identifies that register as BODY at "
                "every participating read/write instruction."
            ),
            "persistent_state_writer_proven": False,
            "integration_semantics_proven": False,
            "frame_ordering_proven": False,
            "native_pose_port_ready": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_report", type=Path)
    parser.add_argument("provenance_report", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--require-body-proven-candidate",
        action="store_true",
        help="return non-zero until at least one bridge candidate has complete BODY pointer provenance",
    )
    args = parser.parse_args()

    candidate_report = _load_json(args.candidate_report)
    provenance_report = _load_json(args.provenance_report)
    report = promote_body_writer_bridge_provenance(candidate_report, provenance_report)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"bridge candidates: {report['candidate_count']}")
    print(
        "BODY-proven lane patterns: "
        f"{report['body_lane_access_pattern_proven_count']}"
    )
    print(f"unresolved candidates: {report['unresolved_candidate_count']}")
    print(
        "combined BODY-proven lane patterns: "
        f"{report['combined_body_lane_access_pattern_proven_count']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    if (
        args.require_body_proven_candidate
        and report["body_lane_access_pattern_proven_count"] == 0
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
