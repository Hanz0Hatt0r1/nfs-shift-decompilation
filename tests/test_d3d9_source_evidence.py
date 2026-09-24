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

def test_source_evidence_recovers_original_cprimitivetype_line_numbers():
    result = analyze_shift_exe_c(
        SOURCE
        + r'''
void f(void) {
  FUN_0062de50(0xb1c958,".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",0xb28,0xb1c9a0,'\\0');
  FUN_0062de50(0xb1c6d8,".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",0xbdb,0xb1c9a0,'\\0');
}
'''
    )
    by_id = {row["id"]: row for row in result["observations"]}
    anchors = by_id["cprimitive-type-source-anchors"]["source_line_anchors"]
    assert by_id["cprimitive-type-source-anchors"]["anchor_count"] == 2
    assert anchors[0]["original_line"] == 0xB28
    assert anchors[1]["original_line"] == 0xBDB
    assert anchors[0]["original_line_hex"] == "0xb28"
    assert anchors[1]["original_line_hex"] == "0xbdb"
    assert all(item["decompiler_line"] > 0 for item in anchors)


def test_source_evidence_source_anchors_require_diagnostic_call_shape():
    result = analyze_shift_exe_c('".\\Source\\Platforms\\Win\\CPrimitiveType.cpp"')
    by_id = {row["id"]: row for row in result["observations"]}
    assert by_id["cprimitive-type-source-reference"]["reference_count"] == 1
    assert by_id["cprimitive-type-source-anchors"]["status"] == "not-found"
    assert by_id["cprimitive-type-source-anchors"]["anchor_count"] == 0


def test_d3d9_type_semantics_covers_all_recovered_cases():
    from d3d9_type_semantics import analyze_d3d9_type_semantics

    source = r'''
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
    local_100 = local_84[0];
    local_fc = local_84[1];
    local_f8 = local_84[2];
    local_f4 = local_78;
    fVar7 = (float)FUN_008310c0(&local_100);
    *local_18 = fVar7;
    break;
  case 5:
    local_30 = (longlong)ROUND(local_84[uVar11]);
    *(undefined1 *)((int)&local_c0 + uVar11) = local_30._4_1_;
    break;
  case 6:
    uVar21 = FUN_00901310(uVar5,uVar4);
    *(short *)((int)&local_c4 + uVar11 * 2) = (short)uVar21;
    break;
  case 7:
    uVar21 = FUN_00901310(uVar5,uVar4);
    *(short *)((int)local_dc + uVar11 * 2) = (short)uVar21;
    break;
  case 8:
    local_30 = (longlong)ROUND(local_84[uVar11] * 255.0);
    *(undefined1 *)((int)&local_b4 + uVar11) = local_30._4_1_;
    break;
  case 9:
    uVar21 = FUN_00901310(uVar5,uVar4);
    *(short *)((int)local_ac + uVar11 * 2) = (short)uVar21;
    break;
  case 10:
    uVar21 = FUN_00901310(uVar5,uVar4);
    *(short *)((int)local_a4 + uVar11 * 2) = (short)uVar21;
    break;
  case 0xb:
    local_30 = CONCAT44((int)ROUND(*pfVar14 * 65535.0),(int)local_30);
    (&uStack_76)[uVar11] = local_30._4_2_;
    break;
  case 0xc:
    local_30 = CONCAT44((int)ROUND(*pfVar14 * 65535.0),(int)local_30);
    *(undefined2 *)((int)local_98 + uVar11 * 2) = local_30._4_2_;
    break;
  case 0xd:
    if (0x3fe < (uint)local_30) local_30._0_4_ = 0x3ff;
    *local_18 = (float)((local_ec[2] * 0x400 + local_ec[1]) * 0x400 + local_ec[0]);
    break;
  case 0xe:
    uVar21 = FUN_00901310(uVar5,uVar4);
    (&local_d0)[uVar11] = (float)uVar21;
    *local_18 = (float)((local_c8 * 0x400 + local_cc) * 0x400 + (int)local_d0);
    break;
  case 0xf:
    FUN_0064fcb0(this,(uint)local_84[uVar11]);
    break;
  case 0x10:
    FUN_0064fcb0(puVar16,(uint)local_84[uVar11]);
    break;
  }
}
  FUN_00886930(local_3c,cVar13,(uint)local_3c);
'''
    result = analyze_d3d9_type_semantics(source)
    assert result["enum_alignment"]["status"] == "observed"
    assert result["enum_alignment"]["observed_case_count"] == 17
    assert result["enum_alignment"]["missing_cases"] == []
    assert len(result["cases"]) == 17
    by_code = {row["type_code"]: row for row in result["cases"]}
    assert by_code[4]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"
    assert by_code[4]["status"] == "observed"
    assert by_code[8]["d3d9_type"] == "D3DDECLTYPE_UBYTE4N"
    assert by_code[11]["d3d9_type"] == "D3DDECLTYPE_USHORT2N"
    assert "32767" in by_code[9]["note"]
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_d3d9_type_semantics_fails_closed_without_primitive_switch():
    from d3d9_type_semantics import analyze_d3d9_type_semantics

    result = analyze_d3d9_type_semantics("void f(void) {}")
    assert result["enum_alignment"]["status"] == "not-found"
    assert result["cases"] == []


