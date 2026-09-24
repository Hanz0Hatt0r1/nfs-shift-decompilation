from d3d9_declaration_lifecycle_evidence import analyze_d3d9_declaration_lifecycle


SOURCE = """
void __fastcall FUN_0085aac0(void *this,int param_1)
{
  FUN_008587e0((int)this,param_1);
}

uint __fastcall FUN_008587e0(int param_1,int param_2)
{
  puVar5 = FUN_00830f80(*(ushort **)(param_1 + 0x1c));
  *(ushort **)(param_1 + 0x20) = puVar5;
}

ushort * __fastcall FUN_00830f80(ushort *param_1)
{
  (**(code **)(*piVar3 + 0x158))(piVar3,*(undefined4 *)(puVar5 + 2),puVar5);
  return puVar5;
}

void __thiscall FUN_0084b9a0(void *this)
{
  FUN_00854d30(*(int *)((int)this + 0x8c));
}

undefined4 __fastcall FUN_00854d30(int param_1)
{
  uVar1 = FUN_0082e510((int)DAT_00c26058,*(undefined4 **)(param_1 + 0x20));
  return uVar1;
}

uint __fastcall FUN_0082e510(int param_1,undefined4 *param_2)
{
  uVar1 = (**(code **)(**(int **)(param_1 + 0x478) + 0x15c))
        (*(int **)(param_1 + 0x478),*param_2);
  return uVar1;
}
"""


def test_declaration_lifecycle_call_chain_is_observed():
    result = analyze_d3d9_declaration_lifecycle(SOURCE)

    assert result["format"] == "SHIFT.D3D9DeclarationLifecycleEvidence/1"
    assert result["status"] == "observed"
    assert all(edge["status"] == "observed" for edge in result["edges"].values())
    assert result["edges"]["canonicalizer_to_create"]["vtable_slot"] == 86
    assert result["edges"]["bind_wrapper_to_set_vertex_declaration"]["vtable_slot"] == 87
    assert result["evidence_boundary"]["specific_mesh_instance"] == "not-proven"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_declaration_lifecycle_fails_closed_when_loader_call_is_missing():
    source = SOURCE.replace("FUN_00830f80(*(ushort **)(param_1 + 0x1c));", "FUN_unknown();")
    result = analyze_d3d9_declaration_lifecycle(source)

    assert result["status"] == "not-proven"
    assert result["edges"]["loader_to_canonicalizer"]["status"] == "not-found"
