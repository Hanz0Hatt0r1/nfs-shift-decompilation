from camera_config_manager_runtime import (
    describe_config_manager_refresh,
    describe_config_manager_reset,
    find_camera_config_index,
    get_camera_config_entry,
    load_camera_config_elements,
    rebuild_camera_config_list,
    release_camera_config_list,
    serialize_camera_config_list,
)


def test_get_config_entry_returns_null_when_index_is_out_of_range():
    result = get_camera_config_entry(entries=["a"], index=2)
    assert result["status"] == "out-of-range"
    assert result["value"] is None


def test_find_config_index_returns_first_helper_match():
    result = find_camera_config_index(
        entries=[
            {"matches_query": False},
            {"matches_query": True},
            {"matches_query": True},
        ],
        query="camera",
    )
    assert result["index"] == 1


def test_release_config_list_only_counts_non_null_entries():
    result = release_camera_config_list([None, "a", 0, "b"])
    assert result["released_count"] == 2


def test_save_serializer_walks_plus_44_list():
    result = serialize_camera_config_list(entries=["a", "b"])
    assert result["source_list"] == "+0x44"
    assert len([a for a in result["actions"] if a["action"] == "entry.vtable +0x04"]) == 2


def test_load_config_appends_when_no_existing_name_match():
    result = load_camera_config_elements(
        class_entries=[{"class": "A", "secondary": "x"}],
        existing_configs=[{"name": "B"}],
    )
    assert result["status"] == "ok"
    assert len(result["result_configs"]) == 2
    assert result["actions"][-1]["reason"] == "no existing name match"


def test_load_config_refreshes_existing_name_match():
    result = load_camera_config_elements(
        class_entries=[{"class": "A", "secondary": "new"}],
        existing_configs=[{"name": "A", "secondary": "old"}],
    )
    assert result["status"] == "ok"
    assert len(result["result_configs"]) == 1
    assert result["result_configs"][0]["secondary"] == "new"


def test_load_config_stops_on_failed_class_conversion():
    result = load_camera_config_elements(
        class_entries=[{"class": "A"}],
        existing_configs=[],
        class_conversion_success={0: False},
    )
    assert result["status"] == "failed-class-conversion"


def test_load_config_stops_on_failed_apply():
    result = load_camera_config_elements(
        class_entries=[{"class": "A"}],
        existing_configs=[],
        apply_success={0: False},
    )
    assert result["status"] == "failed-apply"


def test_rebuild_moves_configs_from_44_to_10():
    result = rebuild_camera_config_list(source_entries=[{"name": "A"}, {"name": "B"}])
    assert result["source_list"] == "+0x44"
    assert result["destination_list"] == "+0x10"
    assert result["count"] == 2


def test_refresh_builds_snapshot_static_and_tracking_temps_in_order():
    result = describe_config_manager_refresh(
        config_source_available=True,
        base_config_object="config",
    )
    assert [a["action"] for a in result["actions"][1:4]] == [
        "copy config into temporary snapshot",
        "copy config into static camera",
        "copy config into tracking camera",
    ]


def test_reset_matches_exact_order():
    result = describe_config_manager_reset()
    assert [a["action"] for a in result["actions"]] == [
        "write vtable",
        "FUN_00810490",
        "FUN_0081ea60",
        "FUN_00813500",
        "FUN_004f0050",
        "FUN_004f0050",
        "FUN_006383f0",
    ]


def test_save_serializer_keeps_vtable_and_writer_adjacent_per_entry():
    result = serialize_camera_config_list(entries=["a", "b"])
    assert [a["action"] for a in result["actions"]] == [
        "entry.vtable +0x04",
        "FUN_00640dd0",
        "entry.vtable +0x04",
        "FUN_00640dd0",
    ]
