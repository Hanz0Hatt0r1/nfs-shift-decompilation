import specialized_provider_loop_stencil_runtime as runtime


def test_scale_source_classifies_row_pointer_offset():
    source = (
        "*(double *)(*(int *)(&DAT_00002000 + local_10 * 4) + 0x18)"
    )
    result = runtime._scale_source(source)

    assert result == {
        "form": "row-pointer-offset",
        "table_base": "0x2000",
        "offset": "0x18",
    }


def test_scale_source_classifies_flat_pointer():
    result = runtime._scale_source(
        "*(double *)(&DAT_00002000 + local_10 * 8)"
    )
    assert result == {
        "form": "flat-pointer",
        "base": "0x2000",
    }


def test_destination_forms_cover_pointer_array_and_direct():
    assert runtime._destination_form(
        "*(double *)(&DAT_00001000 + local_10 * 8) = x;"
    ) == ("loop-pointer", 0x1000)
    assert runtime._destination_form(
        "(&DAT_00001000)[local_10] = x;"
    ) == ("loop-array", 0x1000)
    assert runtime._destination_form(
        "_DAT_00001008 = x;"
    ) == ("direct", 0x1008)


def test_loop_stencil_keeps_dvar_scale_loaded_before_loop():
    fixture = """
void FUN_example(void)
{
  double dVar1;
  int local_10;
  dVar1 = 1.0 / _DAT_00001000;
  for (local_10 = 2; local_10 < 4; local_10 = local_10 + 1) {
    (&DAT_00001000)[local_10] =
         *(double *)(&DAT_00002000 + local_10 * 8) * dVar1;
  }
  _DAT_00003000 = _DAT_00003000 * dVar1;
}
void FUN_next(void)
{
}
"""
    report = runtime.extract_loop_stencils(
        fixture,
        provider_id=0,
    )

    assert report["errors"] == []
    assert [s["loop_index"] for s in report["stencils"]] == [2, 3]
    assert all(
        s["scale_source"]["form"] == "direct-dat"
        for s in report["stencils"]
    )


def test_validation_rejects_missing_destination_address():
    result = runtime.validate_loop_stencils(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "stencils": [
                {
                    "destination": {},
                    "scale_source": {"form": "direct-dat"},
                    "loop_index": None,
                }
            ],
            "errors": [],
        }
    )
    assert result["ready"] is False
    assert "stencil-0-missing-destination-address" in result["errors"]
