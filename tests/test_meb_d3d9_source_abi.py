import struct

from meb_d3d9_source_abi import (
    VERIFIED_COLOR_ABI,
    analyze_meb_d3d9_source_abi,
    property_triplet,
)
from meb_format import read_meb


SOURCE = r'''
def read_meb(data: bytes):
    for _ in range(num_vert_props):
        a = r.u32(); b = r.u32(); c = r.u32()
        prop = f"{a}{b}{c}"

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
  case 4:
    fVar7 = (float)FUN_008310c0(&local_100);
    *local_18 = fVar7;
  }
  else if (local_6c == (ushort *)0x6) {
    *(char *)(iVar10 + 7 + iVar12) = local_14._3_1_;
    local_14 = CONCAT13(local_14._3_1_ + '\x01',(undefined3)local_14);
  }
}

uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  switch(local_5c) {
  case 6:
    pcVar23 = "Colour";
  }
}

uint __fastcall FUN_00859800(int param_1,int param_2)
{
  uVar13 = FUN_00853c20(*(uint *)pAVar24);
  uVar13 = FUN_00853c40(*(uint *)(pAVar24 + 4));
  extraout_EDX_01[*(int *)(param_1 + 0x1c) + 7] = SUB41(*(uint *)(pAVar24 + 8),0);
  pAVar24 = pAVar24 + 0xc;
}
'''

def test_property_triplet_matches_three_digit_msb_encoding():
    assert property_triplet("460") == (4, 6, 0)
    assert property_triplet("461") == (4, 6, 1)
    assert property_triplet("033") == (0, 3, 3)


def test_source_correlates_color_properties_to_d3d9_d3dcolor():
    result = analyze_meb_d3d9_source_abi(SOURCE, ("460", "461", "580"))
    assert result["global_evidence"]["meb_three_u32_descriptor"] is True
    assert result["global_evidence"]["binary_descriptor_type_usage_channel"] is True
    assert result["global_evidence"]["declaration_usage_6_colour_channel"] is True
    assert result["global_evidence"]["packed_color_type_4"] is True
    assert result["global_evidence"]["xml_usage_6_colour"] is True

    by_id = {row["property_id"]: row for row in result["properties"]}
    assert by_id["460"]["descriptor_triplet"] == [4, 6, 0]
    assert by_id["460"]["status"] == "verified"
    assert by_id["460"]["d3d9_type"] == "D3DCOLOR"
    assert by_id["460"]["source_memory_order"] == "BGRA"
    assert by_id["460"]["shader_order"] == "RGBA"
    assert by_id["460"]["semantic"] == "COLOR0"

    assert by_id["461"]["descriptor_triplet"] == [4, 6, 1]
    assert by_id["461"]["status"] == "verified"
    assert by_id["461"]["semantic"] == "COLOR1"

    assert by_id["580"]["status"] == "not-proven"
    assert result["meb_mapping"]["status"] == "verified"
    assert result["verification_count"] == 2
    assert result["cross_checks"]["known_triplets"]["200"]["triplet"] == [2, 0, 0]


def test_source_correlated_color_abi_constants_match_report():
    assert VERIFIED_COLOR_ABI["460"]["descriptor_triplet"] == (4, 6, 0)
    assert VERIFIED_COLOR_ABI["461"]["descriptor_triplet"] == (4, 6, 1)
    assert VERIFIED_COLOR_ABI["460"]["d3d9_type"] == "D3DCOLOR"
    assert VERIFIED_COLOR_ABI["461"]["source_memory_order"] == "BGRA"


def test_meb_property_layout_preserves_descriptor_triplet():
    name = b"TEST\x00"
    header = struct.pack(">II", 1, 0) + name
    header += b"\x00" * ((4 - len(header) % 4) % 4)
    header += struct.pack("<III", 1, 1, 0)
    header += bytes(40)
    payload = struct.pack("<III", 4, 6, 0) + bytes((10, 20, 30, 255))

    mesh = read_meb(header + payload)
    assert mesh.vertex_properties == ["460"]
    assert mesh.property_layouts[0]["descriptor_triplet"] == [4, 6, 0]
    assert mesh.property_layouts[0]["id"] == "460"


def test_source_abi_fails_closed_when_binary_loader_mapping_is_missing():
    result = analyze_meb_d3d9_source_abi(
        SOURCE.replace("pAVar24 = pAVar24 + 0xc;", "pAVar24 = pAVar24 + 8;"),
        ("460",),
    )
    assert result["properties"][0]["status"] == "not-proven"
    assert result["meb_mapping"]["status"] == "not-proven"
