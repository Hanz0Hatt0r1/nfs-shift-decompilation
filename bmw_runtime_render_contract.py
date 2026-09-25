"""Build the renderer-facing contract for one exact captured BMW draw.

This is an execution package, not an image renderer. It translates the exact
runtime-selected FXO VS/PS pair, reconstructs stage-specific D3D9 constant
banks, and records bound texture objects. External texture contents remain an
explicit requirement rather than being fabricated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_material_from_bff import TARGET_MEB
from bmw_runtime_shader_join import _runtime_draw_states
from meb_format import read_meb
from shader_backend import translate_pair_blob
from shift_importer import BFF

FORMAT = "SHIFT.BMWRuntimeRenderContract/1"


def _selected_candidate(material_input: Mapping[str, Any], selection: Mapping[str, Any]) -> Mapping[str, Any]:
    binding = material_input.get("material_binding")
    rows = binding.get("fxo_candidates") if isinstance(binding, Mapping) else None
    if not rows:
        rows = material_input.get("fxo_candidates")
    rows = [row for row in (rows or []) if isinstance(row, Mapping)]
    selected = selection.get("selected") or {}
    candidate_file = selected.get("candidate_file")
    candidate_offset = selected.get("candidate_program_offset")
    for row in rows:
        if row.get("file") == candidate_file and int(row.get("program_offset", -1)) == int(candidate_offset):
            return row
    raise ValueError("selected runtime shader candidate is not present in material input")


def _runtime_frame(runtime_report: Mapping[str, Any], selection: Mapping[str, Any]) -> Mapping[str, Any]:
    selected = selection.get("selected") or {}
    selected_frame = selected.get("frame")
    selected_draw = selected.get("draw_index")
    frames = [frame for frame in (runtime_report.get("frames") or []) if isinstance(frame, Mapping)]
    matches = [frame for frame in frames if frame.get("frame") == selected_frame]
    if len(matches) != 1:
        raise ValueError(
            f"selected runtime frame {selected_frame!r} must resolve exactly once; found {len(matches)}"
        )
    if selected_draw is None:
        return matches[0]
    snapshot_matches = [
        state
        for frame, state, source in _runtime_draw_states(runtime_report)
        if frame.get("frame") == selected_frame
        and source == "draw-snapshot"
        and state.get("draw_index") == selected_draw
    ]
    if len(snapshot_matches) != 1:
        raise ValueError(
            f"selected runtime draw {selected_frame!r}:{selected_draw!r} must resolve exactly once; found {len(snapshot_matches)}"
        )
    return snapshot_matches[0]


def _constant_banks(frame: Mapping[str, Any]) -> dict[str, dict[str, dict[int, list[float]]]]:
    banks: dict[str, dict[str, dict[int, list[float]]]] = {
        "vertex": {"c": {}},
        "pixel": {"c": {}},
    }
    for row in frame.get("constant_writes") or []:
        if not isinstance(row, Mapping):
            continue
        stage = str(row.get("stage") or "").lower()
        if stage not in banks:
            raise ValueError(f"runtime constant has unsupported stage {stage!r}")
        start = int(row.get("start_register"))
        count = int(row.get("vector4f_count"))
        values = row.get("values")
        if start < 0 or count <= 0 or not isinstance(values, list) or len(values) != count * 4:
            raise ValueError("runtime constant write has invalid shape")
        for index in range(count):
            banks[stage]["c"][start + index] = [
                float(value) for value in values[index * 4:index * 4 + 4]
            ]
    return banks


def _external_requirements(material_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    binding = material_input.get("material_binding")
    rows = binding.get("bindings") if isinstance(binding, Mapping) else material_input.get("bindings")
    requirements = []
    for row in rows or []:
        if not isinstance(row, Mapping) or row.get("binding") != "external-or-specialised":
            continue
        register = row.get("d3d9_sampler_register")
        if register is None:
            continue
        requirements.append({
            "sampler": row.get("sampler"),
            "sampler_type": row.get("sampler_type"),
            "d3d9_sampler_register": int(register),
        })
    return sorted(requirements, key=lambda row: row["d3d9_sampler_register"])


def _texture_requirements(
    frame: Mapping[str, Any],
    external: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    latest: dict[int, Any] = {}
    for row in frame.get("texture_bindings") or []:
        if not isinstance(row, Mapping):
            continue
        stage = int(row.get("stage"))
        latest[stage] = row.get("texture_ptr")
    requirements = []
    blockers = []
    for row in external:
        register = row["d3d9_sampler_register"]
        texture_ptr = latest.get(register)
        status = "bound-object" if texture_ptr else "contents-not-supplied"
        descriptor = {}
        for event in frame.get("texture_bindings") or []:
            if not isinstance(event, Mapping):
                continue
            try:
                event_stage = int(event.get("stage"))
            except (TypeError, ValueError):
                continue
            if event_stage == register and isinstance(event.get("resource_descriptor"), Mapping):
                descriptor = dict(event["resource_descriptor"])
        snapshot_paths: list[str] = []
        snapshot_status = "not-supplied"
        for event in frame.get("texture_bindings") or []:
            if not isinstance(event, Mapping):
                continue
            try:
                event_stage = int(event.get("stage"))
            except (TypeError, ValueError):
                continue
            if event_stage == register:
                snapshot_paths = [str(path) for path in (event.get("snapshot_paths") or [])]
                snapshot_status = str(event.get("snapshot_status") or "not-supplied")
        requirements.append({
            **row,
            "texture_ptr": texture_ptr,
            "resource_descriptor": descriptor,
            "snapshot_status": snapshot_status,
            "snapshot_paths": snapshot_paths,
            "status": status,
        })
        if not texture_ptr:
            blockers.append(f"runtime:texture-object-not-bound:s{register}")
    return requirements, blockers


def build_runtime_render_contract(
    material_input: Mapping[str, Any],
    runtime_report: Mapping[str, Any],
    *,
    primary_bff: str | Path,
    render_bff: str | Path,
    require_external_texture_objects: bool = True,
) -> dict[str, Any]:
    from bmw_runtime_shader_select import select_runtime_shader

    selection = select_runtime_shader(material_input, runtime_report)
    if not selection.get("ready"):
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "reference_render_ready": False,
            "blocking_reasons": list(selection.get("blocking_reasons") or []),
            "selection": selection,
        }

    candidate = _selected_candidate(material_input, selection)
    frame = _runtime_frame(runtime_report, selection)
    identity = frame.get("shader_permutation_identity") or {}
    permutation = candidate.get("permutation_identity") or {}
    vertex_offset = permutation.get("vertex_offset")
    pixel_offset = permutation.get("pixel_offset") or candidate.get("program_offset")
    if vertex_offset is None or pixel_offset is None:
        raise ValueError("selected candidate does not carry exact VS/PS offsets")

    candidate_file = str(candidate.get("file") or "")
    prefix, separator, entry_path = candidate_file.partition("::")
    if not separator:
        raise ValueError("selected FXO candidate must use ARCHIVE::ENTRY provenance")
    if Path(prefix).name != Path(render_bff).name:
        raise ValueError(
            f"selected FXO candidate archive {prefix!r} does not match {Path(render_bff).name!r}"
        )

    with BFF(render_bff) as archive:
        entries = [
            entry for entry in archive.entries
            if str(entry.path).replace("\\", "/").lower() == entry_path.replace("\\", "/").lower()
        ]
        if len(entries) != 1:
            raise ValueError(
                f"selected FXO entry {entry_path!r} must resolve exactly once; found {len(entries)}"
            )
        fxo_bytes = archive.extract_entry(entries[0])

    with BFF(primary_bff) as archive:
        meb_entries = [
            entry for entry in archive.entries
            if str(entry.path).replace("\\", "/").lower() == TARGET_MEB
        ]
        if len(meb_entries) != 1:
            raise ValueError(f"BMW MEB target must resolve exactly once; found {len(meb_entries)}")
        meb_bytes = archive.extract_entry(meb_entries[0])
    mesh = read_meb(meb_bytes)

    linked_pair = translate_pair_blob(
        fxo_bytes,
        int(vertex_offset),
        int(pixel_offset),
        vertex_properties=tuple(mesh.vertex_properties),
    )
    banks = _constant_banks(frame)
    external = _external_requirements(material_input)
    external_requirements, external_blockers = _texture_requirements(frame, external)

    blockers = list(external_blockers) if require_external_texture_objects else []
    reference_ready = not blockers
    return {
        "format": FORMAT,
        "status": "ready" if not blockers else "partial",
        "ready": True,
        "reference_render_ready": reference_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "selection": selection,
        "shader": {
            "candidate": {
                "file": candidate.get("file"),
                "program_offset": candidate.get("program_offset"),
                "pixel_sha256": candidate.get("pixel_sha256"),
                "vertex_sha256": candidate.get("vertex_sha256"),
                "pair_sha256": candidate.get("pair_sha256"),
            },
            "identity": identity,
            "linked_shader_pair": linked_pair,
            "runtime_shader_pointers": {
                "vertex": (frame.get("vertex_shader") or {}).get("shader_ptr"),
                "pixel": (frame.get("pixel_shader") or {}).get("shader_ptr"),
            },
        },
        "constants": {
            "vertex": banks["vertex"],
            "pixel": banks["pixel"],
        },
        "external_textures": external_requirements,
        "mesh": {
            "archive": Path(primary_bff).name,
            "resource": TARGET_MEB,
            "resource_sha256": material_input.get("provenance", {}).get("mesh_entry", {}).get("sha256"),
            "vertex_properties": list(mesh.vertex_properties),
            "vertex_count": mesh.vertex_count,
            "triangle_count": mesh.triangle_count,
        },
        "frame": {
            "frame": frame.get("frame"),
            "draw_index": frame.get("draw_index"),
            "texture_binding_count": len(frame.get("texture_bindings") or []),
            "constant_write_count": len(frame.get("constant_writes") or []),
            "indexed_draw_count": (
                1
                if frame.get("draw_index") is not None
                else len(frame.get("draws") or [])
            ),
        },
        "boundary": {
            "external_texture_contents": "not-supplied",
            "offline_image": "blocked" if not reference_ready else "possible",
            "raw_binaries_committed": False,
        },
    }


def validate_files(
    material_input_path: str | Path,
    runtime_report_path: str | Path,
    *,
    primary_bff: str | Path,
    render_bff: str | Path,
) -> dict[str, Any]:
    material = json.loads(Path(material_input_path).read_text(encoding="utf-8"))
    runtime = json.loads(Path(runtime_report_path).read_text(encoding="utf-8"))
    return build_runtime_render_contract(
        material,
        runtime,
        primary_bff=primary_bff,
        render_bff=render_bff,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the exact BMW runtime render contract from a D3D9 capture"
    )
    parser.add_argument("material_input")
    parser.add_argument("runtime_report")
    parser.add_argument("primary_bff")
    parser.add_argument("render_bff")
    parser.add_argument("output")
    args = parser.parse_args()
    report = validate_files(
        args.material_input,
        args.runtime_report,
        primary_bff=args.primary_bff,
        render_bff=args.render_bff,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "reference_render_ready": report["reference_render_ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
