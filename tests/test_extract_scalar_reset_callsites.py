from pathlib import Path

import tools.extract_scalar_reset_callsites as tool
from specialized_provider_scalar_reset_callsite_extractor_runtime import (
    extract_scalar_reset_callsites,
    validate_extracted_callsite_contract,
)


DISASSEMBLY = """
  7b4024: e8 e7 e1 ff ff        call   0x7b2210
  7b402f: e8 dc e1 ff ff        call   0x7b2210
  7b403a: e8 d1 e1 ff ff        call   0x7b2210
  7b4079: e8 92 e1 ff ff        call   0x7b2210
  7b4084: e8 87 e1 ff ff        call   0x7b2210
  7b40c6: e8 45 e1 ff ff        call   0x7b2210
"""


def test_parse_direct_calls_extracts_call_and_return_addresses():
    result = extract_scalar_reset_callsites(
        DISASSEMBLY,
    )

    assert result["call_count"] == 6
    assert result["return_addresses"] == [
        "0x7b4029",
        "0x7b4034",
        "0x7b403f",
        "0x7b407e",
        "0x7b4089",
        "0x7b40cb",
    ]


def test_extracted_callsite_contract_validates_instruction_sizes():
    result = extract_scalar_reset_callsites(
        DISASSEMBLY,
    )
    validation = validate_extracted_callsite_contract(result)

    assert validation["ready"] is True
    assert validation["errors"] == []


def test_cli_analysis_can_compare_against_phase486_table(monkeypatch):
    monkeypatch.setattr(
        tool,
        "_run_objdump",
        lambda executable, objdump, start, stop: DISASSEMBLY,
    )

    result = tool.analyze_executable(
        Path("SHIFT.exe"),
    )

    assert result["ready"] is True
    assert result["extracted"]["call_count"] == 6
    assert result["expected_comparison"]["ready"] is True


def test_cli_parser_defaults_to_known_fun_007b3f40_range():
    parser = tool.build_parser()
    args = parser.parse_args(["SHIFT.exe"])

    assert args.start == 0x007B3F40
    assert args.stop == 0x007B410A
    assert args.target == 0x007B2210


def test_cli_rejects_missing_objdump(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda _: None)

    try:
        tool._run_objdump(
            Path("SHIFT.exe"),
            objdump="objdump",
            start=0x007B3F40,
            stop=0x007B410A,
        )
    except RuntimeError as exc:
        assert "objdump not found" in str(exc)
    else:
        raise AssertionError("missing objdump was not rejected")
