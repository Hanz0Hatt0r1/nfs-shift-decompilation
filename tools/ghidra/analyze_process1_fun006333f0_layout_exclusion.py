from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
UPSTREAM_CONTRACT = "SHIFT.Process1Controller1BManagerQueueWake/1"
CONTROLLER_QUEUE_ALLOCATION_SIZE = 0xE0
FUN006333_REQUIRED_FIELD_OFFSET = 0x250


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def function_body(text: str, name: str) -> str:
    match = re.search(
        r"(?m)^[^\n;{}]*\b" + re.escape(name) + r"\([^\n]*\)\s*\n\s*\{",
        text,
    )
    if not match:
        raise ValueError(f"missing {name}")
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise ValueError(f"unterminated {name}")


def require(body: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in body]
    if missing:
        raise ValueError(f"source drift: {missing!r}")


def build_payload(source: Path) -> dict[str, object]:
    if digest(source) != SOURCE_SHA256:
        raise ValueError("SHIFT.exe.c hash mismatch")
    text = source.read_text(encoding="utf-8", errors="replace")

    thread_setup = function_body(text, "FUN_00649cb0")
    controller_bind = function_body(text, "FUN_00655000")
    ordered_enqueue = function_body(text, "FUN_006333f0")

    require(
        thread_setup,
        "iVar5 = FUN_008868c0(0xe0);",
        "uVar2 = FUN_0064fe70();",
        "*(undefined4 *)((int)pvVar3 + 0x5c) = uVar2;",
        "FUN_00655000((int)param_2,pvVar3,uVar2);",
    )
    require(controller_bind, "*(undefined4 *)(param_1 + 8) = param_3;")
    require(
        ordered_enqueue,
        "(*(byte *)(param_1 + 0x250) & 1)",
        "FUN_00650350(param_1,param_2,param_3,local_8);",
    )

    if FUN006333_REQUIRED_FIELD_OFFSET < CONTROLLER_QUEUE_ALLOCATION_SIZE:
        raise ValueError("layout exclusion invariant no longer holds")

    return {
        "format": "SHIFT.Process1Fun006333f0LayoutExclusion/1",
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_source_sha256": SOURCE_SHA256,
            "upstream_contract": UPSTREAM_CONTRACT,
            "xbox_recomp_required": False,
        },
        "controller1_queue": {
            "allocation_size": "0xe0",
            "allocation_function": "FUN_008868c0",
            "constructor": "FUN_0064fe70",
            "thread_state_slot": "ThreadState+0x5c",
            "controller_slot": "Controller+0x08",
            "bind_function": "FUN_00655000",
        },
        "fun_006333f0": {
            "required_object_field_offset": "+0x250",
            "required_field_read_is_on_entry_path": True,
            "generic_enqueue_fallback": "FUN_00650350",
        },
        "layout_exclusion": {
            "required_offset_exceeds_controller_queue_allocation": True,
            "controller1_queue_alias_ruled_out": True,
        },
        "adjudication": {
            "source_visible_generic_queue_pointer_alias_frontier_closed": True,
            "indirect_or_native_apc_injection_ruled_out": False,
            "render_or_present_phase_lock_proven": False,
        },
        "next_blocker": {
            "process": 1,
            "description": (
                "generic source-visible queue aliases are closed; continue with indirect/native "
                "APC injection ownership and render/presentation phase-lock evidence"
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
