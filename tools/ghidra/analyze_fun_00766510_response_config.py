#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT.Fun00766510ResponseConfigOwnership/1"
PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

REQUIRED = {
    "setup_call": "FUN_00756bb0(this_01,param_1,(int)param_2);",
    "curve_scalar_copy": "*(undefined8 *)((int)this + 0x3910) = *(undefined8 *)(param_2 + 0x730);",
    "curve_gate_setup": "FUN_00752f10((void *)((int)this + 0x3918),*(undefined8 *)(param_2 + 0x738),",
    "response_vector_base": "local_18 = (double *)((int)this + 0x3960);",
    "response_vector_source": "local_14 = (float *)(param_2 + 0x768);",
    "response_vector_stride": "local_14 = local_14 + 0x12;",
    "response_vector_count": "pdStack_1c = (double *)0x6;",
    "derived_store": "*(double *)((int)this + 0x3908) =",
    "derived_setup_call": "FUN_00756ac0(this,(double)*(int *)(param_1 + 0x169c) * *(double *)(param_1 + 0x1690) +",
    "derived_mutation_call": "FUN_00756ac0(this,*(double *)((int)this + 0x3c78));",
    "derived_reset_call": "FUN_00756ac0(param_1,*(double *)((int)param_1 + 0x3c78));",
    "consumer_curve": "fVar9 = FUN_00755340((double *)((int)param_1 + 0x3918),local_60,local_50);",
    "consumer_scale": "+ (float10)*(double *)((int)param_1 + 0x3908)) * fVar9;",
    "consumer_vectors": "FUN_007551e0((void *)((int)param_1 + 0x3950),&local_60,local_200,local_1b8,&local_78);",
}


def line_numbers(lines: list[str], needle: str) -> list[int]:
    return [i for i, line in enumerate(lines, 1) if needle in line]


