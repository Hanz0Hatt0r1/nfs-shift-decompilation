from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_direct_caller_accumulator_surface.json"
EARLY = ROOT / "evidence/fun_00766510_early_response_branch_ownership.json"
OPTIONAL = ROOT / "evidence/fun_00766510_optional_response_branch_ownership.json"
PRIMARY = ROOT / "evidence/fun_00766510_primary_caller_accumulator.json"
LATER = ROOT / "evidence/fun_00766510_later_response_branch_ownership.json"
AUX_HEADER = ROOT / "native_runtime/include/shift_aux_contact_response.hpp"
DOC = ROOT / "docs/PROCESS_1_FUN_00766510_DIRECT_CALLER_ACCUMULATOR_SURFACE.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_direct_caller_surface_accounts_for_all_four_inventory_sites() -> None:
    payload = _load(EVIDENCE)
    assert payload["format"] == "SHIFT.Fun00766510DirectCallerAccumulatorSurface/1"
    assert payload["ready"] is True
    assert payload["authority"]["semantic_platform"] == "PC retail 1.02"
    assert payload["authority"]["new_machine_or_source_claims_in_this_join"] is False
    inventory = payload["inventory_basis"]
    assert inventory["direct_FUN_00753650_add_sites_in_FUN_00766510"] == 4
    assert inventory["auxiliary_FUN_00758fc0_calls"] == 2
    assert inventory["final_transformed_vector_add_site"] == 1
    accumulator = payload["accumulator"]
    assert accumulator["direct_site_count_expected"] == 4
    assert accumulator["direct_site_count_accounted"] == 4
    assert accumulator["all_direct_FUN_00753650_sites_accounted"] is True
    assert accumulator["direct_surface_complete"] is True


def test_direct_sites_match_existing_positive_contracts() -> None:
    payload = _load(EVIDENCE)
    sites = {row["id"]: row for row in payload["direct_sites"]}
    assert list(sites) == ["early_3b20", "optional_3c60", "primary_3950", "later_3a40"]
    early = _load(EARLY)
    optional = _load(OPTIONAL)
    primary = _load(PRIMARY)
    later = _load(LATER)
    assert early["format"] == sites["early_3b20"]["contract"]
    assert early["runtime_branch"]["caller_accumulator_write_line"] == sites["early_3b20"]["caller_accumulator_write_line"] == 759558
    assert optional["format"] == sites["optional_3c60"]["contract"]
    assert optional["runtime_branch"]["caller_accumulator_line"] == sites["optional_3c60"]["caller_accumulator_write_line"] == 759621
    assert optional["runtime_branch"]["gate"] == sites["optional_3c60"]["gate"]
    assert primary["format"] == sites["primary_3950"]["contract"]
    assert primary["source"]["primary_application_source_lines"] == sites["primary_3950"]["source_window"] == [759686, 759692]
    assert primary["source"]["cross_and_caller_store_span"]["raw_byte_sha256"] == sites["primary_3950"]["cross_and_store_machine_sha256"]
    assert later["format"] == sites["later_3a40"]["contract"]
    assert later["runtime_branch"]["cross_product_line"] == sites["later_3a40"]["cross_product_line"] == 759731
    assert later["runtime_branch"]["caller_accumulator_line"] == sites["later_3a40"]["caller_accumulator_write_line"] == 759732
    assert all(row["owner_closed"] is True for row in sites.values())


def test_auxiliary_pair_is_adjacent_positive_input_not_direct_site() -> None:
    payload = _load(EVIDENCE)
    pair = payload["adjacent_positive_inputs"]["auxiliary_pair"]
    assert pair["format"] == "SHIFT.NativeAuxContactPair/1"
    assert pair["callee"] == "FUN_00758fc0"
    assert pair["record_count"] == 2
    assert pair["record_offsets"] == ["0x37d8", "0x3858"]
    assert pair["direct_surface_member"] is False
    text = AUX_HEADER.read_text(encoding="utf-8")
    assert "kAuxContactRecordCount = 2u" in text
    assert "kAuxContactRecordOffsets = {0x37d8u, 0x3858u}" in text


def test_direct_surface_closure_does_not_overclaim_p1_1c() -> None:
    payload = _load(EVIDENCE)
    assert len(payload["remaining_p1_1c"]) == 3
    gate = payload["adjudication"]
    assert gate["four_direct_caller_cross_product_sites_closed"] is True
    assert gate["whole_caller_accumulator_closed"] is False
    assert gate["p1_1c_complete"] is False
    assert gate["contact_response_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7
    text = DOC.read_text(encoding="utf-8")
    for token in ("exactly four direct", "759558", "759621", "759686–759692", "759732", "FUN_00758fc0", "final transformed cumulative-response vector", "contact_response", "NEXT_STEP"):
        assert token in text
