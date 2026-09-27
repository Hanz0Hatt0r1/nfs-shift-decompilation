#!/usr/bin/env python3
"""Run the complete BMW apitrace raw-buffer proof in one reproducible command.

Pipeline:
  original .trace
    -> compact BMW draw/state extraction
    -> bounded apitrace --blobs extraction for the known BMW resource instances
    -> deterministic MEB VB/IB reconstruction from the retail BMW BFF
    -> exact 7-object byte parity
    -> SHIFT.BMWM3RuntimeGeometryProof/1
    -> SHIFT.BMWM3APITRACERuntimeDrawInstanceProof/1

The command never commits or embeds proprietary binary inputs. It writes only
metadata, hashes and derived local artifacts under the requested output dir.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bmw_meb_runtime_buffer_artifacts import (
    build_artifact_report,
    extract_meb_from_bff,
)
from bmw_runtime_geometry_proof import build_report as build_geometry_proof
from bmw_apitrace_runtime_instance_proof import build_report as build_runtime_instance_proof
from tools.extract_apitrace_bmw_buffer_blobs import extract_from_source
from tools.extract_apitrace_unique_bmw import extract as extract_unique_bmw_geometry
from tools.verify_apitrace_bmw_buffer_blob_parity import build_report as build_byte_parity

FORMAT = "SHIFT.BMWM3APITRACEBufferProofPipeline/1"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_expected_artifacts(
    bff: Path,
    output_dir: Path,
) -> dict[str, Any]:
    meb_bytes, provenance = extract_meb_from_bff(bff)
    report, vertex_bytes, index_bytes, primitive_bytes = build_artifact_report(
        meb_bytes,
        source=provenance,
    )
    expected_dir = output_dir / "expected"
    expected_dir.mkdir(parents=True, exist_ok=True)

    vertex_path = expected_dir / "vertex_buffer.meb-order.bin"
    index_path = expected_dir / "index_buffer.uint16.bin"
    vertex_path.write_bytes(vertex_bytes)
    index_path.write_bytes(index_bytes)
    primitive_paths = []
    for index, payload in enumerate(primitive_bytes):
        path = expected_dir / f"index_buffer_{index:02d}.uint16.bin"
        path.write_bytes(payload)
        primitive_paths.append(path)

    report = dict(report)
    report["outputs"] = {
        "vertex_buffer": str(vertex_path),
        "index_buffer": str(index_path),
        "primitive_buffers": [str(path) for path in primitive_paths],
    }
    _write_json(expected_dir / "manifest.json", report)
    return {
        "manifest": report,
        "directory": expected_dir,
        "vertex": vertex_path,
        "index": index_path,
    }


def run_pipeline(
    trace: str | Path,
    geometry_report: str | Path,
    bff: str | Path,
    output_dir: str | Path,
    *,
    apitrace: str = "apitrace",
) -> dict[str, Any]:
    trace_path = Path(trace).expanduser().resolve()
    geometry_path = Path(geometry_report).expanduser().resolve()
    bff_path = Path(bff).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)
    if not geometry_path.is_file():
        raise FileNotFoundError(geometry_path)
    if not bff_path.is_file():
        raise FileNotFoundError(bff_path)

    unique_geometry_summary = extract_unique_bmw_geometry(
        trace_path,
        out,
        apitrace=apitrace,
        target_runtime_geometry=geometry_path,
        include_shaders=True,
        include_textures=True,
    )
    unique_geometry_path = out / "unique_bmw_geometry.json"

    blob_dir = out / "extracted"
    extraction_summary = extract_from_source(
        trace_path,
        unique_geometry_path,
        blob_dir,
        apitrace=apitrace,
    )
    blob_evidence_path = blob_dir / "buffer_blob_evidence.json"
    byte_evidence = _load_json(blob_evidence_path)
    _write_json(out / "buffer_blob_evidence.json", byte_evidence)

    expected = _write_expected_artifacts(bff_path, out)
    geometry = _load_json(geometry_path)

    parity = build_byte_parity(
        byte_evidence,
        expected["directory"],
        blob_dir.resolve(),
    )
    _write_json(out / "direct_parity_report.json", parity)

    proof = build_geometry_proof(geometry, parity)
    _write_json(out / "runtime_geometry_proof.json", proof)

    runtime_instance_proof = None
    if unique_geometry_path.is_file():
        runtime_instance_proof = build_runtime_instance_proof(
            _load_json(unique_geometry_path)
        )
        _write_json(
            out / "runtime_draw_instance_proof.json",
            runtime_instance_proof,
        )

    blockers: list[str] = []
    if not proof.get("ready"):
        blockers.extend(str(reason) for reason in proof.get("blocking_reasons") or [])
    ready = proof.get("ready") is True

    result = {
        "format": FORMAT,
        "status": "proven" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "inputs": {
            "trace": str(trace_path),
            "trace_size_bytes": trace_path.stat().st_size,
            "geometry_report": str(geometry_path),
            "bff": str(bff_path),
            "apitrace": apitrace,
        },
        "unique_geometry_extraction": unique_geometry_summary,
        "extraction": extraction_summary,
        "outputs": {
            "buffer_blob_evidence": str(blob_evidence_path),
            "direct_parity_report": str(out / "direct_parity_report.json"),
            "runtime_geometry_proof": str(out / "runtime_geometry_proof.json"),
            "runtime_draw_instance_proof": (
                str(out / "runtime_draw_instance_proof.json")
                if runtime_instance_proof is not None
                else None
            ),
            "unique_bmw_geometry": (
                str(unique_geometry_path)
                if unique_geometry_path.is_file()
                else None
            ),
            "expected_manifest": str(out / "expected" / "manifest.json"),
        },
        "byte_parity": parity,
        "geometry_proof": proof,
        "runtime_draw_instance_proof": runtime_instance_proof,
        "next_gate": {
            "runtime_geometry": "proven" if ready else "not-proven",
            "runtime_declaration_instance": (
                "proven"
                if runtime_instance_proof is not None
                and runtime_instance_proof.get("ready") is True
                else "not-proven"
            ),
            "shader_material_same_instance": "separate-gate",
        },
    }
    _write_json(out / "pipeline_result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the BMW apitrace raw-buffer proof pipeline")
    parser.add_argument("trace", type=Path)
    parser.add_argument("geometry_report", type=Path)
    parser.add_argument("bff", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--apitrace", default="apitrace")
    args = parser.parse_args(argv)

    result = run_pipeline(
        args.trace,
        args.geometry_report,
        args.bff,
        args.output_dir,
        apitrace=args.apitrace,
    )
    print(
        json.dumps(
            {
                "format": result["format"],
                "status": result["status"],
                "ready": result["ready"],
                "matches": result["byte_parity"].get("matches"),
                "blocking_reasons": result["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
