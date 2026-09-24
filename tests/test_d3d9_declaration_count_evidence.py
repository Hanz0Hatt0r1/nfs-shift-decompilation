from d3d9_declaration_count_evidence import analyze_d3d9_declaration_count


SOURCE = """
void __fastcall FUN_0082ea90(ushort *param_1)
{
  ushort uVar1;
  int iVar2;

  iVar2 = 0;
  uVar1 = *param_1;
  while (uVar1 < 0xff) {
    iVar2 = iVar2 + 1;
    uVar1 = param_1[iVar2 * 4];
  }
}

ushort * __fastcall FUN_00830f80(ushort *param_1)
{
  uVar1 = FUN_0082ea90(param_1);
  uVar1 = uVar1 * 8 + 8;
  puVar6 = alloc(uVar1);
  _memcpy(puVar6,param_1,uVar1);
  return puVar5;
}
"""


def test_declaration_count_evidence_recovers_stream_stop_rule():
    result = analyze_d3d9_declaration_count(SOURCE)

    assert result["format"] == "SHIFT.D3D9DeclarationCountEvidence/1"
    assert result["status"] == "observed"
    assert result["count_boundary"]["record_stride_bytes"] == 8
    assert result["count_boundary"]["stop_field"] == "Stream WORD"
    assert result["count_boundary"]["stop_criterion"] == "Stream >= 0xff"
    assert result["create_boundary"]["buffer_expression"] == "count * 8 + 8"
    assert result["semantic_links"]["count_to_create_buffer"]["status"] == "observed"
    assert result["semantic_links"]["stream_stop_to_exact_end_sentinel"]["status"] == "not-proven"


def test_declaration_count_evidence_fails_when_stop_condition_is_missing():
    result = analyze_d3d9_declaration_count(SOURCE.replace(
        "while (uVar1 < 0xff) {",
        "while (uVar1 < 0xfe) {",
    ))

    assert result["status"] == "not-proven"
    assert result["observations"]["stop_condition"]["status"] == "not-found"
