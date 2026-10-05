"""Fail-closed consumer for the proven BMW Vehicle Render Model resource join.

This module consumes ``SHIFT.BMWVehicleRenderModelResourceJoin/1`` as an
upstream Process 1 contract.  It does not rediscover vehicle resource identity
and it never treats basenames, archive order, or visual similarity as selection
authority.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
TARGET_VEHICLE = "BMW_M3_E36"
TARGET_PROPERTY = "Vehicle Render Model"
TARGET_PROPERTY_VALUE = "BMW_M3_E36.vhf"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
CANONICAL_ARCHIVE = "BMW_M3_E36.bff"
COCKPIT_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36_cockpit.vhf"
DEFAULT_JOIN = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "process1_bmw_vehicle_render_model_resource_join.json"
)


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").casefold()


def _load(value: str | Path | Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        value = DEFAULT_JOIN
    if isinstance(value, Mapping):
        payload = deepcopy(dict(value))
    else:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("BMW render-model resource join must be a JSON object")
    return payload


def _sha256(value: Any, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{label} SHA-256 is missing or invalid")
    return text


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} is invalid")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is invalid") from exc
    if result < 0:
        raise ValueError(f"{label} is invalid")
    return result


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result <= 0:
        raise ValueError(f"{label} is invalid")
    return result


def load_bmw_vehicle_render_model_resource_join(
    value: str | Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load and validate the positive Process 1 BMW render-model handoff."""
    payload = _load(value)
    if payload.get("format") != FORMAT:
        raise ValueError(f"BMW render-model join must be {FORMAT}")
    if payload.get("ready") is not True:
        raise ValueError("BMW render-model join is not ready")

    selected = payload.get("selected_vehicle_descriptor")
    if not isinstance(selected, Mapping):
        raise ValueError("BMW render-model join has no selected vehicle descriptor")
    if str(selected.get("vehicle_name") or "") != TARGET_VEHICLE:
        raise ValueError("BMW render-model join targets the wrong vehicle")
    if str(selected.get("property_name") or "") != TARGET_PROPERTY:
        raise ValueError("BMW render-model join does not identify Vehicle Render Model")
    if str(selected.get("property_value") or "") != TARGET_PROPERTY_VALUE:
        raise ValueError("BMW render-model property value is not the proven BMW primary VHF")
    if selected.get("selected_BMW_vehicle_render_model_value_ready") is not True:
        raise ValueError("BMW Vehicle Render Model value is not positive")

    canonical = payload.get("canonical_bmw_vhf_resource")
    if not isinstance(canonical, Mapping):
        raise ValueError("BMW render-model join has no canonical VHF resource")
    if _norm(canonical.get("resolved_path")) != _norm(CANONICAL_VHF):
        raise ValueError("canonical BMW VHF path is not the playable-slice resource")
    if str(canonical.get("archive") or "") != CANONICAL_ARCHIVE:
        raise ValueError("canonical BMW VHF archive is not BMW_M3_E36.bff")
    canonical_archive_sha = _sha256(
        canonical.get("archive_sha256"),
        "canonical BMW VHF archive",
    )
    canonical_entry_index = _nonnegative_int(
        canonical.get("entry_index"),
        "canonical BMW VHF entry index",
    )
    canonical_decoded_sha = _sha256(
        canonical.get("decoded_sha256"),
        "canonical BMW VHF decoded payload",
    )
    canonical_decoded_size = _positive_int(
        canonical.get("uncompressed_size"),
        "canonical BMW VHF decoded size",
    )
    if canonical.get("canonical_BMW_VHF_resource_join_ready") is not True:
        raise ValueError("canonical BMW VHF resource join is not positive")
    if str(canonical.get("root_tag") or "") != "CAR":
        raise ValueError("canonical BMW VHF root tag is not CAR")
    if str(canonical.get("root_name") or "") != TARGET_VEHICLE:
        raise ValueError("canonical BMW VHF root name disagrees with selected vehicle")
    if str(canonical.get("root_node_type") or "") != "HIERARCHY":
        raise ValueError("canonical BMW VHF root is not a HIERARCHY")

    negative = payload.get("negative_disambiguation")
    if not isinstance(negative, Mapping):
        raise ValueError("BMW render-model join has no cockpit negative disambiguation")
    cockpit_archive_sha = _sha256(
        negative.get("BMW_M3_E36_Cockpit.bff_sha256"),
        "BMW cockpit archive",
    )
    if _norm(negative.get("cockpit_vhf_path")) != _norm(COCKPIT_VHF):
        raise ValueError("BMW cockpit VHF negative identity is missing")
    if negative.get("cockpit_does_not_match_selected_vehicle_render_model") is not True:
        raise ValueError("BMW cockpit VHF is not explicitly excluded")
    if _norm(negative.get("cockpit_vhf_path")) == _norm(canonical.get("resolved_path")):
        raise ValueError("BMW primary and cockpit VHF identities collapsed")

    scope = payload.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("BMW render-model join scope is missing")
    if scope.get("basename_only_fallback_used") is not False:
        raise ValueError("BMW render-model join used basename-only fallback")
    if scope.get("archive_order_fallback_used") is not False:
        raise ValueError("BMW render-model join used archive-order fallback")

    result = deepcopy(payload)
    result["canonical_bmw_vhf_resource"] = {
        **dict(canonical),
        "resolved_path": CANONICAL_VHF,
        "archive": CANONICAL_ARCHIVE,
        "archive_sha256": canonical_archive_sha,
        "entry_index": canonical_entry_index,
        "decoded_sha256": canonical_decoded_sha,
        "uncompressed_size": canonical_decoded_size,
    }
    result["negative_disambiguation"] = {
        **dict(negative),
        "BMW_M3_E36_Cockpit.bff_sha256": cockpit_archive_sha,
        "cockpit_vhf_path": COCKPIT_VHF,
    }
    return result


