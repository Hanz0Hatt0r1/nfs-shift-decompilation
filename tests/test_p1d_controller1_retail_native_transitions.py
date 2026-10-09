import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_retail_native_transitions.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_retail_native_transition_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_native_transitions", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_objdump_parser_distinguishes_real_transition_from_embedded_bytes():
    module = load_module()
    text = """
  4209c8: 0f 34                 sysenter
  4209ca: e9 6a fd fd ff        jmp    0x400739
  943f05: 89 84 0f 34 40 01 00  mov    DWORD PTR [edi+ecx*1+0x14034],eax
  4d15e6: 80 3d cd 2e be 00 00  cmp    BYTE PTR ds:0xbe2ecd,0x0
  500000: cd 2e                 int    0x2e
"""
    rows = module.parse_instructions(text)
    native = [row for row in rows if module.is_native_transition(row)]
    assert [(row["address"], row["mnemonic"]) for row in native] == [
        ("0x004209c8", "sysenter"),
        ("0x00500000", "int"),
    ]


def test_direct_static_reference_detection_is_exact():
    module = load_module()
    text = """
  401000: e8 c3 f9 01 00        call   0x4209c8
  401005: 75 05                 jne    0x40100c
  4209c8: 0f 34                 sysenter
"""
    rows = module.parse_instructions(text)
    refs = module.direct_static_refs(rows, 0x4209C8)
    assert refs == [{"address": "0x00401000", "asm": "call   0x4209c8"}]


def test_containing_function_keeps_orphan_transition_outside_function_scope():
    module = load_module()
    functions = [
        {"start": 0x420900, "end": 0x4209C2, "address": "0x00420900", "name": "FUN_A", "size": 0xC2},
        {"start": 0x420A00, "end": 0x420A40, "address": "0x00420a00", "name": "FUN_B", "size": 0x40},
    ]
    assert module.containing_function(functions, 0x4209C8) is None


def test_pinned_retail_surface_remains_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1RetailNativeTransitionSurface/1"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    inv = payload["inventory"]
    assert inv["instruction_aligned_native_transition_count"] == 1
    assert inv["sysenter_count"] == 1
    assert inv["int2e_count"] == 0
    assert inv["outside_sized_ghidra_function_count"] == 1
    assert inv["transitions"][0]["address"] == "0x004209c8"
    assert inv["transitions"][0]["direct_static_reference_count"] == 0
    adj = payload["adjudication"]
    assert adj["whole_pe_sysenter_int2e_instruction_surface_bounded"] is True
    assert adj["function_scoped_ghidra_exporter_covers_all_native_transitions"] is False
    assert adj["indirect_entry_to_native_transition_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
