from d3d9_api_bind_evidence import analyze_d3d9_api_bind_source


def _source(
    *,
    dispatch=True,
    argument=True,
    cache=True,
):
    dispatch_line = (
        "      uVar1 = (**(code **)(**(int **)(param_1 + 0x478) + 0x15c))"
        if dispatch
        else "      uVar1 = FUN_unknown();"
    )
    argument_line = (
        "                        (*(int **)(param_1 + 0x478),*param_2);"
        if argument
        else "                        (*(int **)(param_1 + 0x478),param_2);"
    )
    cache_line = (
        "    *(undefined4 **)(param_1 + 0x70c) = param_2;"
        if cache
        else "    *(undefined4 **)(param_1 + 0x710) = param_2;"
    )
    return "\n".join(
        (
            "uint __fastcall FUN_0082e510(int param_1,undefined4 *param_2)",
            "{",
            "  if (param_2 != *(undefined4 **)(param_1 + 0x70c)) {",
            "    if (param_2 != (undefined4 *)0x0) {",
            dispatch_line,
            argument_line,
            "    }",
            cache_line,
            "  }",
            "  return 1;",
            "}",
        )
    )


def test_d3d9_api_bind_identifies_set_vertex_declaration_slot():
    result = analyze_d3d9_api_bind_source(_source())

    assert result["format"] == "SHIFT.D3D9ApiBindEvidence/1"
    assert result["status"] == "observed"
    assert result["api_identity"]["vtable_slot"] == 87
    assert result["api_identity"]["vtable_byte_offset"] == "0x15c"
    assert result["api_identity"]["method"] == "IDirect3DDevice9::SetVertexDeclaration"
    assert result["observations"]["device_vtable_dispatch"]["status"] == "observed"
    assert result["observations"]["declaration_argument_forwarded"]["status"] == "observed"
    assert result["observations"]["cached_current_declaration"]["status"] == "observed"
    assert result["semantic_links"]["declaration_object_to_d3d9_bind"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_d3d9_api_bind_fails_closed_when_dispatch_is_missing():
    result = analyze_d3d9_api_bind_source(_source(dispatch=False))

    assert result["status"] == "not-proven"
    assert result["semantic_links"]["declaration_object_to_d3d9_bind"]["status"] == "not-proven"