def validate_vhf_identity_against_render_model_join(
    observed: Mapping[str, Any],
    join: str | Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Require an observed VHF resource to equal the exact Process 1 identity."""
    proof = load_bmw_vehicle_render_model_resource_join(join)
    expected = proof["canonical_bmw_vhf_resource"]

    archive = str(observed.get("archive") or "")
    archive_sha = _sha256(observed.get("archive_sha256"), "observed BMW VHF archive")
    entry_index = _nonnegative_int(observed.get("entry_index"), "observed BMW VHF entry index")
    path = str(observed.get("path") or "")
    decoded_sha = _sha256(
        observed.get("decoded_sha256"),
        "observed BMW VHF decoded payload",
    )
    decoded_size = _positive_int(
        observed.get("decoded_size"),
        "observed BMW VHF decoded size",
    )

    if archive != expected["archive"]:
        raise ValueError("observed BMW VHF archive disagrees with Process 1 resource join")
    if archive_sha != expected["archive_sha256"]:
        raise ValueError("observed BMW VHF archive SHA-256 disagrees with Process 1 resource join")
    if entry_index != expected["entry_index"]:
        raise ValueError("observed BMW VHF entry index disagrees with Process 1 resource join")
    if _norm(path) != _norm(expected["resolved_path"]):
        raise ValueError("observed BMW VHF exact path disagrees with Process 1 resource join")
    if decoded_sha != expected["decoded_sha256"]:
        raise ValueError("observed BMW VHF decoded SHA-256 disagrees with Process 1 resource join")
    if decoded_size != expected["uncompressed_size"]:
        raise ValueError("observed BMW VHF decoded size disagrees with Process 1 resource join")
    if _norm(path) == _norm(proof["negative_disambiguation"]["cockpit_vhf_path"]):
        raise ValueError("BMW cockpit VHF cannot satisfy the primary render-model resource join")

    return {
        "format": FORMAT,
        "ready": True,
        "canonical_primary_vhf": expected["resolved_path"],
        "archive": archive,
        "archive_sha256": archive_sha,
        "entry_index": entry_index,
        "decoded_sha256": decoded_sha,
        "decoded_size": decoded_size,
        "basename_fallback_used": False,
        "cockpit_substitution_rejected": True,
    }
