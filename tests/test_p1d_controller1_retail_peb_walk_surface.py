import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_retail_peb_walk_surface.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_retail_peb_walk_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_peb_walk", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fs30_detector_accepts_direct_and_bracketed_forms():
    module = load_module()
    assert module.fs30_access({"asm": "mov eax,fs:0x30"}) is True
    assert module.fs30_access({"asm": "mov eax,DWORD PTR fs:[0x30]"}) is True
    assert module.fs30_access({"asm": "mov eax,fs:0x0"}) is False


def test_objdump_parser_preserves_fs_operands():
    module = load_module()
    rows = module.parse_instructions(
        """
  401000: 64 a1 30 00 00 00     mov    eax,fs:0x30
  401006: 64 a1 00 00 00 00     mov    eax,fs:0x0
"""
    )
    assert len(rows) == 2
    assert module.fs30_access(rows[0]) is True
    assert module.fs30_access(rows[1]) is False


def test_pinned_retail_peb_surface_is_negative_but_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1RetailPebWalkSurface/1"
    assert payload["inventory"]["instruction_count"] == 2845103
    assert payload["inventory"]["fs_segment_instruction_count"] == 3458
    assert payload["inventory"]["fs30_peb_access_count"] == 0
    adj = payload["adjudication"]
    assert adj["whole_pe_fs30_surface_bounded"] is True
    assert adj["standard_fs30_peb_entry_present"] is False
    assert adj["standard_fs30_peb_export_walk_ruled_out"] is True
    assert adj["all_manual_export_resolution_ruled_out"] is False
    assert adj["loader_api_or_import_derived_module_base_ruled_out"] is False
    assert adj["generated_or_runtime_code_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
