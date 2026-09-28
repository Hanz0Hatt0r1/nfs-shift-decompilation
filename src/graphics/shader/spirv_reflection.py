"""Minimal dependency-free SPIR-V descriptor reflection for the SHIFT Vulkan backend.

The reflection layer intentionally covers only descriptor metadata required by the
current renderer boundary: set/binding, descriptor class, resource type, stage and
optional OpName. It does not interpret shader instructions or invent resource usage.
"""
from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.SPIRVReflection/1"
MAGIC = 0x07230203

OP_NAME = 5
OP_ENTRY_POINT = 15
OP_DECORATE = 71
OP_TYPE_VOID = 19
OP_TYPE_BOOL = 20
OP_TYPE_INT = 21
OP_TYPE_FLOAT = 22
OP_TYPE_VECTOR = 23
OP_TYPE_IMAGE = 25
OP_TYPE_SAMPLER = 26
OP_TYPE_SAMPLED_IMAGE = 27
OP_TYPE_ARRAY = 28
OP_TYPE_RUNTIME_ARRAY = 29
OP_TYPE_STRUCT = 30
OP_TYPE_POINTER = 32
OP_VARIABLE = 59

DECORATION_BINDING = 33
DECORATION_DESCRIPTOR_SET = 34
DECORATION_LOCATION = 30

STORAGE_UNIFORM_CONSTANT = 0
STORAGE_UNIFORM = 2
STORAGE_INPUT = 1
STORAGE_OUTPUT = 3
STORAGE_PUSH_CONSTANT = 9
STORAGE_STORAGE_BUFFER = 12

DIM_1D = 0
DIM_2D = 1
DIM_3D = 2
DIM_CUBE = 3


@dataclass(frozen=True)
class Descriptor:
    result_id: int
    set_index: int
    binding: int
    descriptor_type: str
    resource_type: str
    stage: str
    name: str | None
    variable_type_id: int
    resource_type_id: int


