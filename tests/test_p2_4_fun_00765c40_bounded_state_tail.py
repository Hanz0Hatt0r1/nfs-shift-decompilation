import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_bounded_state_tail.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_bounded_state_tail.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_BOUNDED_STATE_TAIL.md"


def test_bounded_state_tail_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40BoundedStateTail/1"
    assert payload["ready"] is True
    assert payload["retail_write_surface"] == [
        {"offset": "+0x3660", "site": "0x007661ac", "width": "byte", "proven_value": 1},
        {"offset": "+0x3668", "site": "0x00766381", "width": "qword", "proven_value": None},
        {"offset": "+0x3670", "site": "0x0076638a", "width": "qword", "proven_value": None},
        {"offset": "+0x3678", "site": "0x0076639b", "width": "dword", "proven_value": None},
    ]
    native = payload["native_consumption"]
    assert native["write_block_executed_is_explicit_input"] is True
    assert native["skipped_branch_produces_no_commit"] is True
    assert native["offset_0x3660_literal_one_internalized"] is True
    assert native["computed_payloads_preserved_bit_for_bit"] is True
    assert native["branch_predicate_internalized"] is False
    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_preserves_optional_commit_and_exact_widths() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40BoundedStateTail/1" in text
    assert "std::optional<Fun00765c40BoundedStateTailCommit>" in text
    assert "write_block_executed" in text
    assert "return std::nullopt" in text
    assert "std::uint8_t flag_3660 = 1u" in text
    assert "std::uint64_t state_3668_bits" in text
    assert "std::uint64_t state_3670_bits" in text
    assert "std::uint32_t state_3678_bits" in text
    for value in ("0x3660u", "0x3668u", "0x3670u", "0x3678u"):
        assert value in text


def test_stable_cmake_and_docs_keep_provider_removal_closed() -> None:
    assert "shift_runtime_fun_00765c40_bounded_state_tail_check" in CMAKE.read_text()
    doc = DOC.read_text()
    assert "branch predicate remains external" in doc
    assert "external provider count remains 7" in doc
