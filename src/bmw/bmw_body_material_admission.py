"""Orchestrate canonical BMW M3 body primitive material admission.

Per-primitive failures remain independent. A blocked non-paint material does
not erase evidence from already-ready primitives, while the top-level ready
bit remains strict: every selected canonical primitive and the combined slice
set must validate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from bmw_material_slice_set import build_bmw_material_slice_set
from bmw_material_vulkan_adapter import build_bmw_vulkan_set_from_material_slice
from bmw_real_material_slice import build_real_bmw_material_slice

FORMAT = "SHIFT.BMWBodyMaterialAdmission/1"
DEFAULT_GOLDEN = "evidence/bmw_m3_e36_kit00_body_loda.golden.json"


def _load_golden(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("BMW golden manifest must be a JSON object")
    if value.get("format") != "SHIFT.BMWGoldenAssetManifest/1":
        raise ValueError("BMW golden manifest has an invalid format")
    return value


def _canonical_indices(
    golden: dict[str, Any],
    primitive_indices: Iterable[int] | None,
) -> list[int]:
    primitives = list((golden.get("mesh") or {}).get("primitives") or [])
    if not primitives:
        raise ValueError("BMW golden manifest has no mesh primitives")
    if primitive_indices is None:
        return list(range(len(primitives)))

    indices = [int(index) for index in primitive_indices]
    if not indices:
        raise ValueError("BMW body admission requires at least one primitive")
    if len(indices) != len(set(indices)):
        raise ValueError("BMW body admission primitive indices must be unique")
    for index in indices:
        if index < 0 or index >= len(primitives):
            raise ValueError(
                f"BMW body admission primitive index out of range: {index}"
            )
    return sorted(indices)


def _permutation_identity(material_slice: dict[str, Any]) -> str | None:
    submeshes = list(
        ((material_slice.get("render_command") or {}).get("submeshes") or [])
    )
    if len(submeshes) == 1:
        shader = submeshes[0].get("shader") or {}
        permutation = shader.get("permutation_identity") or {}
        identity = str(permutation.get("identity_sha256") or "")
        if len(identity) == 64:
            return identity

    binding = material_slice.get("material_binding") or {}
    permutation = binding.get("permutation_identity") or {}
    identity = str(permutation.get("identity_sha256") or "")
    return identity if len(identity) == 64 else None


def _summary(
    primitive_index: int,
    material_slice: dict[str, Any] | None,
    error: Exception | None = None,
) -> dict[str, Any]:
    if material_slice is None:
        return {
            "primitive_index": primitive_index,
            "status": "error",
            "ready": False,
            "material_ref": None,
            "material_bmt": None,
            "shader_permutation_identity_sha256": None,
            "blocking_reasons": [
                f"body-admission:primitive-{primitive_index}:"
                f"{type(error).__name__}:{error}"
            ],
        }

    return {
        "primitive_index": primitive_index,
        "status": material_slice.get("status"),
        "ready": material_slice.get("ready") is True,
        "material_ref": material_slice.get("material_ref"),
        "material_bmt": material_slice.get("material_bmt"),
        "shader_permutation_identity_sha256": _permutation_identity(
            material_slice
        ),
        "blocking_reasons": [
            str(reason)
            for reason in material_slice.get("blocking_reasons") or []
        ],
    }


def build_bmw_body_material_admission(
    primary_bff: str | Path,
    golden_manifest: str | Path = DEFAULT_GOLDEN,
    *,
    supplemental_bffs: Iterable[str | Path] = (),
    primitive_indices: Iterable[int] | None = None,
    color_abi_report: str | Path | None = None,
    vulkan_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run selected canonical BMW body primitives through the retail path."""
    golden = _load_golden(golden_manifest)
    indices = _canonical_indices(golden, primitive_indices)
    supplemental = [Path(path) for path in supplemental_bffs]
    primary = Path(primary_bff)

    primitive_results: list[dict[str, Any]] = []
    ready_slices: list[dict[str, Any]] = []
    blockers: list[str] = []

    for index in indices:
        material_slice: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            material_slice = build_real_bmw_material_slice(
                primary,
                golden_manifest,
                primitive_index=index,
                supplemental_bffs=supplemental,
                color_abi_report=color_abi_report,
            )
        except Exception as exc:
            error = exc

        row = _summary(index, material_slice, error)
        primitive_results.append({**row, "slice": material_slice})

        if row["ready"] and material_slice is not None:
            ready_slices.append(material_slice)
        else:
            reasons = row["blocking_reasons"] or [
                f"body-admission:primitive-{index}:not-ready"
            ]
            blockers.extend(
                str(reason)
                if str(reason).startswith(
                    f"body-admission:primitive-{index}:"
                )
                else f"body-admission:primitive-{index}:{reason}"
                for reason in reasons
            )

    slice_set: dict[str, Any] | None = None
    if ready_slices:
        slice_set = build_bmw_material_slice_set(ready_slices)
        if slice_set.get("ready") is not True:
            blockers.extend(
                f"body-admission:slice-set:{reason}"
                for reason in (
                    slice_set.get("blocking_reasons") or ["not-ready"]
                )
            )

    identities = [
        row["shader_permutation_identity_sha256"]
        for row in primitive_results
        if row["ready"] and row["shader_permutation_identity_sha256"]
    ]
    permutation_counts = Counter(identities)
    permutations = [
        {
            "identity_sha256": identity,
            "primitive_count": permutation_counts[identity],
            "primitive_indices": [
                row["primitive_index"]
                for row in primitive_results
                if row["ready"]
                and row["shader_permutation_identity_sha256"] == identity
            ],
            "material_refs": sorted({
                str(row["material_ref"])
                for row in primitive_results
                if row["ready"]
                and row["shader_permutation_identity_sha256"] == identity
                and row["material_ref"]
            }),
        }
        for identity in sorted(permutation_counts)
    ]

    vulkan_set: dict[str, Any] | None = None
    if (
        vulkan_output_dir is not None
        and slice_set is not None
        and slice_set.get("ready") is True
    ):
        vulkan_set = build_bmw_vulkan_set_from_material_slice(
            slice_set,
            vulkan_output_dir,
            source_bffs=[primary, *supplemental],
        )
        if vulkan_set.get("ready") is not True:
            blockers.extend(
                f"body-admission:vulkan-set:{reason}"
                for reason in (
                    vulkan_set.get("blocking_reasons") or ["not-ready"]
                )
            )

    ready_count = len(ready_slices)
    complete = (
        ready_count == len(indices)
        and slice_set is not None
        and slice_set.get("ready") is True
        and (
            vulkan_output_dir is None
            or (
                vulkan_set is not None
                and vulkan_set.get("ready") is True
            )
        )
        and not blockers
    )
    status = "ready" if complete else ("partial" if ready_count else "blocked")

    canonical = list((golden.get("mesh") or {}).get("primitives") or [])
    selected_materials = [
        {
            "primitive_index": index,
            "first_index": canonical[index].get("first_index"),
            "index_count": canonical[index].get("index_count"),
            "material": canonical[index].get("material"),
        }
        for index in indices
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": complete,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "primary_bff": primary.name,
            "supplemental_bffs": [path.name for path in supplemental],
            "golden_manifest": str(golden_manifest),
            "color_abi_report": (
                str(color_abi_report)
                if color_abi_report is not None
                else None
            ),
        },
        "selection": {
            "primitive_indices": indices,
            "canonical_primitives": selected_materials,
            "selected_count": len(indices),
        },
        "admission": {
            "ready_primitive_count": ready_count,
            "blocked_primitive_count": len(indices) - ready_count,
            "distinct_ready_permutation_count": len(permutations),
            "ready_primitive_indices": [
                row["primitive_index"]
                for row in primitive_results
                if row["ready"]
            ],
            "blocked_primitive_indices": [
                row["primitive_index"]
                for row in primitive_results
                if not row["ready"]
            ],
            "permutations": permutations,
        },
        "primitive_results": primitive_results,
        "material_slice_set": slice_set,
        "vulkan_set": vulkan_set,
        "boundary": {
            "complete_body_requires_every_selected_primitive": True,
            "partial_ready_slices_are_preserved": True,
            "native_multidraw_requested": vulkan_output_dir is not None,
            "runtime_instance_attribution": "not-proven",
        },
    }


