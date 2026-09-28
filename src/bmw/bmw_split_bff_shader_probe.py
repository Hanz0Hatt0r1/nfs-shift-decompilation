"""Compact probe for the real split BMW material/shader inputs.

Primary archive normally contains the vehicle MEB/BMT/textures while RENDER.bff
contains renderer-global FX source and compiled FXO permutations. This probe
keeps those provenance boundaries visible without selecting undocumented
runtime state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bmw_material_from_bff import (
    TARGET_BMT,
    TARGET_MEB,
    build_real_bmw_material_binding,
)

FORMAT = "SHIFT.BMWSplitBFFShaderProbe/1"


def build_probe(
    primary: str | Path,
    supplemental: list[str | Path],
) -> dict[str, Any]:
    report = build_real_bmw_material_binding(
        primary,
        supplemental_bffs=supplemental,
    )
    binding = report.get("material_binding") or {}
    provenance = report.get("provenance") or {}
    selected = binding.get("selected_fxo") or {}
    linked = binding.get("linked_shader_pair")
    return {
        "format": FORMAT,
        "status": report.get("status"),
        "ready": report.get("ready"),
        "blocking_reasons": report.get("blocking_reasons") or [],
        "targets": {
            "bmt": TARGET_BMT,
            "meb": TARGET_MEB,
        },
        "shader": {
            "material_shader": binding.get("shader"),
            "selection_status": binding.get("selection_status"),
            "selected_fxo": {
                "file": selected.get("file"),
                "program_offset": selected.get("program_offset"),
                "pixel_sha256": selected.get("pixel_sha256"),
                "vertex_sha256": selected.get("vertex_sha256"),
                "pair_sha256": selected.get("pair_sha256"),
                "permutation_identity": selected.get("permutation_identity"),
            } if selected else None,
            "linked_shader_pair_present": linked is not None,
            "linked_shader_error": binding.get("linked_shader_error"),
        },
        "provenance": {
            "primary_bff": provenance.get("primary_bff"),
            "supplemental_bffs": provenance.get("supplemental_bffs") or [],
            "material_entry": provenance.get("material_entry"),
            "mesh_entry": provenance.get("mesh_entry"),
            "shader_source": provenance.get("shader_source") or provenance.get("shader_source_entry"),
            "fxo_candidate_count": provenance.get("fxo_candidate_count", 0),
            "dds_path_count": provenance.get("dds_path_count", 0),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Probe real BMW BMT/MEB plus split RENDER.bff shader inputs"
    )
    ap.add_argument("primary", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument(
        "--supplemental-bff",
        action="append",
        default=[],
        help="supplemental archive; repeat for RENDER.bff and other shared archives",
    )
    args = ap.parse_args(argv)
    report = build_probe(args.primary, args.supplemental_bff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "selection_status": report["shader"]["selection_status"],
        "selected_fxo": report["shader"]["selected_fxo"],
        "fxo_candidate_count": report["provenance"]["fxo_candidate_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