def test_d3d9_table_shape_evidence_recovers_17_type_ordinals():
    from d3d9_table_shape_evidence import analyze_d3d9_table_shapes

    source = r'''
undefined DAT_00b90088;
undefined DAT_00b900d8;
undefined DAT_00b9011c;
undefined DAT_00b90140;
undefined DAT_00b90178;
pointer PTR_DAT_00b901d0;

undefined4 __fastcall FUN_00853c20(int param_1)
{
  return *(undefined4 *)(&DAT_00b90088 + param_1 * 4);
}
undefined4 __fastcall FUN_00853c30(int param_1)
{
  return *(undefined4 *)(&DAT_00b900d8 + param_1 * 4);
}
uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  do {
    pbVar17 = (&PTR_DAT_00b901d0)[(int)local_18];
    uVar9 = FUN_00853c20((int)local_18);
  } while (local_18 < (AptCIH *)0x11);
  do {
    local_5c = local_5c + 1;
  } while (local_5c < 9);
}
'''
    result = analyze_d3d9_table_shapes(source)
    assert result["tables"]["DAT_00b90088"]["declared"] is True
    assert result["tables"]["PTR_DAT_00b901d0"]["declared"] is True
    assert result["indexing"]["type_table"]["byte_stride"] == 4
    assert result["indexing"]["type_table"]["layout_hint_dword_slots"] == 20
    assert result["indexing"]["size_table"]["layout_hint_dword_slots"] == 17
    assert result["xml_stream"]["type_ordinal_exclusive_limit"] == 0x11
    assert result["xml_stream"]["usage_exclusive_limit"] == 9
    assert result["xml_stream"]["status"] == "observed"
    assert result["conclusions"]["type_table_initializer_bytes"]["status"] == "opaque"
    assert result["conclusions"]["meb_460_461_mapping"]["status"] == "not-proven"


def test_d3d9_table_shape_evidence_is_conservative_without_xml_bounds():
    from d3d9_table_shape_evidence import analyze_d3d9_table_shapes

    result = analyze_d3d9_table_shapes("undefined DAT_00b90088;")
    assert result["xml_stream"]["status"] == "not-proven"
    assert result["conclusions"]["type_table_initializer_bytes"]["status"] == "opaque"


def test_d3d9_usage_evidence_recovers_colour_usage_6_and_known_names():
    from d3d9_usage_evidence import analyze_d3d9_usage_semantics

    source = r'''
uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  local_5c = 0;
  do {
    pbVar17 = (&PTR_s_Position_00b901a8)[local_5c];
    switch(local_5c) {
    case 0:
      pcVar23 = "Position";
      break;
    case 1:
      pcVar23 = "Weights";
      break;
    case 2:
      pcVar23 = "Normal";
      break;
    case 3:
      pcVar23 = &DAT_00b1d188;
      break;
    case 4:
      pcVar23 = "Tangent";
      break;
    case 5:
      pcVar23 = "Binormal";
      break;
    case 6:
      pcVar23 = "Colour";
      break;
    case 7:
      pcVar23 = "Depth";
      break;
    case 8:
      pcVar23 = "Indices";
      break;
    }
  } while (local_5c < 9);
}
'''
    result = analyze_d3d9_usage_semantics(source)
    assert result["switch"]["status"] == "observed"
    assert result["switch"]["usage_exclusive_limit"] == 9
    assert result["switch"]["pointer_array"] == "PTR_s_Position_00b901a8"
    by_code = {row["usage_code"]: row for row in result["usages"]}
    assert by_code[0]["source_name"] == "Position"
    assert by_code[6]["source_name"] == "Colour"
    assert by_code[6]["status"] == "observed"
    assert by_code[3]["status"] == "observed"
    assert by_code[3]["source_symbol"] == "DAT_00b1d188"
    assert result["semantic_links"]["usage_6_to_colour"]["status"] == "observed"
    assert result["semantic_links"]["usage_6_to_meb_colour_properties"]["status"] == "not-proven"


