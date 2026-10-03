"""Source/machine-code contract for the retail BODY frame integration bridge.

This is static evidence only.  It records the exact writer path recovered from
the retail `SHIFT.exe.c` export (SHA256 below) and corroborating x86 machine
code.  It does not implement the Linux runtime scheduler.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.BodyFrameIntegrationStatic/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXECUTABLE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

FUNCTION_BYTES = {
    "FUN_007b2270": {
        "start": 0x007B2270,
        "end": 0x007B22A9,
        "sha256": "e4e1b6ae89ba26017f9ac5a29e8043d6335899c9dc4b0789c62f2c9208b6a639",
    },
    "FUN_007bab70": {
        "start": 0x007BAB70,
        "end": 0x007BAC53,
        "sha256": "097bcfc9b1fd8127a14c7808c2c39cb680924354f3cb6e5672517ab1af20179f",
    },
    "FUN_007ba630": {
        "start": 0x007BA630,
        "end": 0x007BA7DE,
        "sha256": "4d7c11507756faf8213747d354ff9ab30ec1162693286afb69de241718f9080c",
    },
    "FUN_007aefb0": {
        "start": 0x007AEFB0,
        "end": 0x007AF003,
        "sha256": "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29",
    },
}

BODY_LAYOUT = {
    "origin": (0x00, 0x08, 0x10),
    "cross_vector": (0x18, 0x20, 0x28),
    "prepared_vector": (0x30, 0x38, 0x40),
    "accumulator_a": (0x48, 0x50, 0x58),
    "accumulator_b": (0x60, 0x68, 0x70),
    "motion_triplet": (0x78, 0x80, 0x88),
    "scalar_0x90": (0x90,),
    "symmetric_tensor": (0xB0, 0xB4, 0xB8, 0xBC, 0xC0, 0xC4, 0xC8, 0xCC, 0xD0),
    "basis": (0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4),
}


def build_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "source": {
            "program": "SHIFT.exe",
            "executable_md5": EXECUTABLE_MD5,
            "decompile_sha256": SOURCE_SHA256,
            "evidence_kinds": [
                "recovered retail source",
                "retail x86 machine code",
                "existing BODY ABI contract",
                "direct Ghidra callgraph ordering",
            ],
        },
        "functions": {
            "FUN_00765470": {
                "address": "0x00765470",
                "role": "source-backed-half-step-orchestration-boundary",
                "promoted_name": False,
                "observations": [
                    "calls FUN_007b3f40 then FUN_007b4110",
                    "calls FUN_007b2270 at 0x0076582a after post-solve feedback",
                    "forwards its double timestep argument to FUN_007b2270",
                ],
            },
            "FUN_007b2270": {
                "address": "0x007b2270",
                "role": "proven-body-array-integration-loop",
                "body_count_offset": "0x10",
                "body_array_offset": "0x14",
                "body_stride": "0x170",
                "callee": "FUN_007bab70",
                "callee_instruction": "0x007b228f",
                "promoted_name": False,
            },
            "FUN_007bab70": {
                "address": "0x007bab70",
                "role": "proven-body-state-integration-primitive",
                "promoted_name": False,
                "timestep_argument": "f64",
                "writes": [
                    {
                        "lane": "origin",
                        "equation": "origin += motion_triplet * dt",
                        "status": "proven",
                    },
                    {
                        "lane": "motion_triplet",
                        "equation": "motion_triplet += accumulator_b * scalar_0x90 * dt",
                        "status": "proven",
                    },
                    {
                        "lane": "basis",
                        "equation": "basis = FUN_007afdd0(basis, cross_vector * dt)",
                        "status": "proven",
                    },
                    {
                        "lane": "prepared_vector",
                        "equation": "prepared_vector += accumulator_a * dt",
                        "status": "proven",
                    },
                    {
                        "lane": "cross_vector",
                        "equation": "cross_vector = symmetric_tensor * prepared_vector",
                        "status": "machine-code-corroborated",
                    },
                ],
            },
            "FUN_007ba630": {
                "address": "0x007ba630",
                "role": "rebuilds BODY symmetric tensor from basis/reciprocal coefficients",
                "eax_behavior": "machine code contains no EAX write; caller EAX survives",
                "promoted_name": False,
            },
            "FUN_007aefb0": {
                "address": "0x007aefb0",
                "role": "3x3 f32 matrix times f64x3 input -> f64x3 output",
                "promoted_name": False,
            },
            "FUN_007afdd0": {
                "address": "0x007afdd0",
                "role": "basis rotation by axis/magnitude vector",
                "promoted_name": False,
            },
        },
        "machine_code_join": {
            "function": "FUN_007bab70",
            "instructions": [
                {
                    "address": "0x007bac12",
                    "observation": "LEA EAX,[ESI+0x30] selects prepared_vector",
                },
                {
                    "address": "0x007bac36",
                    "observation": "CALL FUN_007ba630 with ECX=BODY",
                },
                {
                    "address": "0x007bac3c",
                    "observation": "PUSH EAX after FUN_007ba630",
                },
                {
                    "address": "0x007bac3d",
                    "observation": "LEA ECX,[ESI+0xb0] selects symmetric_tensor",
                },
                {
                    "address": "0x007bac43",
                    "observation": "CALL FUN_007aefb0; output pointer is BODY+0x18",
                },
            ],
            "proof": (
                "EAX was loaded with BODY+0x30 before FUN_007ba630; the exact retail "
                "FUN_007ba630 bytes do not write EAX, so FUN_007aefb0 receives "
                "BODY+0x30 as its vector input and BODY+0x18 as its output."
            ),
        },
        "outer_schedule": {
            "FUN_00770e80": {
                "physics_pass_1": "0x00770f8f -> FUN_0076d100",
                "half_step_1": "0x00770fac -> FUN_00765470",
                "relation_refresh_1": "0x00770fb7 -> FUN_007b8810",
                "physics_pass_2": "0x00770fbf -> FUN_0076d100",
                "half_step_2": "0x00770fdc -> FUN_00765470",
                "relation_refresh_2": "0x00770fe7 -> FUN_007b8810",
                "half_step_scale": 0.5,
                "half_step_scale_address": "0x00aa9a20",
            }
        },
        "closed_boundaries": {
            "accumulator_b_to_motion_triplet": True,
            "motion_triplet_to_origin": True,
            "cross_vector_to_basis": True,
            "accumulator_a_to_prepared_vector": True,
            "prepared_vector_to_cross_vector": True,
            "body_array_stride_and_count": True,
            "two_half_step_order_inside_FUN_00770e80": True,
        },
        "unknown": [
            "semantic class/method names for FUN_00765470/FUN_007b2270/FUN_007bab70",
            "physical unit/name of BODY+0x90 beyond its observed multiplicative role",
            "whether outer FUN_00770e80 is invoked exactly once per rendered frame",
            "resolved targets of the two indirect calls inside FUN_007b3f40",
        ],
        "scope": {
            "game_launched": False,
            "runtime_capture_used": False,
            "linux_runtime_implementation_changed": False,
            "automatic_function_renaming_performed": False,
        },
    }


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("format") != FORMAT:
        raise ValueError(f"expected {FORMAT}")
    if contract.get("source", {}).get("executable_md5") != EXECUTABLE_MD5:
        raise ValueError("unexpected retail executable identity")
    if contract.get("source", {}).get("decompile_sha256") != SOURCE_SHA256:
        raise ValueError("unexpected decompile source identity")

    closed = contract.get("closed_boundaries")
    if not isinstance(closed, dict) or not closed:
        raise ValueError("closed_boundaries must be a non-empty object")
    if any(value is not True for value in closed.values()):
        raise ValueError("all advertised closed boundaries must be proven")

    functions = contract.get("functions")
    if not isinstance(functions, dict):
        raise ValueError("functions must be an object")
    for required in (
        "FUN_00765470",
        "FUN_007b2270",
        "FUN_007bab70",
        "FUN_007ba630",
        "FUN_007aefb0",
        "FUN_007afdd0",
    ):
        if required not in functions:
            raise ValueError(f"missing function evidence: {required}")
        if functions[required].get("promoted_name") is not False:
            raise ValueError(f"semantic promotion is forbidden here: {required}")


def main() -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    contract = build_contract()
    validate_contract(contract)
    payload = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
