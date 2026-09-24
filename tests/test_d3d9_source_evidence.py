import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from d3d9_source_evidence import analyze_shift_exe_c


SOURCE = r'''
uint __fastcall FUN_008310c0(float *param_1)
{
  local_10 = (uint)(longlong)ROUND(param_1[3] * 255.0);
  uVar1 = local_10 << 8;
  local_10 = (uint)(longlong)ROUND(*param_1 * 255.0);
  uVar1 = uVar1 | local_10;
  local_10 = (uint)(longlong)ROUND(param_1[1] * 255.0);
  uVar1 = uVar1 << 8 | local_10;
  local_10 = (uint)(longlong)ROUND(param_1[2] * 255.0);
  return uVar1 << 8 | local_10;
}

undefined4 __fastcall FUN_00854e70(int param_1,int param_2)
{
  switch(*pbVar18) {
  case 0:
  case 1:
  case 2:
  case 3:
    _memcpy(local_18,local_84,uVar4 * 4);
    break;
  case 4:
    fVar7 = (float)FUN_008310c0(&local_100);
    *local_18 = fVar7;
    break;
  case 5:
    *local_18 = local_c0;
  }
}

undefined4 * __thiscall FUN_00858180(void *this,uint param_1)
{
  local_40 = pvVar10;
  *(undefined1 *)(iVar7 + 4 + *(int *)(param_1 + 0x1c)) = 0;
  *(undefined1 *)(iVar7 + 6 + *(int *)(param_1 + 0x1c)) = 0;
  *(undefined1 *)(iVar7 + 7 + *(int *)(param_1 + 0x1c)) = 0;
}

uint __fastcall FUN_00859800(int param_1,int param_2)
{
  pvVar10 = (void *)FUN_0063c7a0(local_40,(byte *)"STREAM");
  pcVar16 = (char *)FUN_0063d360(local_40,(byte *)"Type");
  pcVar16 = (char *)FUN_0063d360(local_40,(byte *)"Usage");
  FUN_0063d410(local_40,"Channel",&local_1c);
}
'''


def test_source_evidence_observes_packed_color_and_type4_path():
    result = analyze_shift_exe_c(SOURCE)
    assert result["format"] == "SHIFT.D3D9SourceVertexEvidence/1"
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["packed-color-helper"]["status"] == "observed"
    assert by_id["packed-color-helper"]["little_endian_memory_order"] == "BGRA"
    assert by_id["declaration-type-4-packed-color"]["status"] == "observed"
    assert by_id["declaration-type-4-packed-color"]["type_code"] == 4
    assert by_id["stream-type-usage-channel"]["status"] == "observed"
    assert result["linkage"]["type_4_to_packed_color"]["status"] == "observed"
    assert result["linkage"]["meb_460_461_to_type_4"]["status"] == "not-proven"
    assert result["selection"] == "not-selected"
    assert result["verified_abi"] is False


def test_source_evidence_is_negative_when_required_patterns_are_missing():
    result = analyze_shift_exe_c("void f() {}")
    assert result["observations"][0]["status"] == "not-found"
    assert result["linkage"]["type_4_to_packed_color"]["status"] == "not-proven"
    assert result["verified_abi"] is False


def test_source_evidence_file_preserves_source_hash(tmp_path):
    from d3d9_source_evidence import analyze_shift_exe_c_file
    path = tmp_path / "SHIFT.exe.c"
    path.write_text(SOURCE, encoding="utf-8")
    result = analyze_shift_exe_c_file(path)
    assert result["source"]["path"] == str(path)
    assert result["source"]["bytes"] == path.stat().st_size
    assert len(result["source"]["sha256"]) == 64


def test_source_evidence_records_type_table_chain_and_source_lines():
    result = analyze_shift_exe_c(
        SOURCE
        + r'''
undefined4 __fastcall FUN_00853c20(int param_1)
{
  return *(undefined4 *)(&DAT_00b90088 + param_1 * 4);
}

uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  pbVar17 = (&PTR_DAT_00b901d0)[(int)local_18];
  uVar9 = FUN_00853c20((int)local_18);
  *(char *)(iVar7 + 4 + *(int *)(param_1 + 0x1c)) = (char)uVar9;
  pcVar16 = (char *)FUN_0063d360(local_40,(byte *)"Usage");
  uVar9 = FUN_00853c40(local_5c);
  FUN_0063d410(local_40,"Channel",&local_1c);
  switch(local_5c) {
    case 6:
      pcVar23 = "Colour";
  }
}
'''
    )
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["type-table-accessor"]["status"] == "observed"
    assert by_id["type-table-accessor"]["source_line"] is not None
    assert by_id["xml-type-table-chain"]["status"] == "observed"
    assert by_id["xml-type-table-chain"]["source_line"] is not None
    assert by_id["xml-colour-stream-field"]["status"] == "observed"
    assert result["linkage"]["xml_type_name_to_d3d9_type_table"]["status"] == "observed"
    assert result["linkage"]["xml_colour_to_type_4"]["status"] == "not-proven"
    assert result["linkage"]["meb_460_461_to_type_4"]["status"] == "not-proven"


def test_source_evidence_negative_fixture_does_not_invent_type_table_linkage():
    result = analyze_shift_exe_c("uint f(void) { return 0; }")
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["type-table-accessor"]["status"] == "not-found"
    assert by_id["xml-type-table-chain"]["status"] == "not-found"
    assert result["linkage"]["xml_type_name_to_d3d9_type_table"]["status"] == "not-proven"
    assert result["linkage"]["xml_colour_to_type_4"]["status"] == "not-proven"


def test_source_evidence_census_records_type_table_callsites_and_source_reference():
    source = SOURCE + r'''
undefined4 __fastcall FUN_00853c20(int param_1)
{
  return *(undefined4 *)(&DAT_00b90088 + param_1 * 4);
}
uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  uVar9 = FUN_00853c20((int)local_18);
}
uint __fastcall FUN_00854e70(int param_1,int param_2)
{
  uVar5 = FUN_00853c20(*(int *)(*(int *)(local_28 + 0x3c) + local_70 * 4));
}
void f(void) {
  FUN_0062de50(0xb1c6d8,".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",0xbdb,0xb1c9a0,'\\0');
}
'''
    result = analyze_shift_exe_c(source)
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["type-table-callsite-census"]["call_count"] == 2
    assert all(line > 0 for line in by_id["type-table-callsite-census"]["source_lines"])
    assert by_id["cprimitive-type-source-reference"]["reference_count"] == 1


def test_source_evidence_census_is_empty_without_type_table_or_source_reference():
    result = analyze_shift_exe_c("void f(void) {}")
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["type-table-callsite-census"]["status"] == "not-found"
    assert by_id["type-table-callsite-census"]["call_count"] == 0
    assert by_id["cprimitive-type-source-reference"]["status"] == "not-found"
    assert by_id["cprimitive-type-source-reference"]["reference_count"] == 0
