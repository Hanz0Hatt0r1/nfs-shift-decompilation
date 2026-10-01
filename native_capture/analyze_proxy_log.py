#!/usr/bin/env python3
"""Summarize SHIFT D3D9 proxy JSONL startup/render diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HRESULT_NAMES = {
    "0x88760868": "D3DERR_DEVICELOST",
    "0x88760869": "D3DERR_DEVICENOTRESET",
    "0x8876086a": "D3DERR_NOTAVAILABLE",
    "0x8876086c": "D3DERR_INVALIDCALL",
    "0x8876017c": "D3DERR_OUTOFVIDEOMEMORY",
}


def _hr_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return HRESULT_NAMES.get(value.lower())


def analyze_events(events: list[dict[str, Any]], parse_errors: int = 0) -> dict[str, Any]:
    names = [str(item.get("event", "")) for item in events]
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in events:
        by_name.setdefault(str(item.get("event", "")), []).append(item)

    mode = None
    proxy_entries = by_name.get("proxy_direct3dcreate9", [])
    if proxy_entries:
        mode = proxy_entries[-1].get("mode")

    backend = None
    backend_entries = by_name.get("proxy_d3d9_backend_selected", [])
    if backend_entries:
        backend = {
            "source": backend_entries[-1].get("source"),
            "path": backend_entries[-1].get("path"),
        }

    issues: list[dict[str, Any]] = []
    observations: list[str] = []

    if parse_errors:
        issues.append({
            "kind": "malformed-jsonl",
            "count": parse_errors,
            "detail": "one or more capture lines are not valid JSON",
        })

    if not events:
        issues.append({
            "kind": "empty-log",
            "detail": "no D3D9 proxy events were recorded",
        })
    elif not proxy_entries:
        issues.append({
            "kind": "proxy-entry-not-observed",
            "detail": "Direct3DCreate9 never reached the proxy logger",
        })

    if backend:
        observations.append(
            f"D3D9 backend selected from {backend.get('source') or 'unknown'}"
        )

    if by_name.get("proxy_system_d3d9_load_failed"):
        issues.append({
            "kind": "system-d3d9-load-failed",
            "detail": by_name["proxy_system_d3d9_load_failed"][-1],
        })

    if by_name.get("proxy_system_d3d9_missing_required_export"):
        issues.append({
            "kind": "d3d9-backend-missing-required-export",
            "detail": by_name["proxy_system_d3d9_missing_required_export"][-1],
        })

    hook_failures = list(by_name.get("vtable_patch_failed", []))
    hook_failures.extend(by_name.get("d3d9_hook_failed", []))
    hook_failures.extend(
        item for item in by_name.get("d3d9_hooks", [])
        if item.get("installed") is False
    )
    hook_failures.extend(
        item for item in by_name.get("device_hooks", [])
        if item.get("installed") is False
    )
    if hook_failures:
        issues.append({
            "kind": "proxy-hook-installation-failed",
            "count": len(hook_failures),
            "detail": hook_failures[-1],
        })

    create9 = by_name.get("direct3dcreate9_result", [])
    if create9:
        if not bool(create9[-1].get("success")):
            issues.append({
                "kind": "direct3dcreate9-failed",
                "detail": create9[-1],
            })
        else:
            observations.append("system Direct3DCreate9 returned a valid interface")

    create_device = by_name.get("create_device_result", [])
    if mode != "passthrough" and proxy_entries:
        if not create_device:
            issues.append({
                "kind": "create-device-not-observed",
                "detail": "diagnostic/capture mode installed but CreateDevice was not observed",
            })
        elif not bool(create_device[-1].get("success")):
            issue = {
                "kind": "create-device-failed",
                "detail": create_device[-1],
            }
            name = _hr_name(create_device[-1].get("hresult"))
            if name:
                issue["hresult_name"] = name
            issues.append(issue)
        else:
            observations.append("IDirect3D9::CreateDevice succeeded")

    reset_failures = [
        item for item in by_name.get("reset_result", [])
        if not bool(item.get("success"))
    ]
    if reset_failures:
        last = reset_failures[-1]
        issue = {
            "kind": "reset-failed",
            "count": len(reset_failures),
            "detail": last,
        }
        name = _hr_name(last.get("hresult"))
        if name:
            issue["hresult_name"] = name
        issues.append(issue)

    presents = by_name.get("present_result", [])
    failed_presents = [item for item in presents if not bool(item.get("success"))]
    successful_presents = [item for item in presents if bool(item.get("success"))]

    if mode != "passthrough" and create_device and bool(create_device[-1].get("success")):
        if not presents:
            issues.append({
                "kind": "present-not-observed",
                "detail": "device creation succeeded but no Present result was logged",
            })
        elif failed_presents and not successful_presents:
            last = failed_presents[-1]
            issue = {
                "kind": "present-always-failing",
                "count": len(failed_presents),
                "detail": last,
            }
            name = _hr_name(last.get("hresult"))
            if name:
                issue["hresult_name"] = name
            issues.append(issue)
        elif successful_presents:
            observations.append("at least one IDirect3DDevice9::Present succeeded")
            if failed_presents:
                observations.append("Present also failed on some calls; inspect device-loss/reset timing")

    cooperative = by_name.get("test_cooperative_level", [])
    if cooperative:
        last = cooperative[-1]
        issue = {
            "kind": "device-cooperative-level-error",
            "count": len(cooperative),
            "detail": last,
        }
        name = _hr_name(last.get("hresult"))
        if name:
            issue["hresult_name"] = name
        issues.append(issue)

    if successful_presents and not reset_failures:
        diagnosis = "d3d9-presentation-path-alive"
    elif (
        by_name.get("proxy_system_d3d9_load_failed")
        or by_name.get("proxy_system_d3d9_missing_required_export")
    ):
        diagnosis = "system-d3d9-forwarding-failure"
    elif hook_failures:
        diagnosis = "proxy-hook-installation-failure"
    elif create_device and not bool(create_device[-1].get("success")):
        diagnosis = "device-creation-failure"
    elif failed_presents and not successful_presents:
        diagnosis = "device-present-failure"
    elif mode == "passthrough" and create9 and bool(create9[-1].get("success")):
        diagnosis = "passthrough-forwarding-ok"
    elif issues:
        diagnosis = "incomplete-or-failing"
    else:
        diagnosis = "insufficient-evidence"

    return {
        "format": "SHIFT.D3D9ProxyDiagnosticSummary/1",
        "mode": mode,
        "backend": backend,
        "event_count": len(events),
        "parse_error_count": parse_errors,
        "diagnosis": diagnosis,
        "issues": issues,
        "observations": observations,
        "last_event": names[-1] if names else None,
    }


def analyze_log(path: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    parse_errors = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(item, dict):
            events.append(item)
        else:
            parse_errors += 1
    return analyze_events(events, parse_errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args(argv)
    report = analyze_log(args.capture)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if report["parse_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
