#!/usr/bin/env python3
"""Close known [wheel+0x420] child-receiver callees against authoritative retail PE bytes."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Wheel420ChildCalleeMachineClosure/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")
FUNCS = {
    "FUN_007ba860": (0x007BA860, 73, 21, "1ad69d788cf63b85923c0340516a83601266ec2c0317de3c9b27f42a9d68c476"),
    "FUN_007ba7e0": (0x007BA7E0, 114, 44, "c44dac55776ac266f00822c40762b2d452226a043a0bd687209b67d3bbe947a4"),
    "FUN_007af0a0": (0x007AF0A0, 83, 33, "8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc"),
    "FUN_007af010": (0x007AF010, 35, 15, "f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324"),
    "FUN_007aefb0": (0x007AEFB0, 83, 33, "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"),
}
EXPECTED_CALLS = {
    "FUN_007ba860": [(0x007BA8A0, 0x007BA7E0)],
    "FUN_007ba7e0": [(0x007BA80D, 0x007AF0A0), (0x007BA844, 0x007AEFB0)],
    "FUN_007af0a0": [], "FUN_007af010": [], "FUN_007aefb0": [],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def disassemble(exe: Path, start: int, size: int) -> list[dict]:
    proc = subprocess.run([
        "objdump", "-d", "-Mintel", f"--start-address=0x{start:x}",
        f"--stop-address=0x{start + size:x}", str(exe)
    ], check=True, capture_output=True, text=True)
    rows = []
    for line in proc.stdout.splitlines():
        m = INSN_RE.match(line)
        if not m:
            continue
        rows.append({
            "address": int(m.group(1), 16), "bytes": bytes.fromhex(m.group(2)),
            "mnemonic": m.group(3).lower(), "operands": m.group(4).strip().lower(),
        })
    return rows


def direct_target(row: dict) -> int | None:
    if not row["mnemonic"].startswith("call"):
        return None
    op = row["operands"].split()[0]
    return int(op, 16) if re.fullmatch(r"0x[0-9a-f]+", op) else None


def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail executable SHA-256: {digest}")
    bodies = {}
    for name, (start, size, expected_insns, expected_sha) in FUNCS.items():
        rows = disassemble(exe, start, size)
        blob = b"".join(r["bytes"] for r in rows)
        body_sha = hashlib.sha256(blob).hexdigest()
        if len(blob) != size or len(rows) != expected_insns or body_sha != expected_sha:
            raise ValueError(f"{name} machine body drift: bytes={len(blob)} insns={len(rows)} sha={body_sha}")
        calls = [(r["address"], direct_target(r)) for r in rows if r["mnemonic"].startswith("call")]
        if calls != EXPECTED_CALLS[name]:
            raise ValueError(f"{name} direct-call surface drift: {calls!r}")
        # A child/back-pointer recovery would require loading a child-relative memory value into a GPR.
        gpr_child_loads = []
        child_pointer_stores = []
        for r in rows:
            ops = r["operands"]
            if r["mnemonic"] == "mov" and "," in ops:
                dst, src = [x.strip() for x in ops.split(",", 1)]
                if re.fullmatch(r"e(?:ax|bx|cx|dx|si|di|bp|sp)", dst) and re.search(r"\[(?:ecx|esi|edi)(?:\+0x[0-9a-f]+)?\]", src):
                    gpr_child_loads.append(f"0x{r['address']:08x} {r['mnemonic']} {ops}")
                if re.search(r"\[(?:ecx|esi|edi)(?:\+0x[0-9a-f]+)?\]", dst) and re.fullmatch(r"e(?:ax|bx|cx|dx|si|di|bp|sp)", src):
                    child_pointer_stores.append(f"0x{r['address']:08x} {r['mnemonic']} {ops}")
        bodies[name] = {
            "start": f"0x{start:08x}", "size": size, "instruction_count": len(rows),
            "machine_bytes_sha256": body_sha,
            "direct_calls": [{"callsite": f"0x{a:08x}", "target": f"0x{t:08x}"} for a, t in calls],
            "child_relative_gpr_load_count": len(gpr_child_loads),
            "child_relative_gpr_loads": gpr_child_loads,
            "child_relative_gpr_store_count": len(child_pointer_stores),
            "child_relative_gpr_stores": child_pointer_stores,
        }
    # All five bodies are expected to have no child-relative GPR pointer load/store surface.
    for name, body in bodies.items():
        if body["child_relative_gpr_load_count"] or body["child_relative_gpr_store_count"]:
            raise ValueError(f"{name} unexpectedly exposes child-relative GPR pointer traffic")
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1D / P1.3D",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest, "machine_bytes_adjudicate": True},
        "selected_slot3": {"wheel_root": "HDVehicle+0x2380", "target": "HDVehicle+0x28b8..+0x28bf", "local_target": "+0x538"},
        "entry_paths": [
            {"caller": "FUN_00760b50", "load": "0x00760d02 ECX=[wheel+0x420]", "callsite": "0x00760d4b", "callee": "FUN_007ba860", "receiver_identity": "child=[wheel+0x420]"},
            {"caller": "FUN_00755f80", "load": "0x00755f9c EAX=[wheel+0x420]; 0x00755faa ECX=EAX+0xd4", "callsite": "0x00755fb0", "callee": "FUN_007af0a0", "receiver_identity": "child+0xd4"},
            {"caller": "FUN_00755f80", "load": "0x00755fb8 ECX=[wheel+0x420]; 0x00755fc8 ECX+=0xd4", "callsite": "0x00755fd1", "callee": "FUN_007af010", "receiver_identity": "child+0xd4"},
        ],
        "nested_path": {
            "FUN_007ba860": "forwards unchanged child ECX to FUN_007ba7e0 at 0x007ba8a0",
            "FUN_007ba7e0": "copies child ECX to ESI, derives EDI=child+0xd4, calls FUN_007af0a0 and FUN_007aefb0 with EDI",
        },
        "machine_bodies": bodies,
        "child_effects": {
            "FUN_007ba860_writes": ["child+0x128 f32", "child+0x12c f32", "child+0x130 f32", "child+0x138 f64", "child+0x140 f64", "child+0x148 f64"],
            "transform_helpers": "FUN_007af0a0/FUN_007af010/FUN_007aefb0 read scalar matrix/vector fields and write caller-provided output buffers; they do not write receiver fields.",
            "back_pointer_or_wheel_root_recovery_found": False,
            "child_pointer_persistence_found": False,
            "selected_slot3_target_writer_found": False,
        },
        "adjudication": {
            "known_wheel_420_child_callee_subset_complete": True,
            "known_wheel_420_child_nested_direct_calls_complete": True,
            "known_wheel_420_child_back_pointer_recovery_found": False,
            "known_wheel_420_child_pointer_persistence_found": False,
            "known_wheel_420_child_selected_target_writer_found": False,
            "other_callee_created_aliases_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the machine-proven child receiver loaded from selected wheel+0x420 and the bounded nested direct helper chain above.",
            "The child object and child+0xd4 interior are not the selected wheel root; no scalar offset coincidence is promoted to object identity.",
            "Other callee-created aliases, runtime/generated pointers, callbacks, aggregate copies, and 16-carrier source-storage replay remain open.",
        ],
        "next_step": "Continue remaining callee-created/runtime alias surfaces and the independent 16-carrier source-storage replay before changing any global P1.3D gate.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe", type=Path); p.add_argument("--output", type=Path)
    a = p.parse_args()
    try: result = analyze(a.exe)
    except (ValueError, subprocess.CalledProcessError) as e: p.error(str(e))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output: a.output.write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0
if __name__ == "__main__": raise SystemExit(main())
