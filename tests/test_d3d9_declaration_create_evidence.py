from d3d9_declaration_create_evidence import analyze_d3d9_declaration_create


SOURCE = """
unsigned short *FUN_00830f80(unsigned short *param_1) {
  uVar1 = FUN_0082ea90(param_1);
  *(undefined4 *)(puVar5 + 4) = uVar1;
  uVar1 = uVar1 * 8 + 8;
  puVar6 = alloc(uVar1);
  *(ushort **)(puVar5 + 2) = puVar6;
  _memcpy(puVar6,param_1,uVar1);
  (**(code **)(*piVar3 + 0x158))(piVar3,*(undefined4 *)(puVar5 + 2),puVar5);
  return puVar5;
}
"""


def test_declaration_create_evidence_recovers_create_vertex_declaration():
    result = analyze_d3d9_declaration_create(SOURCE)

    assert result["format"] == "SHIFT.D3D9DeclarationCreateEvidence/1"
    assert result["status"] == "observed"
    assert result["api_identity"]["method"] == "IDirect3DDevice9::CreateVertexDeclaration"
    assert result["api_identity"]["vtable_slot"] == 86
    assert result["api_identity"]["vtable_byte_offset"] == "0x158"
    assert result["record_layout"]["stride_bytes"] == 8
    assert result["record_layout"]["extra_record_bytes"] == 8
    assert result["semantic_links"]["canonical_record_bytes_to_create_call"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_declaration_create_evidence_fails_without_create_dispatch():
    result = analyze_d3d9_declaration_create(SOURCE.replace(
        "(**(code **)(*piVar3 + 0x158))(piVar3,*(undefined4 *)(puVar5 + 2),puVar5);",
        "FUN_unknown();",
    ))

    assert result["status"] == "not-proven"
    assert result["observations"]["create_vertex_declaration_dispatch"]["status"] == "not-found"