def write_bmw_body_material_admission(
    report: dict[str, Any],
    output_dir: str | Path,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    slices = root / "slices"
    slices.mkdir(parents=True, exist_ok=True)

    for row in report.get("primitive_results") or []:
        payload = row.get("slice")
        if isinstance(payload, dict):
            path = slices / f"primitive_{int(row['primitive_index']):02d}.json"
            path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

    slice_set = report.get("material_slice_set")
    if isinstance(slice_set, dict):
        (root / "material_slice_set.json").write_text(
            json.dumps(
                slice_set,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    path = root / "admission.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run canonical BMW body primitives through retail material admission"
    )
    parser.add_argument("primary_bff")
    parser.add_argument("output_dir")
    parser.add_argument("--golden", default=DEFAULT_GOLDEN)
    parser.add_argument("--supplemental-bff", action="append", default=[])
    parser.add_argument("--primitive-index", action="append", type=int)
    parser.add_argument("--color-abi-report")
    parser.add_argument("--vulkan-output-dir")
    args = parser.parse_args(argv)

    report = build_bmw_body_material_admission(
        args.primary_bff,
        args.golden,
        supplemental_bffs=args.supplemental_bff,
        primitive_indices=args.primitive_index,
        color_abi_report=args.color_abi_report,
        vulkan_output_dir=args.vulkan_output_dir,
    )
    output = write_bmw_body_material_admission(report, args.output_dir)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "ready_primitive_count": report["admission"][
            "ready_primitive_count"
        ],
        "blocked_primitive_count": report["admission"][
            "blocked_primitive_count"
        ],
        "distinct_ready_permutation_count": report["admission"][
            "distinct_ready_permutation_count"
        ],
        "output": str(output),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
