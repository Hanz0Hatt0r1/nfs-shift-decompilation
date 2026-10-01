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
