from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1d_controller1_native_apc_primitives.py"
EXPORTER = ROOT / "tools/ghidra/ShiftNativeResolutionPrimitiveExporter.java"
DOC = ROOT / "docs/PROCESS_1D_CONTROLLER1_NATIVE_APC_PRIMITIVE_FRONTIER.md"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_native_apc", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(function: str, address: str, text: str, **flags):
    payload = {
        "format": "SHIFT.GhidraNativeResolutionPrimitiveInventory/1",
        "program": "SHIFT.exe",
        "function": function,
        "function_address": "0x00401000",
        "address": address,
        "mnemonic": text.split(" ", 1)[0],
        "text": text,
        "fs_access": False,
        "sysenter": False,
        "int2e": False,
        "export_offset_hint": False,
    }
    payload.update(flags)
    return payload


def test_manual_export_walk_candidate_requires_peb_and_pe_offsets():
    module = load_module()
    rows = [
        row("FUN_00401000", "0x00401010", "MOV EAX,FS:[0x30]", fs_access=True, export_offset_hint=True),
        row("FUN_00401000", "0x00401020", "MOV EDX,dword ptr [EAX + 0x3c]", export_offset_hint=True),
        row("FUN_00401000", "0x00401030", "MOV ECX,dword ptr [EDX + 0x78]", export_offset_hint=True),
    ]
    payload = module.classify(rows)
    assert payload["candidate_function_count"] == 1
    candidate = payload["candidate_functions"][0]
    assert candidate["manual_export_walk_candidate"] is True
    assert candidate["direct_native_call_candidate"] is False
    assert candidate["peb_access_sites"] == ["0x00401010"]


def test_peb_access_alone_is_not_promoted():
    module = load_module()
    payload = module.classify([
        row("FUN_00402000", "0x00402010", "MOV EAX,FS:[0x30]", fs_access=True, export_offset_hint=True)
    ])
    assert payload["candidate_function_count"] == 0


def test_sysenter_and_int2e_are_native_candidates_only():
    module = load_module()
    payload = module.classify([
        row("FUN_00403000", "0x00403010", "SYSENTER", sysenter=True),
        row("FUN_00404000", "0x00404010", "INT 0x2e", int2e=True),
    ])
    assert payload["candidate_function_count"] == 2
    assert all(item["direct_native_call_candidate"] is True for item in payload["candidate_functions"])
    assert payload["adjudication"]["candidate_presence_proves_apc_injection"] is False
    assert payload["adjudication"]["native_or_syscall_apc_injection_ruled_out"] is False
    assert payload["adjudication"]["controller1_timing_exhaustive"] is False
    assert payload["adjudication"]["external_provider_count"] == 7


def test_exporter_and_doc_preserve_fail_closed_scope():
    exporter = EXPORTER.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    assert "SYSENTER" in exporter or "sysenter" in exporter
    assert "0x2e" in exporter
    assert "fs:" in exporter.lower()
    assert "manual export" in doc.lower()
    assert "not" in doc.lower() and "no-apc" in doc.lower()
    assert "Controller #1" in doc