def _words(data: bytes) -> list[int]:
    if len(data) < 20 or len(data) % 4 != 0:
        raise ValueError("SPIR-V binary is truncated or not word-aligned")
    words = list(struct.unpack("<" + "I" * (len(data) // 4), data))
    if words[0] != MAGIC:
        raise ValueError("SPIR-V magic is invalid")
    return words


def _string(words: list[int]) -> str:
    raw = struct.pack("<" + "I" * len(words), *words)
    raw = raw.split(b"\x00", 1)[0]
    return raw.decode("utf-8", errors="replace")


def _descriptor_type(
    type_id: int,
    types: dict[int, tuple[str, tuple[int, ...]]],
) -> tuple[str, str, int]:
    seen: set[int] = set()
    current = type_id
    pointer_storage = -1
    while current in types and current not in seen:
        seen.add(current)
        opcode, operands = types[current]
        if opcode == "pointer":
            pointer_storage = operands[0]
            current = operands[1]
            continue
        if opcode == "sampled_image":
            image_id = operands[0]
            image = types.get(image_id)
            resource = "sampler2D"
            if image and image[0] == "image":
                dim = image[1][1]
                if dim == DIM_CUBE:
                    resource = "samplerCube"
            return "combined-image-sampler", resource, current
        if opcode == "image":
            dim = operands[1]
            sampled = operands[5]
            resource = "samplerCube" if dim == DIM_CUBE else "image"
            descriptor = "sampled-image" if sampled != 0 else "storage-image"
            return descriptor, resource, current
        if opcode == "sampler":
            return "sampler", "sampler", current
        if opcode == "struct":
            if pointer_storage == STORAGE_UNIFORM:
                return "uniform-buffer", "uniform-block", current
            if pointer_storage == STORAGE_STORAGE_BUFFER:
                return "storage-buffer", "storage-block", current
            return "struct", "struct", current
        current = operands[0] if operands else current
        break

    raise ValueError(f"unsupported SPIR-V descriptor type id {type_id}")


def reflect_spirv(
    data: bytes,
    *,
    stage: str,
) -> dict[str, Any]:
    stage = str(stage).lower()
    if stage not in {"vertex", "pixel", "fragment"}:
        raise ValueError("stage must be vertex or pixel")

    words = _words(data)
    names: dict[int, str] = {}
    decorations: dict[int, dict[int, int]] = {}
    variables: list[tuple[int, int, int]] = []
    types: dict[int, tuple[str, tuple[int, ...]]] = {}
    entry_points: list[str] = []

    index = 5
    while index < len(words):
        word = words[index]
        count = word >> 16
        opcode = word & 0xFFFF
        if count == 0 or index + count > len(words):
            raise ValueError("invalid SPIR-V instruction length")
        operands = words[index + 1:index + count]

        if opcode == OP_NAME and len(operands) >= 2:
            names[operands[0]] = _string(operands[1:])
        elif opcode == OP_ENTRY_POINT and len(operands) >= 3:
            entry_points.append(_string(operands[2:]))
        elif opcode == OP_DECORATE and len(operands) >= 3:
            target, decoration = operands[:2]
            literal = operands[2] if len(operands) >= 3 else 0
            decorations.setdefault(target, {})[decoration] = literal
        elif opcode == OP_TYPE_IMAGE and len(operands) >= 7:
            types[operands[0]] = ("image", tuple(operands[1:]))
        elif opcode == OP_TYPE_SAMPLER and operands:
            types[operands[0]] = ("sampler", tuple(operands[1:]))
        elif opcode == OP_TYPE_SAMPLED_IMAGE and len(operands) >= 2:
            types[operands[0]] = ("sampled_image", tuple(operands[1:]))
        elif opcode == OP_TYPE_STRUCT and operands:
            types[operands[0]] = ("struct", tuple(operands[1:]))
        elif opcode == OP_TYPE_POINTER and len(operands) >= 3:
            types[operands[0]] = ("pointer", tuple(operands[1:]))
        elif opcode == OP_TYPE_ARRAY and len(operands) >= 3:
            types[operands[0]] = ("array", tuple(operands[1:]))
        elif opcode == OP_TYPE_RUNTIME_ARRAY and len(operands) >= 2:
            types[operands[0]] = ("runtime_array", tuple(operands[1:]))
        elif opcode == OP_VARIABLE and len(operands) >= 3:
            variables.append((operands[1], operands[0], operands[2]))

        index += count

    descriptors: list[dict[str, Any]] = []
    blockers: list[str] = []
    for result_id, variable_type_id, storage in variables:
        decoration = decorations.get(result_id, {})
        if DECORATION_BINDING not in decoration and DECORATION_DESCRIPTOR_SET not in decoration:
            continue
        if DECORATION_BINDING not in decoration or DECORATION_DESCRIPTOR_SET not in decoration:
            blockers.append(f"spirv-reflection:incomplete-binding:{result_id}")
            continue
        set_index = decoration[DECORATION_DESCRIPTOR_SET]
        binding = decoration[DECORATION_BINDING]
        try:
            descriptor_type, resource_type, resource_type_id = _descriptor_type(
                variable_type_id, types
            )
        except ValueError as error:
            blockers.append(f"spirv-reflection:unsupported-descriptor:{result_id}:{error}")
            continue

        if storage not in {
            STORAGE_UNIFORM_CONSTANT,
            STORAGE_UNIFORM,
            STORAGE_STORAGE_BUFFER,
        }:
            blockers.append(f"spirv-reflection:unsupported-storage-class:{result_id}:{storage}")
            continue

        descriptors.append({
            "result_id": result_id,
            "set": set_index,
            "binding": binding,
            "descriptor_type": descriptor_type,
            "resource_type": resource_type,
            "stage": "fragment" if stage == "pixel" else stage,
            "name": names.get(result_id),
            "variable_type_id": variable_type_id,
            "resource_type_id": resource_type_id,
        })

    descriptors.sort(key=lambda row: (row["set"], row["binding"], row["stage"], row["result_id"]))
    collisions: dict[tuple[int, int], list[str]] = {}
    for row in descriptors:
        collisions.setdefault((row["set"], row["binding"]), []).append(row["descriptor_type"])
    for (set_index, binding), kinds in collisions.items():
        if len(set(kinds)) != 1:
            blockers.append(
                f"spirv-reflection:descriptor-type-collision:set{set_index}:binding{binding}"
            )

    return {
        "format": FORMAT,
        "version": 1,
        "stage": "fragment" if stage == "pixel" else stage,
        "entry_points": entry_points,
        "descriptors": descriptors,
        "descriptor_count": len(descriptors),
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "ready": not blockers,
    }


def reflect_spirv_file(
    path: str | Path,
    *,
    stage: str,
) -> dict[str, Any]:
    source = Path(path)
    result = reflect_spirv(source.read_bytes(), stage=stage)
    result["source"] = {
        "path": str(source),
        "sha256": __import__("hashlib").sha256(source.read_bytes()).hexdigest(),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reflect a Vulkan SPIR-V descriptor interface")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--stage", required=True, choices=("vertex", "pixel", "fragment"))
    args = parser.parse_args(argv)
    result = reflect_spirv_file(args.input, stage=args.stage)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "ready": result["ready"],
        "descriptor_count": result["descriptor_count"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
