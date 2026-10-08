from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_0074f560_collision_provider_machine_proof.json"
DOC = ROOT / "docs/PROCESS_1_FUN_0074F560_COLLISION_PROVIDER_MACHINE_PROOF.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_authority_matches_pinned_retail_executable() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Fun0074f560CollisionProviderMachineProof/1"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["authority"]["executable_size"] == 8801792


def test_exact_provider_dispatch_is_pinned() -> None:
    dispatch = _load()["provider_dispatch"]
    assert dispatch["provider_global_pointer"] == "0x00c133ac"
    assert dispatch["virtual_slot_offset"] == "0x1c0"
    assert dispatch["provider_load"].startswith("0x0074f5a1")
    assert dispatch["slot_load"].startswith("0x0074f5eb")
    assert dispatch["indirect_call"] == "0x0074f600: call eax"
    assert dispatch["physx_class_name_proven"] is False


def test_lower_record_joins_back_to_fun_007b0710_cache_abi() -> None:
    payload = _load()
    ring = payload["surface_record_provenance"]
    upper = payload["upper_join"]
    assert ring["record_stride"] == "0x58"
    assert ring["ring_base_global"] == "0x00c1bae0"
    assert upper["fallback_call_site"] == "0x007b0c8e"
    assert upper["returned_record_cache_store"].startswith("0x007b0d17")
    assert payload["p1_2a_adjudication"]["p1_2a_complete_as_typed_external_provider_boundary"] is True
    assert payload["p1_2a_adjudication"]["replacement_with_guessed_track_query_allowed"] is False


def test_documentation_preserves_non_speculative_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in ("0x00c133ac", "+0x1c0", "0x58-byte", "P1.2a", "class name", "guessed track query"):
        assert token in text
