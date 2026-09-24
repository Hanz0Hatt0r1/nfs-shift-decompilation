from d3d9_binding_args_evidence import analyze_d3d9_binding_args


SOURCE = """
undefined4 __fastcall FUN_00854da0(int *param_1,undefined4 param_2,int param_3)
{
  piVar2 = (int *)FUN_0082e110(DAT_00c26058);
  uVar3 = (**(code **)(*param_1 + 0x1c))();
  uVar3 = (**(code **)(iVar1 + 0x190))
                    (piVar2,param_2,*(undefined4 *)(param_1[9] + 0xc + param_3 * 0x10),0,uVar3);
}
undefined4 __fastcall FUN_00854e10(int param_1,int param_2)
{
  piVar1 = (int *)FUN_0082e110(DAT_00c26058);
  uVar2 = (**(code **)(*piVar1 + 0x1a0))
                    (piVar1,*(undefined4 *)(param_2 * 0x50 + 0x40 + *(int *)(param_1 + 0x2c)));
}
"""


def test_binding_args_recover_stream_and_index_arguments():
    result = analyze_d3d9_binding_args(SOURCE)

    assert result["format"] == "SHIFT.D3D9BindingArgsEvidence/1"
    assert result["status"] == "observed"
    assert result["stream_source"]["arguments"]["stream"]["expression"] == "param_2"
    assert result["stream_source"]["arguments"]["offset_in_bytes"]["value"] == 0
    assert result["stream_source"]["arguments"]["stride"]["status"] == "observed"
    assert result["index_source"]["arguments"]["index_buffer"]["status"] == "observed"
    assert result["semantic_links"]["stream_arguments_to_device"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_binding_args_fails_closed_when_stream_buffer_path_is_missing():
    result = analyze_d3d9_binding_args(
        SOURCE.replace(
            "*(undefined4 *)(param_1[9] + 0xc + param_3 * 0x10)",
            "FUN_unknown()",
        )
    )

    assert result["status"] == "not-proven"
    assert result["stream_source"]["arguments"]["vertex_buffer"]["status"] == "not-found"
