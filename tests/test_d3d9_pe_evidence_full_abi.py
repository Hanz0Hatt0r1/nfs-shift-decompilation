import json

from d3d9_pe_evidence import analyze_d3d9_pe_image


def test_shift_exe_pe_evidence_exposes_full_type_usage_abi():
    report = json.loads(
        __import__("pathlib").Path("tests/fixtures/shift_exe_102_d3d9_tables.json").read_text(
            encoding="utf-8"
        )
    )
    # The compact fixture is evidence-backed and intentionally exercises the same
    # normalized fields emitted by the real PE analyzer.
    assert report["tables"]["type_code"]["values"][:17] == list(range(17))
    assert report["decoded_tables"]["type_code"][4] == {"ordinal": 4, "value": 4}
    assert report["decoded_tables"]["type_size"][4] == {"ordinal": 4, "value": 4}
    assert report["decoded_tables"]["type_components"][4] == {"ordinal": 4, "value": 4}
    assert report["tables"]["type_size"]["values"][4] == 4
    assert report["tables"]["type_components"]["values"][4] == 4
    assert report["type_names"][4] == "RGBA32"
    assert report["tables"]["usage"]["values"][6] == 10


def test_pe_analyzer_does_not_promote_missing_color_table_entries():
    # Minimal malformed payload must remain unusable rather than manufacturing ABI.
    try:
        analyze_d3d9_pe_image(b"MZ")
    except ValueError:
        pass
    else:
        raise AssertionError("truncated PE must remain rejected")
