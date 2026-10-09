import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1d_controller1_loader_argument_flow.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_loader_argument_flow.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_loader_args", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evidence_pins_all_seven_direct_loader_arguments():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Controller1LoaderArgumentFlow/1"
    surface = data["surface"]
    assert surface["worker_reachable_direct_loader_call_count"] == 7
    assert surface["literal_module_argument_count"] == 6
    assert surface["null_current_module_argument_count"] == 1
    calls = {(row["callsite"], row["api"]): row for row in surface["calls"]}
    assert calls[("0x00907490", "GetModuleHandleA")]["argument"] == "mscoree.dll"
    assert calls[("0x0090a9e3", "GetModuleHandleA")]["argument_kind"] == "null-current-module"
    assert calls[("0x0090aa60", "GetModuleHandleA")]["argument"] == "KERNEL32.DLL"
    assert calls[("0x0090aad7", "GetModuleHandleA")]["argument"] == "KERNEL32.DLL"
    assert calls[("0x0090abc9", "GetModuleHandleA")]["argument"] == "KERNEL32.DLL"
    assert calls[("0x00918a16", "GetModuleHandleA")]["argument"] == "kernel32.dll"
    assert calls[("0x0091c0a0", "LoadLibraryA")]["argument"] == "USER32.DLL"


def test_current_module_walk_is_section_lookup_not_export_walk():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    walk = data["current_module_pe_walk"]
    assert walk["loader_call"] == "0x0090a9e3 GetModuleHandleA(NULL)"
    assert walk["section_name"] == ".mixcrt"
    assert walk["e_lfanew_read"] == "0x0090a9e9 mov esi,[eax+0x3c]"
    assert walk["section_stride"] == "0x0090aa12 add edi,0x28"
    assert walk["export_directory_0x78_access_present"] is False
    assert walk["role"] == "current-module section-table lookup, not PE export-directory resolution"


def test_loader_closure_remains_fail_closed_for_indirect_paths():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["all_worker_reachable_direct_loader_arguments_proven"] is True
    assert adj["direct_loader_literal_or_null_surface_complete"] is True
    assert adj["current_module_section_walk_is_export_resolver"] is False
    assert adj["direct_loader_argument_surface_supports_apc_resolution"] is False
    assert adj["indirect_loader_calls_ruled_out"] is False
    assert adj["manual_export_walking_overall_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_machine_anchor_set_covers_null_and_literal_loader_forms():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    anchors = {row["address"]: row["bytes"] for row in data["machine_anchors"]["byte_windows"]}
    assert anchors["0x0090a9c8"] == "33db"
    assert anchors["0x0090a9e2"] == "53"
    assert anchors["0x0090a9e3"] == "ff15d061aa00"
    assert anchors["0x0091c09b"] == "685421b400"
    assert anchors["0x0091c0a0"] == "ff150063aa00"
    literals = {row["address"]: row["value"] for row in data["machine_anchors"]["literal_strings"]}
    assert literals["0x00b384b4"] == ".mixcrt"
    assert literals["0x00b42154"] == "USER32.DLL"