def require(lines: list[str], key: str, *, minimum: int = 1) -> list[int]:
    needle = REQUIRED[key]
    hits = line_numbers(lines, needle)
    if len(hits) < minimum:
        raise SystemExit(f"missing required anchor {key}: {needle!r}")
    return hits


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PINNED_SOURCE_SHA256:
        raise SystemExit(f"unexpected SHIFT.exe.c sha256: {sha}")
    lines = raw.decode("utf-8", errors="strict").splitlines()

    setup_call = require(lines, "setup_call")
    copy_3910 = require(lines, "curve_scalar_copy")
    setup_3918 = require(lines, "curve_gate_setup")
    vector_base = require(lines, "response_vector_base")
    vector_source = require(lines, "response_vector_source")
    vector_stride = require(lines, "response_vector_stride")
    vector_count = require(lines, "response_vector_count")
    store_3908 = require(lines, "derived_store")
    setup_3908 = require(lines, "derived_setup_call")
    refresh_3908 = require(lines, "derived_mutation_call", minimum=1)
    reset_3908 = require(lines, "derived_reset_call", minimum=1)
    consumer_curve = require(lines, "consumer_curve")
    consumer_scale = require(lines, "consumer_scale")
    consumer_vectors = require(lines, "consumer_vectors")

    setup_start, setup_end = 751499, 751697
    writer_start, writer_end = 751454, 751465
    setup_lines = lines[setup_start - 1:setup_end]
    writer_lines = lines[writer_start - 1:writer_end]
    direct_3910 = [setup_start + i for i, line in enumerate(setup_lines) if "+ 0x3910) =" in line]
    direct_3918_setup = [setup_start + i for i, line in enumerate(setup_lines) if "+ 0x3918)," in line]
    direct_3908 = [writer_start + i for i, line in enumerate(writer_lines) if "+ 0x3908) =" in line]
    if direct_3910 != copy_3910:
        raise SystemExit(f"unexpected +0x3910 direct writer surface: {direct_3910}")
    if direct_3908 != store_3908:
        raise SystemExit(f"unexpected +0x3908 direct writer surface: {direct_3908}")
    if direct_3918_setup != setup_3918:
        raise SystemExit(f"unexpected +0x3918 setup surface: {direct_3918_setup}")

    return {
        "format": FORMAT,
        "ready": True,
        "source": {
            "authority": "PC retail 1.02",
            "retail_executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
            "file": path.name,
            "sha256": sha,
            "xbox_recomp_required": False,
        },
        "setup_owner": {
            "vehicle_setup_function": "FUN_0076b280",
            "response_setup_function": "FUN_00756bb0",
            "setup_call_line": setup_call[0],
            "setup_param_2_role": "VehicleLoadData/config object passed unchanged into FUN_00756bb0",
        },
        "fields": {
            "HDVehicle+0x3910": {"ownership": "setup-copy", "source": "setup_param_2+0x730", "writer": "FUN_00756bb0", "writer_line": copy_3910[0], "direct_writer_count": 1, "runtime_consumer": "FUN_00766510"},
            "HDVehicle+0x3918": {"ownership": "setup-configured helper state", "source": ["setup_param_2+0x738", "setup_param_2+0x740", "setup_param_2+0x748"], "writer": "FUN_00756bb0 -> FUN_00752f10", "writer_line": setup_3918[0], "setup_writer_count": 1, "runtime_consumer": "FUN_00766510 -> FUN_00755340"},
            "HDVehicle+0x3950[6]": {"ownership": "setup-populated six-vector table", "storage": "six contiguous 0x18-byte vectors at +0x3950..+0x39d8", "constructor": "FUN_0076b130 vector constructor count=6 stride=0x18", "source_record_base": "setup_param_2+0x750", "source_record_stride": "0x48 bytes", "source_record_count": 6, "evaluator": "FUN_007a6be0", "population_function": "FUN_00756bb0", "population_anchor_lines": [vector_count[0], vector_base[0], vector_source[0], vector_stride[0]], "runtime_consumer": "FUN_00766510 -> FUN_007551e0"},
            "HDVehicle+0x3908": {"ownership": "derived mutable state", "writer": "FUN_00756ac0", "writer_line": store_3908[0], "direct_writer_count": 1, "formula": "(+0x3750*s*s) + (+0x3748*s) + (+0x3740)", "selector_state": "HDVehicle+0x3c78", "setup_seed": "VehicleLoadData interpolation at param_1+0x1688/+0x1690/+0x169c", "setup_call_line": setup_3908[0], "post_setup_refresh": {"FUN_00757e60": "mutates +0x3740/+0x3758 then recomputes +0x3908 from +0x3c78", "FUN_00758210": "clamps/reset +0x3740/+0x3758 then recomputes +0x3908 from +0x3c78", "FUN_00769d60": "global reset path recomputes +0x3908 from +0x3c78", "source_visible_recompute_anchor_lines": sorted(set(refresh_3908 + reset_3908))}, "runtime_consumer": "FUN_00766510"},
        },
        "consumer": {"function": "FUN_00766510", "curve_line": consumer_curve[0], "scale_line": consumer_scale[0], "vector_table_line": consumer_vectors[0], "ordering": "curve(+0x3918) -> scale(+0x3910,+0x3908) -> six-vector response(+0x3950)"},
        "adjudication": {"response_config_owner_closed": True, "plus_3910_per_pass_provider_required": False, "plus_3918_per_pass_provider_required": False, "plus_3950_per_pass_provider_required": False, "plus_3908_is_setup_constant": False, "plus_3908_requires_persistent_state_and_mutation_hooks": True, "contact_response_provider_removable_now": False},
        "limits": ["This contract proves owner/write/refresh provenance, not selected BMW numeric values for every response-config scalar/vector.", "It does not internalize the earlier +0x3b20 branch, optional +0x3bc8/+0x3cxx branch, or all auxiliary/state/diagnostic writes in FUN_00766510.", "Xbox recompilation is not required for any promoted claim."],
        "next_owner": "Process 2 for consuming setup-owned +0x3910/+0x3918/+0x3950 and persistent +0x3908 state once selected values/materialization are available; Process 1 continues P1.1 remaining branches.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("--output", type=Path)
    ns = ap.parse_args()
    payload = analyze(ns.source)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if ns.output:
        ns.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
