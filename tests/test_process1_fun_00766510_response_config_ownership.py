from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_response_config_ownership.json"
ANALYZER = ROOT / "tools/ghidra/analyze_fun_00766510_response_config.py"


def test_response_config_ownership_contract_is_positive_and_narrow() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510ResponseConfigOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False
    assert payload["setup_owner"]["vehicle_setup_function"] == "FUN_0076b280"
    assert payload["setup_owner"]["response_setup_function"] == "FUN_00756bb0"

    fields = payload["fields"]
    assert fields["HDVehicle+0x3910"]["source"] == "setup_param_2+0x730"
    assert fields["HDVehicle+0x3910"]["direct_writer_count"] == 1
    assert fields["HDVehicle+0x3918"]["source"] == [
        "setup_param_2+0x738",
        "setup_param_2+0x740",
        "setup_param_2+0x748",
    ]
    table = fields["HDVehicle+0x3950[6]"]
    assert table["source_record_base"] == "setup_param_2+0x750"
    assert table["source_record_stride"] == "0x48 bytes"
    assert table["source_record_count"] == 6


def test_plus_3908_is_persistent_derived_state_not_setup_constant() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    field = payload["fields"]["HDVehicle+0x3908"]
    assert field["writer"] == "FUN_00756ac0"
    assert field["direct_writer_count"] == 1
    assert field["formula"] == "(+0x3750*s*s) + (+0x3748*s) + (+0x3740)"
    assert field["selector_state"] == "HDVehicle+0x3c78"
    assert field["post_setup_refresh"]["source_visible_recompute_anchor_lines"] == [
        752606,
        752728,
        761370,
    ]
    assert payload["adjudication"]["plus_3908_is_setup_constant"] is False
    assert payload["adjudication"]["plus_3908_requires_persistent_state_and_mutation_hooks"] is True
    assert payload["adjudication"]["contact_response_provider_removable_now"] is False


def test_analyzer_pins_pc_source_and_required_anchors() -> None:
    text = ANALYZER.read_text(encoding="utf-8")
    assert 'PINNED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"' in text
    for token in (
        "FUN_00756bb0(this_01,param_1,(int)param_2);",
        "+ 0x3910) = *(undefined8 *)(param_2 + 0x730)",
        "+ 0x3918),*(undefined8 *)(param_2 + 0x738)",
        "local_14 = (float *)(param_2 + 0x768);",
        "FUN_00756ac0(this,*(double *)((int)this + 0x3c78));",
        "FUN_007551e0((void *)((int)param_1 + 0x3950)",
    ):
        assert token in text
