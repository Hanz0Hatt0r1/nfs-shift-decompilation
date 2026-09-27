import gearbox_gdf_runtime as gdf


def test_gdf_parses_both_runtime_sections_and_ratio_pairs():
    report = gdf.parse_gdf("""
[GEAR_RATIOS]
ratio=(10,35)
ratio=(12,36)
[FINAL_DRIVE]
bevel=(1,1)
ratio=(6,39)
""")
    assert report["ready"] is True
    assert report["section_count"] == 2
    assert report["gear_ratio_count"] == 2
    assert report["final_drive_ratio_count"] == 1
    assert report["final_drive_bevel"] == [[1,1]]
    assert gdf.entries(report, "GEAR_RATIOS", "ratio")[0]["value"] == [10,35]


def test_gdf_unknown_entries_are_retained():
    report = gdf.parse_gdf("[FINAL_DRIVE]\nratio=(6,39)\nunknown=7\n")
    row = gdf.entries(report, "FINAL_DRIVE", "unknown")[0]
    assert row["recognized_by_loader"] is False
    assert row["value"] == 7
