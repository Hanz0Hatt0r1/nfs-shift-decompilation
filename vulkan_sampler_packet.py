"""Binary sampler-state packet consumed by the native Vulkan texture executor.

SVTP/1 remains unchanged. SVSS/1 carries the normalized subset that the current
single-mip native executor can apply without reconstructing D3D9 state:
min/mag filters, mip filter declaration, address U/V/W and sRGB. Mip filtering and
anisotropy greater than one are preserved but marked non-consumable because the
current texture packet contains one mip level and the executor does not enable
anisotropic sampling.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Mapping

from texture_pipeline import build_sampler_contract

FORMAT = "SHIFT.VulkanSamplerPacket/1"
MAGIC = b"SVSS"
VERSION = 1
HEADER = struct.Struct("<4sIIII")
RECORD = struct.Struct("<10I f")

_FILTER = {"NEAREST": 1, "LINEAR": 2}
_MIP = {"NONE": 0, "POINT": 1, "LINEAR": 2}
_ADDRESS = {"REPEAT": 1, "CLAMP_TO_EDGE": 2}


def _contract(row: Mapping[str, Any]) -> dict[str, Any]:
    state = row.get("sampler_state")
    if state is None:
        state = {
            key: row.get(key)
            for key in (
                "min_filter", "mag_filter", "mip_filter",
                "address_u", "address_v", "address_w",
                "max_anisotropy", "lod_bias", "srgb", "linear",
            )
            if row.get(key) is not None
        }
    return build_sampler_contract(dict(state or {}))


def build_vulkan_sampler_packet(
    render_command: Mapping[str, Any],
    output: str | Path,
) -> dict[str, Any]:
    rows = []
    blockers: list[str] = []
    seen: set[int] = set()

    for submesh_index, submesh in enumerate(render_command.get("submeshes", []) or []):
        for row_index, row in enumerate(submesh.get("textures", []) or []):
            if not isinstance(row, Mapping) or row.get("resource") == "external":
                continue
            register = row.get("d3d9_sampler_register", row.get("slot"))
            try:
                register = int(register)
            except (TypeError, ValueError):
                blockers.append(
                    f"sampler-packet:texture-register-invalid:{submesh_index}:{row_index}"
                )
                continue
            if register in seen:
                blockers.append(f"sampler-packet:duplicate-register:s{register}")
                continue
            seen.add(register)

            contract = _contract(row)
            if not contract.get("ready"):
                blockers.extend(
                    f"sampler-packet:s{register}:{reason}"
                    for reason in contract.get("blocking_reasons") or []
                )
                continue

            sampler = contract
            min_filter = str(sampler.get("min_filter") or "NEAREST")
            mag_filter = str(sampler.get("mag_filter") or "NEAREST")
            mip_filter = str(sampler.get("mip_filter") or "NONE")
            address_u = str(sampler.get("address_u") or "REPEAT")
            address_v = str(sampler.get("address_v") or "REPEAT")
            address_w = str(sampler.get("address_w") or address_v)
            anisotropy = int(sampler.get("max_anisotropy") or 1)
            if min_filter not in _FILTER or mag_filter not in _FILTER:
                blockers.append(f"sampler-packet:s{register}:unsupported-filter")
                continue
            if mip_filter not in _MIP:
                blockers.append(f"sampler-packet:s{register}:unsupported-mip-filter")
                continue
            if address_u not in _ADDRESS or address_v not in _ADDRESS or address_w not in _ADDRESS:
                blockers.append(f"sampler-packet:s{register}:unsupported-address")
                continue
            if mip_filter != "NONE":
                blockers.append(
                    f"sampler-packet:s{register}:mip-filter-requires-mip-chain"
                )
            if anisotropy != 1:
                blockers.append(
                    f"sampler-packet:s{register}:anisotropy-not-enabled"
                )

            rows.append({
                "register": register,
                "submesh_index": submesh_index,
                "min_filter": _FILTER[min_filter],
                "mag_filter": _FILTER[mag_filter],
                "mip_filter": _MIP[mip_filter],
                "address_u": _ADDRESS[address_u],
                "address_v": _ADDRESS[address_v],
                "address_w": _ADDRESS[address_w],
                "srgb": 1 if sampler.get("color_space") == "sRGB" else 0,
                "anisotropy": anisotropy,
                "lod_bias": float(sampler.get("lod_bias") or 0),
            })

    blob = bytearray(HEADER.pack(MAGIC, VERSION, len(rows), 1, 0))
    for row in rows:
        blob.extend(RECORD.pack(
            row["register"],
            row["min_filter"],
            row["mag_filter"],
            row["mip_filter"],
            row["address_u"],
            row["address_v"],
            row["address_w"],
            row["srgb"],
            row["anisotropy"],
            row["submesh_index"],
            row["lod_bias"],
        ))
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(path),
        "record_count": len(rows),
        "records": rows,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "native_consumption": "min-mag-address-srgb; mip-filter-and-anisotropy-blocked",
    }
