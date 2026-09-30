"""Bridge admitted SGB scene objects into the generic RenderBinding pipeline.

Phase 552 proves scene placement, resource identity and numeric world transforms.
This module consumes only those admitted rows and resolves their resource
references through the existing neutral MEB/BMT/FX/FXO pipeline. It never
promotes blocked SGB rows or guesses non-MEB resource semantics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from render_pipeline import build_render_bindings_from_resource_instances
from sgb_resource_factory import classify_sgb_object_resource
from sgb_meshinst_runtime import build_meshinst_runtime_contract

FORMAT = "SHIFT.SGBRenderBindingBridge/1"
ADMISSION_FORMAT = "SHIFT.SGBRenderBindingAdmission/1"


def _matrix16(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def build_sgb_render_binding_bridge(
    admission: Mapping[str, Any],
    ir_root: str | Path,
) -> dict[str, Any]:
    if admission.get("format") != ADMISSION_FORMAT:
        raise ValueError(
            "admission input must be SHIFT.SGBRenderBindingAdmission/1"
        )

    instances: list[dict[str, Any]] = []
    direct_render_instances: list[dict[str, Any]] = []
    resource_adapter_blocked: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    blockers: list[str] = []

    for ordinal, row in enumerate(admission.get("bindings") or []):
        if not isinstance(row, Mapping):
            skipped.append({
                "binding_index": ordinal,
                "reason": "invalid-binding-row",
            })
            continue

        binding_index = int(row.get("binding_index", ordinal))
        scene_gate = row.get("scene_admission") or {}
        if not isinstance(scene_gate, Mapping):
            scene_gate = {}
        admitted = (
            row.get("ready") is True
            and scene_gate.get("admitted_to_generic_render_binding") is True
        )
        if not admitted:
            skipped.append({
                "binding_index": binding_index,
                "reason": "not-scene-admitted",
                "blocking_reasons": list(row.get("blocking_reasons") or []),
            })
            continue

        object_row = row.get("object") or {}
        if not isinstance(object_row, Mapping):
            object_row = {}
        resource_ref = object_row.get("resource_reference")
        world_matrix = _matrix16(object_row.get("world_matrix"))
        row_reasons: list[str] = []
        if not resource_ref:
            row_reasons.append("resource-reference-missing")
        if world_matrix is None:
            row_reasons.append("numeric-world-matrix-not-ready")
        if row_reasons:
            for reason in row_reasons:
                blockers.append(f"binding-{binding_index}:{reason}")
            skipped.append({
                "binding_index": binding_index,
                "reason": "invalid-admitted-row",
                "blocking_reasons": row_reasons,
            })
            continue

        resource_factory = object_row.get("resource_factory")
        if not isinstance(resource_factory, Mapping):
            resource_factory = classify_sgb_object_resource(
                str(resource_ref)
            )

        meshinst_runtime = object_row.get("meshinst_runtime")
        if (
            not isinstance(meshinst_runtime, Mapping)
            and resource_factory.get("factory_type") == 7
        ):
            meshinst_runtime = build_meshinst_runtime_contract(
                str(resource_ref)
            )

        instance = {
            "resource_reference": str(resource_ref),
            "world_matrix": world_matrix,
            "resource_factory": dict(resource_factory),
            "meshinst_runtime": meshinst_runtime,
            "source": {
                "admission_binding_index": binding_index,
                "placement": row.get("placement"),
                "object": {
                    "object_path": object_row.get("object_path"),
                    "wrapper": object_row.get("wrapper"),
                    "transform_mode": object_row.get("transform_mode"),
                    "resource_factory": dict(resource_factory),
                },
            },
        }
        instances.append(instance)

        suffix = Path(str(resource_ref).replace("\\", "/")).suffix.lower()
        if suffix == ".meb":
            direct_render_instances.append(instance)
        else:
            factory_type = resource_factory.get("factory_type")
            if factory_type == 7:
                loader = resource_factory.get("resource_loader") or {}
                loader_mode = loader.get("mode")
                if loader_mode == "xml":
                    adapter_reason = "meshinst-xml-adapter-unimplemented"
                elif loader_mode == "binary":
                    adapter_reason = "meshinst-binary-adapter-incomplete"
                else:
                    adapter_reason = "meshinst-adapter-unimplemented"
            else:
                loader_mode = None
                adapter_reason = "meshtype-adapter-unimplemented"
            blockers.append(
                f"binding-{binding_index}:scene-resource:{adapter_reason}"
            )
            resource_adapter_blocked.append({
                "binding_index": binding_index,
                "resource_reference": str(resource_ref),
                "factory_type": factory_type,
                "factory_name": resource_factory.get("factory_name"),
                "loader_mode": loader_mode,
                "meshinst_runtime": meshinst_runtime,
                "reason": adapter_reason,
            })

    if not instances:
        blockers.append("sgb-render-binding-bridge:no-admitted-bindings")

    render_binding = build_render_bindings_from_resource_instances(
        ir_root,
        direct_render_instances,
        source_format=ADMISSION_FORMAT,
    )

    unresolved = list((render_binding.get("stats") or {}).get("unresolved") or [])
    for item in unresolved:
        binding_index = item.get("admission_binding_index")
        reason = item.get("reason") or item.get("kind") or "unresolved"
        if binding_index is None:
            instance_index = item.get("instance_index")
            if (
                isinstance(instance_index, int)
                and 0 <= instance_index < len(direct_render_instances)
            ):
                binding_index = (
                    direct_render_instances[instance_index].get("source") or {}
                ).get("admission_binding_index")
        prefix = (
            f"binding-{binding_index}"
            if binding_index is not None
            else "resource-instance"
        )
        blockers.append(f"{prefix}:resource-resolution:{reason}")

    resolved_count = int(
        (render_binding.get("stats") or {}).get(
            "resolved_resource_instances",
            0,
        )
    )
    blockers = list(dict.fromkeys(blockers))
    ready = (
        bool(instances)
        and resolved_count == len(instances)
        and not blockers
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source_admission": {
            "format": admission.get("format"),
            "binding_count": admission.get("binding_count"),
            "admitted_binding_count": admission.get("admitted_binding_count"),
            "blocked_binding_count": admission.get("blocked_binding_count"),
        },
        "scene_admitted_instance_count": len(instances),
        "direct_render_instance_count": len(direct_render_instances),
        "resource_adapter_blocked_count": len(resource_adapter_blocked),
        "resolved_instance_count": resolved_count,
        "unresolved_instance_count": len(instances) - resolved_count,
        "resource_adapter_blocked": resource_adapter_blocked,
        "skipped_bindings": skipped,
        "render_binding": render_binding,
        "boundary": {
            "retail_resource_factory": "MeshType(type 0) / MeshInst(type 7)",
            "meshinst_extensions": ["imb", "imx"],
            "direct_neutral_adapter": "MEB only",
            "resource_pipeline": "MEB -> BMT/MTX -> FX/FXO -> SHIFT.RenderBinding/1",
            "meshtype_equals_meb": False,
            "meshinst_equals_meb": False,
            "world_matrix_source": "SHIFT.SGBRenderBindingAdmission/1",
            "blocked_scene_rows_promoted": False,
            "generic_render_binding_packets_emitted": True,
            "draw_admission": (
                "delegated to existing StaticDraw/RenderCommand gates"
            ),
        },
    }


def validate_file(
    admission_path: str | Path,
    ir_root: str | Path,
) -> dict[str, Any]:
    value = json.loads(Path(admission_path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("SGB admission JSON must be an object")
    return build_sgb_render_binding_bridge(value, ir_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve scene-admitted SGB resources into RenderBinding"
    )
    parser.add_argument("admission")
    parser.add_argument("ir_root")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_file(args.admission, args.ir_root)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "scene_admitted_instance_count": report[
            "scene_admitted_instance_count"
        ],
        "direct_render_instance_count": report[
            "direct_render_instance_count"
        ],
        "resource_adapter_blocked_count": report[
            "resource_adapter_blocked_count"
        ],
        "resolved_instance_count": report["resolved_instance_count"],
        "unresolved_instance_count": report["unresolved_instance_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
