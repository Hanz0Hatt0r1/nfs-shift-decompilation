from d3d9_render_api_boundary import analyze_d3d9_render_api_boundary


SOURCE = """
void __fastcall FUN_0082e510(int param_1) {
  (**(code **)(*piVar2 + 0x15c))(piVar2, param_1);
}
void __fastcall FUN_00854d30(int param_1) {
  FUN_0082e510(0, param_1);
}
void __fastcall FUN_00854da0(int *param_1, undefined4 param_2, int param_3) {
  uVar3 = (**(code **)(iVar1 + 400))(piVar2,param_2,x,0,uVar3);
}
undefined4 __fastcall FUN_00854e10(int param_1,int param_2) {
  uVar2 = (**(code **)(*piVar1 + 0x1a0))(piVar1,x);
}
void __thiscall FUN_0084b9a0(void *this) {
  FUN_00854d30(thing);
  FUN_00854da0(a,b,c);
  FUN_00854e10(a,b);
  (**(code **)(*piVar2 + 0x148))(piVar2,4,0,0,4,0,2);
}
""".replace("+ 400", "+ 0x190")


def test_render_api_boundary_recovers_setup_and_draw_slots():
    result = analyze_d3d9_render_api_boundary(SOURCE)

    assert result["format"] == "SHIFT.D3D9RenderApiBoundaryEvidence/1"
    assert result["status"] == "observed"
    assert result["api_methods"]["declaration"]["slot"] == 87
    assert result["api_methods"]["stream_source"]["slot"] == 100
    assert result["api_methods"]["index_source"]["slot"] == 104
    assert result["api_methods"]["draw_indexed"]["slot"] == 82
    assert result["observations"]["mesh_render_setup_order"]["status"] == "observed"
    assert result["observations"]["draw_indexed_dispatch"]["status"] == "observed"
    assert result["semantic_links"]["render_setup_to_draw"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_render_api_boundary_fails_closed_without_draw_dispatch():
    source = SOURCE.replace("(**(code **)(*piVar2 + 0x148))(piVar2,4,0,0,4,0,2);", "")
    result = analyze_d3d9_render_api_boundary(source)

    assert result["status"] == "not-proven"
    assert result["observations"]["draw_indexed_dispatch"]["status"] == "not-found"


def test_render_api_boundary_accepts_split_function_signature():
    source = SOURCE.replace(
        "void __thiscall FUN_0084b9a0(void *this) {",
        "void __thiscall\nFUN_0084b9a0(void *this) {",
    )
    result = analyze_d3d9_render_api_boundary(source)

    assert result["observations"]["mesh_render_setup_order"]["status"] == "observed"
