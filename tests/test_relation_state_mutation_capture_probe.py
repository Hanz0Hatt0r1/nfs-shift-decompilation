from pathlib import Path


def test_phase635_gdb_probe_observes_relation_state_mutation_without_scheduling():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    assert "class RelationStateMutationProbe(_BaseProbe)" in source
    assert 'FUNCTIONS["relation_state_mutation"]' in source
    assert '"relation_state_mutation_events.jsonl"' in source
    assert 'gdb.parse_and_eval("$eax")' in source
    assert 'gdb.parse_and_eval("$ecx")' in source
    assert 'RELATION_STATE_MUTATION_LAYOUT["component_base_offset"]' in source
    assert 'RELATION_STATE_MUTATION_LAYOUT["wheel_body_offset"]' in source
    assert 'RELATION_STATE_MUTATION_LAYOUT["spindle_body_offset"]' in source
    assert 'RELATION_STATE_MUTATION_LAYOUT["rear_axle_body_offset"]' in source
    assert "describe_relation_state_mutation_entry(" in source

    assert '"runtime_event_sequence": runtime_event_sequence' in source
    assert '"frame_entry_runtime_event_sequence"' in source
    assert '"scalar_reset_events_since_frame_entry"' in source

    full_mode = source.index("if not provider_only:")
    mutation_install = source.index("RelationStateMutationProbe(", full_mode)
    provider_install = source.index("ProviderSolveProbe(", mutation_install)
    assert full_mode < mutation_install < provider_install

    assert "return False" in source[source.index("class RelationStateMutationProbe"):source.index("class FrameEntryProbe")]


def test_phase635_runtime_event_sequence_anchors_solver_frame_order():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    assert "_RUNTIME_EVENT_SEQUENCE = 0" in source
    assert "def _next_runtime_event_sequence()" in source
    assert '_LAST_FRAME_ENTRY["runtime_event_sequence"] = runtime_event_sequence' in source

    for class_name in (
        "ScalarResetProbe",
        "RelationStateMutationProbe",
        "FrameEntryProbe",
        "SolverEntryProbe",
        "ProviderSolveProbe",
        "PostSolveProbe",
    ):
        start = source.index(f"class {class_name}")
        next_class = source.find("\nclass ", start + 1)
        block = source[start:] if next_class < 0 else source[start:next_class]
        assert "_next_runtime_event_sequence()" in block


def test_phase643_gdb_probe_isolates_and_stamps_capture_sessions():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    assert "_CAPTURE_SESSION_ID: str | None = None" in source
    assert "def _stamp_capture_session(payload: dict)" in source
    assert 'stamped["capture_session_id"] = _CAPTURE_SESSION_ID' in source
    assert '"--session-id"' in source
    assert "capture_artifact_paths(output)" in source
    assert "capture output contains stale evidence artifacts" in source
    assert "_RUNTIME_EVENT_SEQUENCE = 0" in source
    assert "_SCALAR_RESET_EVENT_COUNT = 0" in source
    assert '"runtime_event_sequence": None' in source


def test_phase646_lightweight_relation_mode_uses_metadata_only_post_solve_anchor():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    assert '"--relation-timeline-only"' in source
    assert "class PostSolveAnchorProbe(_BaseProbe)" in source
    start = source.index("class PostSolveAnchorProbe(_BaseProbe)")
    end = source.index("class SDFProbeCommand", start)
    block = source[start:end]
    assert "_next_runtime_event_sequence()" in block
    assert 'gdb.parse_and_eval("$ecx")' in block
    assert "_doubles(" not in block
    assert "_u32(" not in block
    assert '"capture_kind": "post_solve_anchor"' in block

    install = source.index("if relation_timeline_only:")
    provider_install = source.index("if not relation_timeline_only:", install)
    assert "PostSolveAnchorProbe(" in source[install:provider_install]
    assert "ProviderSolveProbe(" not in source[install:provider_install]


def test_phase647_relation_probe_can_stop_after_first_mutation():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    start = source.index("class RelationStateMutationProbe(_BaseProbe)")
    end = source.index("class FrameEntryProbe", start)
    block = source[start:end]
    assert "global _RELATION_MUTATION_OBSERVED" in block
    assert "_RELATION_MUTATION_OBSERVED = True" in block
    assert "return False" in block

    command_start = source.index("class SDFProbeCommand")
    command_block = source[command_start:]
    assert '"--stop-after-relation-mutation"' in command_block
    assert "stop_after_relation_mutation = False" in command_block
    assert "stop_after_relation_mutation=(" in command_block
    assert "_RELATION_MUTATION_OBSERVED = False" in command_block
    assert "--stop-after-relation-mutation is not supported in provider-only mode" in command_block
