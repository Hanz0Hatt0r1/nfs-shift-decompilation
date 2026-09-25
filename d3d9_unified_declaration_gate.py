"""Compose the existing D3D9 declaration chain with the exact SHIFT.exe PE ABI.

This gate deliberately does not reimplement declaration semantics. It requires the
already-produced declaration-chain result and the normalized PE semantic map, then
adds optional runtime numeric parity when a declaration instance is available.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from d3d9_runtime_pe_semantic_parity import validate_runtime_against_pe

FORMAT = "SHIFT.D3D9UnifiedDeclarationGate/1"


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    data = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {value}")
    return data


def build_unified_declaration_gate(
    declaration_chain: str | Path | Mapping[str, Any],
    pe_semantic_map: str | Path | Mapping[str, Any],
    *,
    runtime_declaration: str | Path | Mapping[str, Any] | None = None,
    pe_evidence: str | Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    chain = _load(declaration_chain)
    pe_map = _load(pe_semantic_map)

    blockers: list[str] = []
    checks: dict[str, Any] = {}

    chain_status = chain.get("status")
    checks["declaration_chain"] = {
        "status": "observed" if chain_status == "observed" else "blocked",
        "detail": "existing SHIFT.D3D9DeclarationChainEvidence/1 result",
    }
    if chain_status != "observed":
        blockers.append("unified-declaration:chain-not-ready")

    map_status = pe_map.get("status")
    checks["pe_semantic_map"] = {
        "status": "observed" if pe_map.get("ready") is True else "blocked",
        "detail": "exact SHIFT.exe Type/Usage ABI map",
        "format": pe_map.get("format"),
    }
    if pe_map.get("format") != "SHIFT.D3D9PESemanticMap/1":
        blockers.append("unified-declaration:pe-map-invalid-format")
    elif pe_map.get("ready") is not True:
        blockers.extend(
            pe_map.get("blocking_reasons") or ["unified-declaration:pe-map-not-ready"]
        )

    runtime_parity = None
    if runtime_declaration is not None:
        if pe_evidence is None:
            blockers.append("unified-declaration:runtime-pe-evidence-missing")
            runtime_parity = {
                "format": "SHIFT.D3D9RuntimePESemanticParity/1",
                "status": "blocked",
                "ready": False,
                "blocking_reasons": ["runtime-pe-parity:pe-evidence-missing"],
            }
        else:
            runtime_parity = validate_runtime_against_pe(
                runtime_declaration,
                pe_evidence,
            )
            if runtime_parity.get("ready") is not True:
                blockers.extend(
                    runtime_parity.get("blocking_reasons")
                    or ["unified-declaration:runtime-pe-parity-not-ready"]
                )
            checks["runtime_pe_numeric_parity"] = {
                "status": (
                    "observed"
                    if runtime_parity.get("ready") is True
                    else "blocked"
                ),
                "detail": "runtime declaration Type/Usage values match exact SHIFT.exe PE tables",
            }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "checks": checks,
        "source": {
            "declaration_chain_format": chain.get("format"),
            "pe_semantic_map_format": pe_map.get("format"),
        },
        "pe_semantic_map": pe_map,
        "runtime_pe_numeric_parity": runtime_parity,
        "evidence_policy": {
            "m3_property_identity": "not-established-by-this-gate",
            "same_instance_draw_identity": "separate-runtime-gate",
            "allows_inference": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SHIFT.D3D9UnifiedDeclarationGate/1")
    parser.add_argument("declaration_chain")
    parser.add_argument("pe_semantic_map")
    parser.add_argument("output")
    parser.add_argument("--runtime-declaration")
    parser.add_argument("--pe-evidence")
    args = parser.parse_args(argv)

    result = build_unified_declaration_gate(
        args.declaration_chain,
        args.pe_semantic_map,
        runtime_declaration=args.runtime_declaration,
        pe_evidence=args.pe_evidence,
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
