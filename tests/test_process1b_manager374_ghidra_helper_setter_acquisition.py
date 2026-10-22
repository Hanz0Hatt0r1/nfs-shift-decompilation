from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_p1b_manager374_helper_setter_ghidra_frontier.py"
BOUNDARY_AUDIT = ROOT / "tools" / "ghidra" / "audit_p1b_ghidra_retail_call_boundaries.py"
EXPORTER = ROOT / "tools" / "ghidra" / "ShiftCompactInstructionStreamExporter.java"
FORMAT = "SHIFT.GhidraCompactInstructionStream/1"


def module():
    spec = importlib.util.spec_from_file_location("p1b_ghidra_helper_setter", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def header(**overrides):
    payload = {
        "format": FORMAT,
        "kind": "header",
        "program": "SHIFT.exe",
        "executable_md5": "705af8b420e5eb1e3834ac43d5533c6b",
        "language_id": "x86:LE:32:default",
        "image_base": "0x00400000",
        "pointer_size": 4,
    }
    payload.update(overrides)
    return payload


def insn(address: int, mnemonic: str, operands: list[str] | None = None, flows: list[str] | None = None):
    return {
        "format": FORMAT,
        "kind": "instruction",
        "address": f"0x{address:08x}",
        "mnemonic": mnemonic,
        "operands": operands or [],
        "flow_type": "UNCONDITIONAL_CALL" if mnemonic.lower() == "call" else "FALL_THROUGH",
        "flows": flows or [],
    }


def write_stream(path: Path, rows: list[dict], *, head: dict | None = None) -> None:
    text = "\n".join(json.dumps(row) for row in [head or header(), *rows]) + "\n"
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def three_class_rows():
    return [
        insn(0x1000, "LEA", ["EAX", "[ESI + 0x374]"]),
        insn(0x1006, "MOV", ["ECX", "EAX"]),
        insn(0x1008, "CALL", ["FUN_00003000"], ["0x00003000"]),
        insn(0x100D, "RET"),
        insn(0x1100, "CALL", ["FUN_00004000"], ["0x00004000"]),
        insn(0x1105, "MOV", ["DWORD PTR [EAX]", "EDX"]),
        insn(0x1107, "RET"),
        insn(0x1200, "CALL", ["FUN_00005000"], ["0x00005000"]),
        insn(0x1205, "MOV", ["DWORD PTR [EBP - 0x8]", "EAX"]),
        insn(0x1208, "MOV", ["EDI", "DWORD PTR [EBP - 0x8]"]),
        insn(0x120B, "MOV", ["DWORD PTR [EDI]", "ECX"]),
        insn(0x120D, "RET"),
        insn(0x3000, "MOV", ["DWORD PTR [ECX]", "EDX"]),
        insn(0x3002, "RET"),
        insn(0x4000, "LEA", ["EAX", "[ECX + 0x374]"]),
        insn(0x4006, "RET"),
        insn(0x5000, "LEA", ["EAX", "[EDX + 0x374]"]),
        insn(0x5006, "RET"),
    ]


def test_ghidra_direct_flows_feed_all_three_merged_transport_classes(tmp_path: Path):
    path = tmp_path / "instructions.jsonl"
    write_stream(path, three_class_rows())
    wrapper, frontier, results = module().acquire(path)

    assert wrapper["format"] == "SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1"
    assert wrapper["authority"]["ghidra_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert wrapper["authority"]["known_retail_sha256_cross_pin"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert wrapper["authority"]["raw_executable_sha256_verified_in_this_run"] is False
    assert wrapper["source_stream"]["instruction_count"] == len(three_class_rows())
    assert set(results) == {"direct_call_argument", "helper_return_immediate", "helper_return_stack"}

    surface = frontier["surface"]
    assert surface["write_candidate_count_by_probe"] == {
        "direct_call_argument": 1,
        "helper_return_immediate": 1,
        "helper_return_stack": 1,
    }
    assert surface["write_candidate_record_count"] == 3
    adj = wrapper["adjudication"]
    assert adj["ghidra_helper_setter_probe_bundle_execution_complete"] is True
    assert adj["ghidra_helper_setter_candidate_frontier_composed"] is True
    assert adj["retail_helper_setter_probe_bundle_execution_complete"] is False
    assert adj["retail_helper_setter_candidate_frontier_composed"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_plain_and_gzip_streams_have_same_canonical_instruction_digest(tmp_path: Path):
    plain = tmp_path / "instructions.jsonl"
    compressed = tmp_path / "instructions.jsonl.gz"
    rows = three_class_rows()
    write_stream(plain, rows)
    write_stream(compressed, rows)

    plain_wrapper, _frontier, _results = module().acquire(plain)
    gzip_wrapper, _frontier2, _results2 = module().acquire(compressed)
    assert (
        plain_wrapper["source_stream"]["canonical_instruction_stream_sha256"]
        == gzip_wrapper["source_stream"]["canonical_instruction_stream_sha256"]
    )
    assert plain_wrapper["source_stream"]["file_sha256"] == hashlib.sha256(plain.read_bytes()).hexdigest()
    assert gzip_wrapper["source_stream"]["file_sha256"] == hashlib.sha256(compressed.read_bytes()).hexdigest()


def test_misleading_flow_does_not_turn_memory_indirect_call_into_direct(tmp_path: Path):
    path = tmp_path / "indirect.jsonl"
    rows = [
        insn(0x2000, "LEA", ["ECX", "[ESI + 0x374]"]),
        insn(0x2006, "CALL", ["DWORD PTR [EAX + 0x4]"], ["0x00003000"]),
        insn(0x200A, "RET"),
        insn(0x3000, "MOV", ["DWORD PTR [ECX]", "EDX"]),
        insn(0x3002, "RET"),
    ]
    write_stream(path, rows)
    _wrapper, frontier, _results = module().acquire(path)
    surface = frontier["surface"]
    assert surface["write_candidate_record_count"] == 0
    assert surface["open_boundary_count_by_class"]["materialized_target_indirect_call_argument_boundaries"] == 1


def test_identity_drift_fails_closed(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    write_stream(path, [insn(0x1000, "RET")], head=header(executable_md5="0" * 32))
    with pytest.raises(ValueError, match="unexpected executable MD5"):
        module().acquire(path)


def test_non_monotonic_or_duplicate_instruction_addresses_fail_closed(tmp_path: Path):
    path = tmp_path / "unordered.jsonl"
    write_stream(path, [insn(0x1000, "NOP"), insn(0x1000, "RET")])
    with pytest.raises(ValueError, match="strictly increasing"):
        module().read_stream(path)


def test_direct_symbol_call_uses_ghidra_flow_but_register_call_does_not():
    mod = module()
    assert mod.canonical_operands("call", ["FUN_00401000"], ["0x00401000"]) == "0x00401000"
    assert mod.canonical_operands("call", ["EAX"], ["0x00401000"]) == "EAX"
    assert mod.canonical_operands("call", ["DWORD PTR [EAX]"], ["0x00401000"]) == "DWORD PTR [EAX]"


def test_exporter_is_whole_program_identity_pinned_and_supports_gzip():
    source = EXPORTER.read_text(encoding="utf-8")
    assert 'FORMAT = "SHIFT.GhidraCompactInstructionStream/1"' in source
    assert "currentProgram.getExecutableMD5()" in source
    assert "currentProgram.getLanguageID().toString()" in source
    assert "currentProgram.getImageBase()" in source
    assert "currentProgram.getDefaultPointerSize()" in source
    assert "listing.getInstructions(true)" in source
    assert "instruction.getFlows()" in source
    assert "GZIPOutputStream" in source


def test_retail_boundary_audit_flags_ghidra_call_inside_retail_instruction():
    spec = importlib.util.spec_from_file_location("p1b_call_boundary_audit", BOUNDARY_AUDIT)
    assert spec and spec.loader
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    parse_target = lambda text: int(text, 16) if text.startswith("0x") else None

    result = audit.audit_rows(
        [
            (0x1002, "CALL", "0x00003000"),
            (0x2000, "CALL", "0x00004000"),
            (0x3000, "CALL", "EAX"),
        ],
        [
            (0x1000, 3, "lea", "edx,[ebp-0x18]"),
            (0x2000, 5, "call", "0x00004000"),
        ],
        parse_target,
    )

    assert result["confirmed_retail_direct_call_count"] == 1
    assert result["ghidra_direct_call_boundary_mismatch_count"] == 1
    mismatch = result["ghidra_direct_call_boundary_mismatches"][0]
    assert mismatch["callsite"] == "0x00001002"
    assert mismatch["ghidra_target"] == "0x00003000"
    assert mismatch["reason"] == "inside_retail_instruction"
    assert mismatch["retail_instruction"] == {
        "address": "0x00001000",
        "length": 3,
        "mnemonic": "lea",
        "operands": "edx,[ebp-0x18]",
    }
