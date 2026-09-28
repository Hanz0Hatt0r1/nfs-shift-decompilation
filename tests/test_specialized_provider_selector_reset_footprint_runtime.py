import specialized_provider_selector_reset_footprint_runtime as runtime


def _event(call_index, frame, return_address, selector, provider_id):
    return {
        "frame_index": frame,
        "call_index": call_index,
        "physics_system": 0x1000,
        "provider_pointer": 0x2000,
        "provider_vtable": (
            0x00B0FC5C if provider_id == 0 else 0x00B0FC8C
        ),
        "provider_id": provider_id,
        "scalar_count": 40 if provider_id == 0 else 34,
        "selector": selector,
        "caller_return_address": return_address,
    }


def test_case_footprint_contains_selector_and_seed():
    result = runtime._case_footprint(
        {
            "pivot_index": 2,
            "zero_assignments": ["0x1000"],
            "bulk_clears": [
                {"base": "0x1010", "bytes": 0x10},
            ],
            "diagonal_address": "0x1008",
        }
    )

    assert result["selector"] == 2
    assert result["zero_count"] == 3
    assert result["touched_count"] == 4
    assert result["unit_diagonal_address"] == "0x1008"


def test_expand_runtime_footprint_filters_to_provider_id():
    source_pattern = """
void FUN_007d3150(undefined4 param_1)
{
  switch(param_1) {
  case 0:
    DAT_00c21740 = 0;
    DAT_00c21738 = 0x3ff0000000000000;
    break;
  case 1:
    DAT_00c21748 = 0;
    DAT_00c21740 = 0x3ff0000000000000;
    break;
  case 2:
    DAT_00c21750 = 0;
    DAT_00c21748 = 0x3ff0000000000000;
    break;
  case 3:
    DAT_00c21758 = 0;
    DAT_00c21750 = 0x3ff0000000000000;
    break;
  case 4:
    DAT_00c21760 = 0;
    DAT_00c21758 = 0x3ff0000000000000;
    break;
  case 5:
    DAT_00c21768 = 0;
    DAT_00c21760 = 0x3ff0000000000000;
    break;
  case 6:
    DAT_00c21770 = 0;
    DAT_00c21768 = 0x3ff0000000000000;
    break;
  case 7:
    DAT_00c21778 = 0;
    DAT_00c21770 = 0x3ff0000000000000;
    break;
  case 8:
    DAT_00c21780 = 0;
    DAT_00c21778 = 0x3ff0000000000000;
    break;
  case 9:
    DAT_00c21788 = 0;
    DAT_00c21780 = 0x3ff0000000000000;
    break;
  case 10:
    DAT_00c21790 = 0;
    DAT_00c21788 = 0x3ff0000000000000;
    break;
  case 11:
    DAT_00c21798 = 0;
    DAT_00c21790 = 0x3ff0000000000000;
    break;
  case 12:
    DAT_00c217a0 = 0;
    DAT_00c21798 = 0x3ff0000000000000;
    break;
  case 13:
    DAT_00c217a8 = 0;
    DAT_00c217a0 = 0x3ff0000000000000;
    break;
  case 14:
    DAT_00c217b0 = 0;
    DAT_00c217a8 = 0x3ff0000000000000;
    break;
  case 15:
    DAT_00c217b8 = 0;
    DAT_00c217b0 = 0x3ff0000000000000;
    break;
  case 16:
    DAT_00c217c0 = 0;
    DAT_00c217b8 = 0x3ff0000000000000;
    break;
  case 17:
    DAT_00c217c8 = 0;
    DAT_00c217c0 = 0x3ff0000000000000;
    break;
  case 18:
    DAT_00c217d0 = 0;
    DAT_00c217c8 = 0x3ff0000000000000;
    break;
  case 19:
    DAT_00c217d8 = 0;
    DAT_00c217d0 = 0x3ff0000000000000;
    break;
  case 20:
    DAT_00c217e0 = 0;
    DAT_00c217d8 = 0x3ff0000000000000;
    break;
  case 21:
    DAT_00c217e8 = 0;
    DAT_00c217e0 = 0x3ff0000000000000;
    break;
  case 22:
    DAT_00c217f0 = 0;
    DAT_00c217e8 = 0x3ff0000000000000;
    break;
  case 23:
    DAT_00c217f8 = 0;
    DAT_00c217f0 = 0x3ff0000000000000;
    break;
  case 24:
    DAT_00c21800 = 0;
    DAT_00c217f8 = 0x3ff0000000000000;
    break;
  case 25:
    DAT_00c21808 = 0;
    DAT_00c21800 = 0x3ff0000000000000;
    break;
  case 26:
    DAT_00c21810 = 0;
    DAT_00c21808 = 0x3ff0000000000000;
    break;
  case 27:
    DAT_00c21818 = 0;
    DAT_00c21810 = 0x3ff0000000000000;
    break;
  case 28:
    DAT_00c21820 = 0;
    DAT_00c21818 = 0x3ff0000000000000;
    break;
  case 29:
    DAT_00c21828 = 0;
    DAT_00c21820 = 0x3ff0000000000000;
    break;
  case 30:
    DAT_00c21830 = 0;
    DAT_00c21828 = 0x3ff0000000000000;
    break;
  case 31:
    DAT_00c21838 = 0;
    DAT_00c21830 = 0x3ff0000000000000;
    break;
  case 32:
    DAT_00c21840 = 0;
    DAT_00c21838 = 0x3ff0000000000000;
    break;
  case 33:
    DAT_00c21848 = 0;
    DAT_00c21840 = 0x3ff0000000000000;
    break;
  case 34:
    DAT_00c21850 = 0;
    DAT_00c21848 = 0x3ff0000000000000;
    break;
  case 35:
    DAT_00c21858 = 0;
    DAT_00c21850 = 0x3ff0000000000000;
    break;
  case 36:
    DAT_00c21860 = 0;
    DAT_00c21858 = 0x3ff0000000000000;
    break;
  case 37:
    DAT_00c21868 = 0;
    DAT_00c21860 = 0x3ff0000000000000;
    break;
  case 38:
    DAT_00c21870 = 0;
    DAT_00c21868 = 0x3ff0000000000000;
    break;
  case 39:
    DAT_00c21878 = 0;
    DAT_00c21870 = 0x3ff0000000000000;
    break;
  }
}
"""
    events = [
        _event(1, 1, 0x007B4029, 1, 0),
        _event(2, 1, 0x007B4034, 2, 0),
        _event(3, 1, 0x007B403F, 3, 0),
        _event(4, 1, 0x007B40CB, 20, 1),
    ]

    result = runtime.expand_runtime_reset_footprint(
        source_pattern,
        events,
        provider_id=0,
    )

    assert result["runtime_event_input_count"] == 4
    assert result["runtime_event_provider_filtered_count"] == 3
    assert result["frames"][0]["runtime_selector_count"] == 3


def test_summarize_selector_reset_footprint():
    result = runtime.summarize_selector_reset_footprint(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "static_selector_footprint": {
                "selectors": [
                    {"selector": 0, "touched_count": 2},
                    {"selector": 1, "touched_count": 3},
                ]
            },
            "frames": [
                {"runtime_selector_count": 5, "unknown_selector_count": 0},
                {"runtime_selector_count": 2, "unknown_selector_count": 1},
            ],
            "ready": True,
        }
    )

    assert result["selector_count"] == 2
    assert result["total_selector_touched_addresses"] == 5
    assert result["runtime_selector_count"] == 7
    assert result["unknown_runtime_selector_count"] == 1
