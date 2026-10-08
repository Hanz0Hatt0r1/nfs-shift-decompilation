from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
UPSTREAM_CONTRACT = "SHIFT.Process1Fun006880c0QueueProvenance/1"
API_WRAPPERS = ["FUN_00634ed0", "FUN_00634f00", "FUN_00634f50"]
F50_EMBEDDED_OFFSETS = ["0x100", "0x120", "0x140", "0x160"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def calls(text: str, name: str) -> list[tuple[int, list[str]]]:
    result: list[tuple[int, list[str]]] = []
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(([^;\n]*)\);")
    for match in pattern.finditer(text):
        args = [piece.strip() for piece in match.group(1).split(",")]
        result.append((match.start(), args))
    return result


def previous_plvar_offset(text: str, position: int) -> str:
    window = text[max(0, position - 12000) : position]
    patterns = [
        r"pLVar1\s*=\s*\(LONG \*\)\(\(int\)this \+ (0x[0-9a-f]+)\)",
        r"pLVar1\s*=\s*\(LONG \*\)\(param_1 \+ (0x[0-9a-f]+)\)",
    ]
    found: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, window):
            found.append((match.start(), match.group(1)))
    if not found:
        raise ValueError("pLVar1 request-object assignment not found before call")
    return max(found, key=lambda item: item[0])[1]


def build_payload(source: Path) -> dict[str, object]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("SHIFT.exe.c hash mismatch")
    text = source.read_text(encoding="utf-8", errors="replace")

    ed0 = calls(text, "FUN_00634ed0")
    f00 = calls(text, "FUN_00634f00")
    f50 = calls(text, "FUN_00634f50")
    thunk = calls(text, "thunk_FUN_0046ef30")

    if len(ed0) != 2:
        raise ValueError(f"FUN_00634ed0 call surface drift: {len(ed0)}")
    ed0_second = [args[1].replace(" ", "") for _, args in ed0]
    if ed0_second != ["(int)this+0x1820", "(int)this+0x1820"]:
        raise ValueError(f"FUN_00634ed0 request identity drift: {ed0_second!r}")

    if len(f00) != 3:
        raise ValueError(f"FUN_00634f00 call surface drift: {len(f00)}")
    f00_offsets: list[str] = []
    heap_request_seen = False
    for position, args in f00:
        second = args[1].replace(" ", "")
        if second == "(int)pLVar1":
            f00_offsets.append(previous_plvar_offset(text, position))
        elif second == "*(int*)((int)this+0x60)":
            heap_request_seen = True
            prefix = text[max(0, position - 5000) : position]
            required = [
                "FUN_008868d0(0x220",
                "FUN_006375c0(puVar2)",
                "*(undefined4 **)((int)this + 0x60) = puVar2;",
                "FUN_00636fb0((int)puVar2,(int *)((int)this + 4));",
            ]
            missing = [token for token in required if token not in prefix]
            if missing:
                raise ValueError(f"heap request construction drift: {missing!r}")
        else:
            raise ValueError(f"unexpected FUN_00634f00 request expression: {second}")
    if f00_offsets != ["0x1820", "0x1820"] or not heap_request_seen:
        raise ValueError("FUN_00634f00 request-object classification drift")

    if len(f50) != 20:
        raise ValueError(f"FUN_00634f50 call surface drift: {len(f50)}")
    direct_offsets: list[str] = []
    forwarded_param2_count = 0
    for position, args in f50:
        second = args[1].replace(" ", "")
        if second == "param_2":
            forwarded_param2_count += 1
        elif second == "(int)pLVar1":
            direct_offsets.append(previous_plvar_offset(text, position))
        else:
            match = re.fullmatch(r"param_1\+(0x[0-9a-f]+)", second)
            if not match:
                raise ValueError(f"unexpected FUN_00634f50 request expression: {second}")
            direct_offsets.append(match.group(1))
    if forwarded_param2_count != 2:
        raise ValueError("FUN_00634f50 forwarding-wrapper count drift")
    if sorted(set(direct_offsets)) != F50_EMBEDDED_OFFSETS:
        raise ValueError(
            f"FUN_00634f50 embedded request offsets drift: {sorted(set(direct_offsets))!r}"
        )

    if len(thunk) != 4:
        raise ValueError(f"thunk_FUN_0046ef30 direct caller surface drift: {len(thunk)}")
    thunk_second = [args[1].replace(" ", "") for _, args in thunk]
    if thunk_second != ["param_1+0x100"] * 4:
        raise ValueError(f"thunk_FUN_0046ef30 request identity drift: {thunk_second!r}")

    return {
        "format": "SHIFT.Process1Fun006880c0RequestObjectIdentity/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_source_sha256": SOURCE_SHA256,
            "upstream_contract": UPSTREAM_CONTRACT,
            "xbox_recomp_required": False,
        },
        "propagation": {
            "api_wrappers": API_WRAPPERS,
            "upstream_provenance": (
                "API param_2 propagates through FUN_0066bb50 embedded_state+0x8 "
                "to FUN_006880c0 queue pointer"
            ),
        },
        "source_visible_request_surface": {
            "fun_00634ed0": {
                "call_count": 2,
                "request_object": "owner+0x1820",
                "classification": "embedded request descriptor",
            },
            "fun_00634f00": {
                "call_count": 3,
                "embedded_request_count": 2,
                "embedded_request_offset": "+0x1820",
                "heap_request_count": 1,
                "heap_request_size": "0x220",
                "heap_request_owner_slot": "+0x60",
            },
            "fun_00634f50": {
                "call_count": 20,
                "forwarding_wrapper_definition_count": 2,
                "forwarding_wrapper_direct_caller_count": 4,
                "forwarding_wrapper_request_offset": "+0x100",
                "direct_embedded_request_offsets": [
                    "+0x100",
                    "+0x120",
                    "+0x140",
                    "+0x160",
                ],
            },
        },
        "adjudication": {
            "fun_006880c0_source_visible_direct_surface_closed": True,
            "fun_006880c0_controller1_queue_alias_ruled_out_for_direct_surface": True,
            "fun_006333f0_controller1_alias_ruled_out": False,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "next_blocker": {
            "process": 1,
            "remaining_generic_queue_pointer_callers": ["FUN_006333f0"],
            "description": (
                "classify FUN_006333f0 by exact queue-object identity; keep indirect/native "
                "APC injection and render/presentation phase locking fail-closed"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_payload(args.source)
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
