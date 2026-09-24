from d3d9_shader_lifecycle_evidence import analyze_d3d9_shader_lifecycle


def test_shader_lifecycle_observes_unified_draw_state():
    source = '''
void __fastcall FUN_0084f000(int param_1)
{
  int *piVar2;
  piVar2 = *(int **)(param_1 + 8);
  if (*(int *)(param_1 + 0x1890) != *(int *)(param_1 + 0x1894)) {
    (**(code **)(*piVar2 + 0x1ac))(piVar2,*(int *)(param_1 + 0x1890));
  }
  if (*(int *)(param_1 + 0x1898) != *(int *)(param_1 + 0x189c)) {
    (**(code **)(*piVar2 + 0x170))(piVar2,*(int *)(param_1 + 0x1898));
  }
  (**(code **)(*piVar2 + 0x15c))(piVar2,0);
  (**(code **)(*piVar2 + 400))(piVar2,0,0,32);
  (**(code **)(*piVar2 + 0x1a0))(piVar2,0);
}
'''
    report = analyze_d3d9_shader_lifecycle(source)
    assert report['status'] == 'observed'
    assert report['shaders']['pixel_shader']['vtable_byte_offset'] == '0x1ac'
    assert report['shaders']['vertex_shader']['vtable_byte_offset'] == '0x170'
    assert report['unified_draw_state']['vertex_declaration']['status'] == 'observed'
    assert report['unified_draw_state']['set_stream_source']['status'] == 'observed'
    assert report['unified_draw_state']['set_indices']['status'] == 'observed'