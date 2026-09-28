"""Strict gate for native execution of SHIFT RenderCommand/1.

The normal RenderCommand validator checks executable structure. This gate adds
provenance requirements for native backends: every executable shader pair must
carry the complete FXO payload hash and the derived permutation identity.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.NativeSubmissionGate/1"


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def validate_native_submission(command: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if command.get("format") != "SHIFT.RenderCommand/1":
        reasons.append("render-command:invalid-format")

    if command.get("ready") is not True:
        reasons.append("render-command:not-ready")

    validation = command.get("validation") or {}
    if validation.get("valid") is not True:
        reasons.extend(
            validation.get("blocking_reasons") or ["render-command:validation-failed"]
        )

    submeshes = list(command.get("submeshes", []) or [])
    if not submeshes:
        reasons.append("native-submission:no-submeshes")

    for index, submesh in enumerate(submeshes):
        shader = submesh.get("shader") or {}
        payload_hash = shader.get("source_payload_sha256")
        if not _valid_sha256(payload_hash):
            reasons.append(
                f"native-submission:shader-payload-identity-missing:{index}"
            )

        permutation = shader.get("permutation_identity")
        if permutation is None:
            reasons.append(
                f"native-submission:permutation-identity-missing:{index}"
            )
        elif permutation.get("format") != "SHIFT.ShaderPermutationIdentity/1":
            reasons.append(
                f"native-submission:permutation-identity-invalid-format:{index}"
            )
        elif not _valid_sha256(permutation.get("identity_sha256")):
            reasons.append(
                f"native-submission:permutation-identity-invalid-sha256:{index}"
            )

    return {
        "format": FORMAT,
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "submesh_count": len(submeshes),
    }


__all__ = ["FORMAT", "validate_native_submission"]
