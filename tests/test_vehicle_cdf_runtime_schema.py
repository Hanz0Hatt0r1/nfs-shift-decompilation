def test_source_schema_matches_all_retail_bmw_wheel_keys():
    from vehicle_cdf_runtime import source_schema
    expected = {
        "BumpTravel", "ReboundTravel", "BumpStopSpring", "BumpStopRisingSpring",
        "BumpStopDamper", "BumpStopRisingDamper", "BumpStage2", "ReboundStage2",
        "FrictionTorque", "SpinInertia", "CGOffsetX", "PushrodSpindle", "PushrodBody",
        "CamberRange", "CamberSetting", "PressureRange", "PressureSetting",
        "PackerRange", "PackerSetting", "SpringMult", "SpringRange", "SpringSetting",
        "RideHeightRange", "RideHeightSetting", "DamperMult", "SlowBumpRange",
        "SlowBumpSetting", "FastBumpRange", "FastBumpSetting", "SlowReboundRange",
        "SlowReboundSetting", "FastReboundRange", "FastReboundSetting",
        "BrakeDiscRange", "BrakeDiscSetting", "BrakePadRange", "BrakePadSetting",
        "BrakeDiscInertia", "BrakeOptimumTemp", "BrakeFadeRange", "BrakeWearRate",
        "BrakeFailure", "BrakeTorque", "BrakeHeating", "BrakeCooling", "BrakeDuctCooling",
    }
    schema = source_schema("FRONTLEFT")["properties"]
    assert expected.issubset(schema)
    assert len(expected) == 46
    assert schema["DamperMult"]["helper"] == "FUN_007a75a0"
    assert schema["SpringMult"]["helper"] == "FUN_007a75a0"
    assert schema["SlowBumpRange"]["helper"] == "FUN_007a6a90"


def test_source_schema_keeps_real_unknown_general_keys_unresolved():
    report = __import__("vehicle_cdf_runtime").parse_cdf("[GENERAL]\nFeelerFlags=0\nNotes=""\n")
    assert report["unknown_entry_count"] == 2
    assert all(not entry["recognized"] for entry in report["sections"][0]["entries"])
