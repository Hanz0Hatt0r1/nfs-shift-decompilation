import math

from ai_database_load_runtime import (
    CURRENT_ADJUST_OFFSET,
    DATABASE_PATH_OBJECT_OFFSET,
    DATABASE_PATH_OVERRIDE_FLAG_OFFSET,
    FORMAT,
    LOAD_STATE_OFFSET,
    META_FILE_PATH_GLOBAL,
    WAYPOINT_COUNT_OFFSET,
    WAYPOINT_LINK_NEXT_OFFSET,
    WAYPOINT_PTR_OFFSET,
    WAYPOINT_STRIDE,
    aiw_load_preset_writes,
    build_aiw_load_trace,
    derive_generated_meta_flag,
    describe_ai_database_load_runtime,
    describe_section_generation_lifecycle,
    describe_waypoint_post_load_passes,
)
from ai_database_runtime import (
    META_RECORD_COUNT_OFFSET,
    META_RECORD_PTR_OFFSET,
    META_RECORD_STRIDE,
    META_REBUILD_FLAG_OFFSET,
    SOURCE_RECORD_COUNT_OFFSET,
    SOURCE_RECORD_PTR_OFFSET,
    SOURCE_RECORD_STRIDE,
)


def test_aiw_load_preset_matches_fun_00720190():
    writes = {row["offset"]: row for row in aiw_load_preset_writes()}
    assert writes[0x10]["float_value"] == -1.0
    assert writes[0x78]["float_value"] == 3.0
    assert writes[0x7C]["float_value"] == 1.0
    assert writes[0x80]["float_value"] == 2.0
    assert writes[0x50]["float_value"] == 0.5
    assert math.isclose(writes[0x58]["float_value"], 1.3, rel_tol=1e-6)
    assert writes[WAYPOINT_COUNT_OFFSET]["raw_value"] == 0
    assert writes[WAYPOINT_PTR_OFFSET]["raw_value"] == 0
    assert writes[LOAD_STATE_OFFSET]["raw_value"] == 1
    assert writes[0x28]["width"] == 1
    assert writes[0x29]["width"] == 1
    assert writes[0x2A]["width"] == 1


def test_waypoint_storage_and_post_load_pass_order_are_exact():
    report = describe_ai_database_load_runtime()
    assert report["format"] == FORMAT
    assert report["waypoints"]["count_offset"] == 0x68
    assert report["waypoints"]["pointer_offset"] == 0x70
    assert report["waypoints"]["stride"] == 0x1BC
    assert report["waypoints"]["classification_offset"] == 0x6C
    assert report["waypoints"]["next_link_offset"] == 0x180

    passes = describe_waypoint_post_load_passes()
    assert [row["function"] for row in passes] == [
        "FUN_007ada70",
        "FUN_007ad940",
        "FUN_007acef0",
    ]
    assert all(row["record_stride"] == WAYPOINT_STRIDE for row in passes)
    assert passes[2]["arguments"] == [
        "waypoint",
        f"waypoint+0x{WAYPOINT_LINK_NEXT_OFFSET:x}",
    ]


def test_persistent_load_success_skips_fallback_and_sets_meta_flag():
    trace = build_aiw_load_trace(
        persistent_load_succeeded=True,
        meta_file_loaded=True,
    )
    assert trace["status"] == "loaded-persistent"
    actions = [row["action"] for row in trace["actions"]]
    assert "fallback-open" not in actions
    assert actions[:5] == [
        "reset",
        "apply-load-preset",
        "default-database-path-if-not-overridden",
        "pre-load-cleanup",
        "persistent-load",
    ]
    assert trace["generated_meta_flag"] == 0
    assert derive_generated_meta_flag(True) == 0


def test_failed_primary_and_failed_fallback_is_fail_closed():
    trace = build_aiw_load_trace(
        persistent_load_succeeded=False,
        fallback_open_succeeded=False,
    )
    assert trace["status"] == "failed-open"
    assert trace["post_load_waypoint_passes"] == []
    assert trace["generated_meta_flag"] is None
    assert trace["actions"][-2] == {
        "action": "write-load-state",
        "offset": LOAD_STATE_OFFSET,
        "value": 0,
    }
    assert trace["actions"][-1]["action"] == "post-failure-cleanup"
    fallback = next(row for row in trace["actions"] if row["action"] == "fallback-open")
    assert fallback["failure_log"] == "Unable to open AIW %s"


def test_fallback_success_preserves_optional_resource_activation():
    trace = build_aiw_load_trace(
        persistent_load_succeeded=False,
        fallback_open_succeeded=True,
        fallback_resource_present=True,
        meta_file_loaded=False,
    )
    assert trace["status"] == "loaded-fallback"
    actions = [row["action"] for row in trace["actions"]]
    assert "fallback-resource-activation" in actions
    assert trace["generated_meta_flag"] == 1
    assert derive_generated_meta_flag(False) == 1


def test_database_path_and_current_adjust_offsets_are_source_backed():
    report = describe_ai_database_load_runtime()
    assert report["database_path"] == {
        "object_offset": DATABASE_PATH_OBJECT_OFFSET,
        "override_flag_offset": DATABASE_PATH_OVERRIDE_FLAG_OFFSET,
        "default_global": "DAT_00c13420",
    }
    assert CURRENT_ADJUST_OFFSET == 0x4C
    current = next(
        row for row in build_aiw_load_trace(
            persistent_load_succeeded=True
        )["actions"]
        if row["action"] == "current-adjust-from-mid-adjust"
    )
    assert current["destination_offset"] == 0x4C
    assert current["source_offset"] == 0x54


def test_external_meta_file_success_inverts_generated_meta_flag():
    trace = build_aiw_load_trace(
        persistent_load_succeeded=True,
        meta_file_loaded=False,
    )
    meta_action = next(
        row for row in trace["actions"]
        if row["action"] == "load-meta-file"
    )
    flag_action = next(
        row for row in trace["actions"]
        if row["action"] == "write-generated-meta-flag"
    )
    assert meta_action["path_global"] == META_FILE_PATH_GLOBAL
    assert meta_action["succeeded"] is False
    assert flag_action["offset"] == META_REBUILD_FLAG_OFFSET
    assert flag_action["value"] == 1


def test_section_generation_reuses_recovered_source_and_meta_arrays():
    lifecycle = describe_section_generation_lifecycle()
    source = lifecycle["source_records"]
    meta = lifecycle["generated_meta_records"]

    assert source["pointer_offset"] == SOURCE_RECORD_PTR_OFFSET == 0x1394
    assert source["count_offset"] == SOURCE_RECORD_COUNT_OFFSET == 0x1398
    assert source["stride"] == SOURCE_RECORD_STRIDE == 0x18
    assert source["constructor"] == "FUN_00702a10"
    assert source["materializer"] == "FUN_00702a40"

    assert meta["pointer_offset"] == META_RECORD_PTR_OFFSET == 0x139C
    assert meta["count_offset"] == META_RECORD_COUNT_OFFSET == 0x13A0
    assert meta["stride"] == META_RECORD_STRIDE == 0x14
    assert meta["function"] == "FUN_0071dc90"

    condition = lifecycle["generation_condition"]
    assert condition["flag_offset"] == META_REBUILD_FLAG_OFFSET == 0x13A4
    assert condition["generated_when"] == 1
    assert condition["external_meta_loaded_when"] == 0
    assert "ai_db.cpp" in lifecycle["evidence"]["source_file"]


def test_loader_contract_does_not_claim_parser_or_waypoint_math():
    report = describe_ai_database_load_runtime()
    assert "does not implement the AIW parser" in report["evidence_boundary"]
