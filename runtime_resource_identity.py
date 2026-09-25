"""Shared resource identity policy for runtime evidence consumers."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.RuntimeResourceIdentity/1"


def normalize_resource_path(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).replace("\\", "/").strip("/").lower() or None


def match_resource_identity(
    binding: Mapping[str, Any],
    *,
    expected_sha256: str | None = None,
    expected_path: str | None = None,
) -> tuple[bool | None, str]:
    actual_sha = binding.get("resource_sha256")
    actual_path = normalize_resource_path(binding.get("resource_path"))

    if expected_sha256:
        expected_sha = str(expected_sha256).strip().lower()
        if not actual_sha:
            normalized_expected_path = normalize_resource_path(expected_path)
            if normalized_expected_path and actual_path == normalized_expected_path:
                return False, "path-match-sha-missing"
            return False, "sha-missing"
        if str(actual_sha).strip().lower() == expected_sha:
            return True, "exact-sha-match"
        return False, "sha-mismatch"

    normalized_expected_path = normalize_resource_path(expected_path)
    if normalized_expected_path:
        if not actual_path:
            return False, "path-missing"
        if actual_path == normalized_expected_path:
            return True, "path-match"
        return False, "path-mismatch"

    return None, "identity-not-supplied"