def test_d3d9_usage_evidence_fails_closed_without_usage_switch():
    from d3d9_usage_evidence import analyze_d3d9_usage_semantics

    result = analyze_d3d9_usage_semantics("void f(void) {}")
    assert result["switch"]["status"] == "not-found"
    assert result["usages"][6]["status"] == "not-found"


def test_d3d9_usage_evidence_anchors_target_function_not_unrelated_switch():
    from d3d9_usage_evidence import analyze_d3d9_usage_semantics

    source = r'''
void unrelated(void) {
  switch(local_5c) {
  case 0:
    pcVar23 = "WRONG";
    break;
  case 6:
    pcVar23 = "WRONG";
    break;
  }
}
uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  switch(local_5c) {
  case 0:
    pcVar23 = "Position";
    break;
  case 1:
    pcVar23 = "Weights";
    break;
  case 2:
    pcVar23 = "Normal";
    break;
  case 3:
    pcVar23 = &DAT_00b1d188;
    break;
  case 4:
    pcVar23 = "Tangent";
    break;
  case 5:
    pcVar23 = "Binormal";
    break;
  case 6:
    pcVar23 = "Colour";
    break;
  case 7:
    pcVar23 = "Depth";
    break;
  case 8:
    pcVar23 = "Indices";
    break;
  }
  } while (local_5c < 9);
}
'''
    result = analyze_d3d9_usage_semantics(source)
    assert result["switch"]["status"] == "observed"
    assert result["switch"]["usage_exclusive_limit"] == 9
    assert result["usages"][6]["source_name"] == "Colour"
    assert result["usages"][6]["status"] == "observed"


def test_d3d9_memory_table_evidence_decodes_tables_and_type_name_pointers():
    import struct

    from d3d9_memory_table_evidence import (
        analyze_d3d9_memory_tables,
        TYPE_NAME_POINTER_TABLE_ADDRESS,
    )

    base = 0x00B90000
    data = bytearray(0x500)

    def put_words(address, words):
        offset = address - base
        struct.pack_into("<" + "I" * len(words), data, offset, *words)

    put_words(0x00B90088, list(range(20)))
    put_words(0x00B900D8, [10] * 17)
    put_words(0x00B9011C, list(range(9)))
    put_words(0x00B90140, [100 + i for i in range(14)])

    string_addresses = [base + 0x300 + i * 16 for i in range(17)]
    put_words(TYPE_NAME_POINTER_TABLE_ADDRESS, string_addresses)
    for ordinal, address in enumerate(string_addresses):
        payload = f"Type{ordinal}".encode("ascii") + b"\\0"
        data[address - base : address - base + len(payload)] = payload

    result = analyze_d3d9_memory_tables(bytes(data), base)
    assert result["tables"]["type_code"]["complete"] is True
    assert result["tables"]["type_code"]["values"][:17] == list(range(17))
    assert result["tables"]["size"]["complete"] is True
    assert result["tables"]["usage"]["values"] == list(range(9))
    assert result["tables"]["usage_index"]["values"][0] == 100
    assert len(result["type_name_pointers"]) == 17
    assert result["type_name_pointers"][0]["string"] == "Type0"
    assert result["type_name_pointers"][16]["string"] == "Type16"
    assert result["type_name_pointers"][16]["status"] == "decoded"
    assert result["proven_type_code_prefix"]["status"] == "decoded"
    assert result["conclusions"]["meb_460_461_to_type_code"]["status"] == "not-proven"


def test_d3d9_memory_table_evidence_fails_closed_for_partial_dump():
    from d3d9_memory_table_evidence import analyze_d3d9_memory_tables

    result = analyze_d3d9_memory_tables(b"\\x00" * 16, 0x00B90000)
    assert result["tables"]["type_code"]["status"] == "out-of-range"
    assert result["tables"]["size"]["status"] == "out-of-range"
    assert result["type_name_pointers"][0]["status"] == "unavailable"
    assert result["proven_type_code_prefix"]["status"] == "partial"
