#!/usr/bin/env python3
"""Cross-check the source/Ghidra ABI immediately above FUN_00770e80.

This tool consumes the known recovered SHIFT.exe.c snapshot plus the structured
Ghidra export. It freezes only source-visible argument storage/forwarding,
object offsets, direct-call counts and bounded upstream topology. It does not
assign physical units or semantic names to the two 64-bit caller channels.

The source hash is pinned so source-text matching cannot silently drift onto a
different decompilation snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.OuterUpdateCallsiteStatic/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
OUTER_UPDATE = "0x00770e80"
DIRECT_CALLERS = ("0x00794a30", "0x0079b2d0")
UPSTREAM_BATCH = "0x00713050"
UPSTREAM_OWNER = "0x00715380"

SOURCE_FUNCTIONS = {
    OUTER_UPDATE: "FUN_00770e80",
    DIRECT_CALLERS[0]: "FUN_00794a30",
    DIRECT_CALLERS[1]: "FUN_0079b2d0",
    UPSTREAM_BATCH: "FUN_00713050",
    UPSTREAM_OWNER: "FUN_00715380",
}

SHARED_POST_OUTER_CALLS = (
    "FUN_0078ef00",
    "FUN_00793ca0",
    "FUN_007aa750",
    "FUN_007851d0",
)


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _line_number(source: str, position: int) -> int:
    return source.count("\n", 0, position) + 1


def _extract_function(source: str, name: str) -> tuple[str, int, int]:
    # Definitions in the recovered source begin at column zero. Calls are
    # indented, so anchoring at a non-whitespace line start excludes callsites.
    pattern = re.compile(rf"(?m)^[^\s\n][^\n]*\b{re.escape(name)}\s*\(")
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(
            f"{name}: expected exactly one function definition; found {len(matches)}"
        )
    start = matches[0].start()
    brace = source.find("{", matches[0].end())
    if brace < 0:
        raise ValueError(f"{name}: opening brace not found")

    depth = 0
    end = None
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError(f"{name}: closing brace not found")
    return source[start:end], start, end


def _require_fragment(function: str, compact_body: str, fragment: str) -> None:
    if _compact(fragment) not in compact_body:
        raise ValueError(f"{function}: required source fragment missing: {fragment}")


def _require_order(function: str, compact_body: str, fragments: Iterable[str]) -> None:
    positions = []
    cursor = 0
    for fragment in fragments:
        token = _compact(fragment)
        position = compact_body.find(token, cursor)
        if position < 0:
            raise ValueError(
                f"{function}: required ordered source fragment missing: {fragment}"
            )
        positions.append(position)
        cursor = position + len(token)
    if positions != sorted(positions):
        raise ValueError(f"{function}: required source order not preserved")


def _function_line(source: str, function_start: int) -> int:
    return _line_number(source, function_start)


def _fragment_line(source: str, function_start: int, body: str, fragment: str) -> int:
    compact_fragment = _compact(fragment)
    compact_chars: list[str] = []
    source_positions: list[int] = []
    for index, char in enumerate(body):
        if char.isspace():
            continue
        compact_chars.append(char)
        source_positions.append(function_start + index)
    compact_body = "".join(compact_chars)
    position = compact_body.find(compact_fragment)
    if position < 0:
        raise ValueError(f"source fragment line lookup failed: {fragment}")
    return _line_number(source, source_positions[position])


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def build_outer_update_callsite_contract(
    source_path: Path,
    ghidra_root: Path,
    *,
    expected_source_sha256: str = SOURCE_SHA256,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != expected_source_sha256:
        raise ValueError(
            "unexpected SHIFT.exe.c SHA-256: "
            f"expected {expected_source_sha256}, got {source_hash}"
        )
    source = source_bytes.decode("utf-8", errors="strict")

    required = ("binary.json", "functions.jsonl", "callgraph.jsonl", "switches.jsonl")
    missing = [name for name in required if not (ghidra_root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    binary = json.loads((ghidra_root / "binary.json").read_text(encoding="utf-8"))
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError(
            "unexpected Ghidra executable MD5: "
            f"expected {PE_MD5}, got {binary.get('executable_md5')}"
        )

    functions = {
        row["address"]: row
        for row in read_jsonl(ghidra_root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }
    missing_functions = [address for address in SOURCE_FUNCTIONS if address not in functions]
    if missing_functions:
        raise ValueError(
            "required function(s) absent from Ghidra export: "
            + ", ".join(missing_functions)
        )

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(ghidra_root / "callgraph.jsonl"):
        if row.get("indirect") is not False:
            continue
        source_function = row.get("from_function")
        target = row.get("to")
        if not isinstance(source_function, str) or not isinstance(target, str):
            continue
        outgoing[source_function].append(row)
        incoming[target].append(row)

    actual_callers = sorted(
        {row["from_function"] for row in incoming.get(OUTER_UPDATE, [])}
    )
    if actual_callers != sorted(DIRECT_CALLERS):
        raise ValueError(
            f"{OUTER_UPDATE}: direct caller set changed: expected "
            f"{sorted(DIRECT_CALLERS)}, got {actual_callers}"
        )
    for caller in DIRECT_CALLERS:
        matches = [row for row in outgoing.get(caller, []) if row.get("to") == OUTER_UPDATE]
        if len(matches) != 1:
            raise ValueError(
                f"{caller}: expected exactly one direct Ghidra call to {OUTER_UPDATE}; "
                f"found {len(matches)}"
            )

    upstream_calls = [
        row for row in outgoing.get(UPSTREAM_BATCH, []) if row.get("to") == DIRECT_CALLERS[0]
    ]
    if len(upstream_calls) != 3:
        raise ValueError(
            f"{UPSTREAM_BATCH}: expected exactly three direct calls to {DIRECT_CALLERS[0]}; "
            f"found {len(upstream_calls)}"
        )
    owner_calls = [
        row for row in outgoing.get(UPSTREAM_OWNER, []) if row.get("to") == UPSTREAM_BATCH
    ]
    if len(owner_calls) != 1:
        raise ValueError(
            f"{UPSTREAM_OWNER}: expected exactly one direct call to {UPSTREAM_BATCH}; "
            f"found {len(owner_calls)}"
        )
    second_caller_incoming = incoming.get(DIRECT_CALLERS[1], [])
    if second_caller_incoming:
        raise ValueError(
            f"{DIRECT_CALLERS[1]}: expected no direct incoming call in this export; "
            f"found {len(second_caller_incoming)}"
        )

    switches = [
        row
        for row in read_jsonl(ghidra_root / "switches.jsonl")
        if row.get("function") == DIRECT_CALLERS[1]
    ]
    if len(switches) != 1 or switches[0].get("status") != "computed-jump-candidate":
        raise ValueError(
            f"{DIRECT_CALLERS[1]}: expected exactly one computed-jump candidate"
        )

    extracted: dict[str, dict[str, Any]] = {}
    for address, name in SOURCE_FUNCTIONS.items():
        body, start, end = _extract_function(source, name)
        extracted[address] = {
            "name": name,
            "body": body,
            "compact": _compact(body),
            "start": start,
            "end": end,
            "line": _function_line(source, start),
        }

    caller_a = extracted[DIRECT_CALLERS[0]]
    a = caller_a["compact"]
    a_store_b = "*(ulonglong *)((int)this + 0x1ab0) = CONCAT44(param_4,param_3);"
    a_store_a = "*(ulonglong *)((int)this + 0x1aa8) = CONCAT44(param_2,param_1);"
    a_gate_1 = "param_5 != '\\0'"
    a_gate_2 = "*(int *)((int)this + 0x234) == 0"
    a_outer_call = (
        "FUN_00770e80(&DAT_00c13700,CONCAT44(param_2,param_1),"
        "CONCAT44(param_4,param_3),'\\0');"
    )
    for fragment in (a_store_b, a_store_a, a_gate_1, a_gate_2, a_outer_call):
        _require_fragment(caller_a["name"], a, fragment)
    _require_order(
        caller_a["name"],
        a,
        (a_store_b, a_store_a, a_outer_call, *[f"{name}(" for name in SHARED_POST_OUTER_CALLS]),
    )

    caller_b = extracted[DIRECT_CALLERS[1]]
    b_body = caller_b["body"]
    b = caller_b["compact"]
    b_gate = "*(int *)((int)param_1 + 0x34) != 0"
    b_switch = "switch(*(undefined4 *)((int)param_1 + 0x234))"
    for fragment in (b_gate, b_switch):
        _require_fragment(caller_b["name"], b, fragment)
    case0_start = b_body.find("case 0:")
    case1_start = b_body.find("case 1:", case0_start + 1)
    if case0_start < 0 or case1_start < 0 or case1_start <= case0_start:
        raise ValueError(f"{caller_b['name']}: case-0 source region not recovered")
    case0 = _compact(b_body[case0_start:case1_start])
    b_outer_call = (
        "FUN_00770e80(&DAT_00c13700,*(undefined8 *)((int)param_1 + 0x1aa8),"
        "*(undefined8 *)((int)param_1 + 0x1ab0),'\\x01');"
    )
    b_copy = "*(undefined8 *)((int)param_1 + 200) = *(undefined8 *)((int)param_1 + 0x1aa8);"
    for fragment in (b_outer_call, b_copy):
        _require_fragment(caller_b["name"], case0, fragment)
    _require_order(
        caller_b["name"],
        case0,
        (b_outer_call, b_copy, *[f"{name}(" for name in SHARED_POST_OUTER_CALLS]),
    )

    outer = extracted[OUTER_UPDATE]
    outer_body = outer["compact"]
    outer_store_b = "*(undefined8 *)((int)this + 0xa0) = param_2;"
    outer_pass = "FUN_0076d100(this,param_3);"
    outer_store_a = "*(undefined8 *)((int)this + 0x98) = param_1;"
    _require_fragment(outer["name"], outer_body, outer_store_b)
    _require_fragment(outer["name"], outer_body, outer_store_a)
    if outer_body.count(_compact(outer_pass)) != 2:
        raise ValueError(f"{outer['name']}: expected exactly two source calls to FUN_0076d100")
    first_pass = outer_body.find(_compact(outer_pass))
    second_pass = outer_body.find(_compact(outer_pass), first_pass + 1)
    if not (
        outer_body.find(_compact(outer_store_b)) < first_pass < second_pass < outer_body.find(_compact(outer_store_a))
    ):
        raise ValueError(f"{outer['name']}: parameter-store/pass ordering changed")

    batch = extracted[UPSTREAM_BATCH]
    batch_body = batch["compact"]
    batch_fragments = (
        "0.0 < *(double *)((int)this + 0x348)",
        "dVar3 = (double)*(int *)(iVar6 + 0x388);",
        "local_14 = (uint)(longlong)ROUND(dVar3 * *(double *)((int)this + 0x348) + 0.5);",
        "dVar2 = *(double *)((int)this + 0x160);",
        "dVar4 = 1.0 / dVar3;",
        "dVar2 = dVar4 + dVar2;",
        "*(int *)((int)this + 0x140)",
        "*(int *)((int)this + 0x144)",
        "iVar7 = iVar7 + 0x1fa0;",
        "(void *)(*piVar1 + 0x340)",
    )
    for fragment in batch_fragments:
        _require_fragment(batch["name"], batch_body, fragment)
    call_token = _compact("FUN_00794a30(")
    if batch_body.count(call_token) != 3:
        raise ValueError(f"{batch['name']}: expected exactly three source calls to FUN_00794a30")
    for fragment in (
        "0x20000000,0x3fa11111,'\\0');",
        "SUB84(dVar4,0),iVar6,'\\0');",
        "SUB84(dVar4,0),iVar6,'\\x01');",
    ):
        _require_fragment(batch["name"], batch_body, fragment)

    owner = extracted[UPSTREAM_OWNER]
    owner_call = "FUN_00713050(this,piVar2);"
    _require_fragment(owner["name"], owner["compact"], owner_call)

    fixed_bits = (0x3FA11111 << 32) | 0x20000000
    fixed_value = struct.unpack("<d", struct.pack("<Q", fixed_bits))[0]

    return {
        "format": FORMAT,
        "source": {
            "path": str(source_path),
            "sha256": source_hash,
            "function_lines": {
                address: row["line"] for address, row in extracted.items()
            },
        },
        "ghidra": {
            "root": str(ghidra_root),
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": binary.get("pointer_size"),
        },
        "outer_update": {
            "function": OUTER_UPDATE,
            "source_line": outer["line"],
            "receiver_at_callsites": "DAT_00c13700",
            "channel_a_parameter": "param_1",
            "channel_a_receiver_offset": "0x98",
            "channel_b_parameter": "param_2",
            "channel_b_receiver_offset": "0xa0",
            "mode_flag_parameter": "param_3",
            "physics_pass_target": "0x0076d100",
            "physics_pass_count": 2,
            "parameter_ordering": "channel_b-store -> pass-1 -> pass-2 -> channel_a-store",
        },
        "direct_callsites": [
            {
                "caller": DIRECT_CALLERS[0],
                "source_line": caller_a["line"],
                "ghidra_call": _edge(
                    next(row for row in outgoing[DIRECT_CALLERS[0]] if row.get("to") == OUTER_UPDATE)
                ),
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_written_from_function_arguments_before_call": True,
                "gate": ["param_5 != 0", "caller +0x234 == 0"],
                "outer_mode_argument": 0,
                "shared_post_outer_calls": list(SHARED_POST_OUTER_CALLS),
                "promoted": False,
            },
            {
                "caller": DIRECT_CALLERS[1],
                "source_line": caller_b["line"],
                "ghidra_call": _edge(
                    next(row for row in outgoing[DIRECT_CALLERS[1]] if row.get("to") == OUTER_UPDATE)
                ),
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_read_from_caller_object": True,
                "gate": ["caller +0x34 != 0", "switch(caller +0x234) case 0"],
                "outer_mode_argument": 1,
                "shared_post_outer_calls": list(SHARED_POST_OUTER_CALLS),
                "direct_incoming_call_count": 0,
                "computed_jump_candidate": switches[0],
                "promoted": False,
            },
        ],
        "upstream_batch_path": {
            "function": UPSTREAM_BATCH,
            "source_line": batch["line"],
            "direct_calls_to_first_caller": [_edge(row) for row in upstream_calls],
            "record_pointer_array_offset": "0x140",
            "record_count_offset": "0x144",
            "record_stride": "0x1fa0",
            "child_object_pointer_adjustment": "0x340",
            "accumulator_offset": "0x348",
            "channel_a_seed_offset": "0x160",
            "rate_source": "FUN_0070fe90() + 0x388",
            "reciprocal_step_expression": "1.0 / rate_source",
            "fixed_channel_b_bits": "0x3fa1111120000000",
            "fixed_channel_b_value": fixed_value,
            "first_caller_source_call_count": 3,
        },
        "upstream_owner_path": {
            "function": UPSTREAM_OWNER,
            "source_line": owner["line"],
            "direct_call": _edge(owner_calls[0]),
        },
        "scope": {
            "source_snapshot_hash_verified": True,
            "ghidra_binary_identity_verified": True,
            "source_and_direct_callgraph_cross_checked": True,
            "caller_channel_offsets_proven": True,
            "outer_receiver_offsets_proven": True,
            "channel_physical_units_proven": False,
            "channel_semantic_names_proven": False,
            "rendered_frame_schedule_proven": False,
            "vehicle_class_identity_proven": False,
            "input_control_ownership_proven": False,
            "ownerless_second_caller_indirect_dispatch_resolved": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="known recovered SHIFT.exe.c snapshot")
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_outer_update_callsite_contract(args.source, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"source sha256: {report['source']['sha256']}")
    print(f"outer update: {report['outer_update']['function']}")
    print(
        "direct callers: "
        + ", ".join(row["caller"] for row in report["direct_callsites"])
    )
    print(
        "upstream batch calls: "
        + str(report["upstream_batch_path"]["first_caller_source_call_count"])
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
