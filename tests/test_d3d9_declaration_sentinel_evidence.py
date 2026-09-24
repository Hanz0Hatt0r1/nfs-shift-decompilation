from d3d9_declaration_sentinel_evidence import analyze_d3d9_declaration_sentinel


SOURCE = """
uint FUN_008587e0(int param_1,int param_2)
{
  *(undefined2 *)(*(int *)(param_1 + 0x1c) + (int)pAVar22 * 8) = 0xff;
  *(undefined2 *)(*(int *)(param_1 + 0x1c) + 2 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 4 + (int)pAVar22 * 8) = 0x11;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 5 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 6 + (int)pAVar22 * 8) = 0;
  *(undefined1 *)(*(int *)(param_1 + 0x1c) + 7 + (int)pAVar22 * 8) = 0;
}
"""


def test_declaration_sentinel_evidence_recovers_all_six_fields():
    result = analyze_d3d9_declaration_sentinel(SOURCE)

    assert result["format"] == "SHIFT.D3D9DeclarationSentinelEvidence/1"
    assert result["status"] == "observed"
    assert result["sentinel"] == {
        "stream": 0xFFFF,
        "offset": 0,
        "type": 0x11,
        "method": 0,
        "usage": 0,
        "usage_index": 0,
    }
    assert all(
        value["status"] == "observed"
        for value in result["observations"]["field_writes"].values()
    )
    assert result["semantic_links"]["exact_d3ddecl_end_shape"]["status"] == "observed"


def test_declaration_sentinel_evidence_fails_closed_when_one_field_is_missing():
    source = SOURCE.replace(
        "*(undefined1 *)(*(int *)(param_1 + 0x1c) + 7 + (int)pAVar22 * 8) = 0;",
        "noop();",
    )
    result = analyze_d3d9_declaration_sentinel(source)

    assert result["status"] == "not-proven"
    assert result["observations"]["field_writes"]["usage_index"]["status"] == "not-found"


def test_declaration_sentinel_evidence_accepts_local_index_variant():
    source = SOURCE.replace(
        "(int)pAVar22 * 8",
        "local_14 * 8",
    )
    result = analyze_d3d9_declaration_sentinel(source)

    assert result["status"] == "observed"
    assert result["observations"]["field_writes"]["stream"]["status"] == "observed"
