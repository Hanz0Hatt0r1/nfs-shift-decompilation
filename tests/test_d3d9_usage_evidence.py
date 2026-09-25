from d3d9_usage_evidence import analyze_d3d9_usage_semantics


def test_usage_ordinal_contract_keeps_numeric_d3d9_usage_unproven():
    source = """
uint __fastcall FUN_008587e0(int param_1)
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
pbVar17 = (&PTR_s_Position_00b901a8)[local_5c];
uVar9 = FUN_00853c40(local_5c);
"""
    report = analyze_d3d9_usage_semantics(source)
    colour = report["usages"][6]
    assert colour["usage_ordinal"] == 6
    assert colour["source_name"] == "Colour"
    assert colour["status"] == "observed"
    assert colour["numeric_d3d9_usage"] is None
    assert colour["numeric_d3d9_usage_status"] == "not-proven"
    assert "DAT_00b9011c[usage_ordinal]" in colour["numeric_d3d9_usage_source"]
