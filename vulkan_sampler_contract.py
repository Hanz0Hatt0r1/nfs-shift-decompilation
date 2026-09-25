"""Lossless sampler-state sidecar for the Vulkan bundle boundary.

The binary SVTP/1 packet intentionally remains unchanged. This module preserves the
full normalized D3D9-FX sampler contract so later native stages can consume it without
reconstructing state from the four-value sampler_mode enum.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from texture_pipeline import build_sampler_contract

FORMAT = "SHIFT.VulkanSamplerContract/1"
METADATA_FORMAT = "SHIFT.VulkanSamplerMetadata/1"


def _state_contract(row: Mapping[str, Any]) -> dict[str, Any]:
    state = row.get("sampler_state") or {
        key: row.get(key)
        for key in (
            "min_filter", "mag_filter", "mip_filter",
            "address_u", "address_v", "address_w",
            "max_anisotropy", "lod_bias", "srgb", "linear",
        )
        if row.get(key) is not None
    }
    return build_sampler_contract(dict(state))


def build_sampler_contract_report(
    render_command: Mapping[str, Any],
) -> dict[str, Any]:
    textures: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    blockers: list[str] = []

    for submesh_index, submesh in enumerate(render_command.get("submeshes", []) or []):
        for row_index, row in enumerate(submesh.get("textures", []) or []):
            if not isinstance(row, Mapping):
                blockers.append(
                    f"sampler-contract:texture-row-invalid:{submesh_index}:{row_index}"
                )
                continue
            if row.get("resource") == "external":
                continue
            register = row.get("d3d9_sampler_register", row.get("slot"))
            try:
                register = int(register)
            except (TypeError, ValueError):
                blockers.append(
                    f"sampler-contract:texture-register-invalid:{submesh_index}:{row_index}"
                )
                continue
            contract = _state_contract(row)
            textures.append({
                "submesh_index": submesh_index,
                "register": register,
                "sampler": row.get("sampler"),
                "material_parameter": row.get("material_parameter"),
                "contract": contract,
            })
            blockers.extend(
                f"sampler-contract:s{register}:{reason}"
                for reason in contract.get("blocking_reasons") or []
            )

        for row_index, row in enumerate(submesh.get("external_samplers", []) or []):
            if not isinstance(row, Mapping):
                blockers.append(
                    f"sampler-contract:external-row-invalid:{submesh_index}:{row_index}"
                )
                continue
            register = row.get("d3d9_sampler_register", row.get("slot"))
            try:
                register = int(register)
            except (TypeError, ValueError):
                blockers.append(
                    f"sampler-contract:external-register-invalid:{submesh_index}:{row_index}"
                )
                continue
            state = row.get("sampler_state")
            external.append({
                "submesh_index": submesh_index,
                "register": register,
                "sampler": row.get("sampler") or row.get("name"),
                "sampler_type": row.get("sampler_type"),
                "contract": (
                    _state_contract(row)
                    if state is not None else {
                        "format": "SHIFT.SamplerState/1",
                        "source": "D3D9-FX",
                        "status": "not-supplied",
                        "ready": True,
                        "blocking_reasons": [],
                        "policy": {
                            "state": "external-runtime-resource-not-captured",
                        },
                    }
                ),
            })

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "textures": textures,
        "external_samplers": external,
        "native_consumption": {
            "status": "preserved-not-consumed",
            "binary_packet": "SHIFT.VulkanTexturePacket/1 sampler_mode",
            "full_contract": "SHIFT.VulkanSamplerContract/1 sidecar",
        },
    }


def write_sampler_contract_report(
    render_command: Mapping[str, Any],
    output: str | Path,
) -> dict[str, Any]:
    report = build_sampler_contract_report(render_command)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return report


def write_sampler_metadata(
    sampler_report: Mapping[str, Any],
    packet_path: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    packet = Path(packet_path)
    report = {
        "format": METADATA_FORMAT,
        "version": 1,
        "packet": {
            "path": packet.name,
            "sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
        },
        "sampler_contract": dict(sampler_report),
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return report
