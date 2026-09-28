from pathlib import Path


PROBE = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "gdb_sdf_solver_probe.py"
)


def test_scalar_reset_probe_is_declared_after_base_probe():
    text = PROBE.read_text(encoding="utf-8")

    assert text.index("class _BaseProbe") < text.index(
        "class ScalarResetProbe"
    )


def test_scalar_reset_probe_reads_this_stack_selector_and_return_address():
    text = PROBE.read_text(encoding="utf-8")

    assert 'physics_system = int(gdb.parse_and_eval("$ecx"))' in text
    assert 'selector = _u32(inferior, esp + 0x04)' in text
    assert 'caller_return_address = _u32(inferior, esp)' in text


def test_scalar_reset_probe_records_raw_provider_provenance():
    text = PROBE.read_text(encoding="utf-8")

    assert "provider_pointer = _u32(" in text
    assert "provider_id, provider_vtable = _provider_id_from_runtime_pointer(" in text
    assert '"provider_pointer": provider_pointer' in text
    assert '"provider_vtable": provider_vtable' in text
    assert '"provider_id": provider_id' in text


def test_scalar_reset_probe_appends_jsonl_and_continues():
    text = PROBE.read_text(encoding="utf-8")

    assert 'def _append_jsonl(' in text
    assert '"scalar_reset_events.jsonl"' in text
    assert "return False" in text


def test_scalar_reset_probe_is_installed_at_FUN_007b2210():
    text = PROBE.read_text(encoding="utf-8")

    assert "ScalarResetProbe(" in text
    assert "0x007B2210" in text
    assert '"scalar_reset=0x007b2210"' in text


def test_unknown_provider_vtable_is_fail_closed_by_schema():
    text = PROBE.read_text(encoding="utf-8")

    assert "unknown-provider-vtable" in (
        Path(
            Path(__file__).resolve().parents[1]
            / "src/physics/providers/specialized_provider_scalar_reset_capture_runtime.py"
        ).read_text(encoding="utf-8")
    )


def test_scalar_reset_probe_embeds_callsite_attribution():
    text = PROBE.read_text(encoding="utf-8")

    assert "from specialized_provider_scalar_reset_callsite_runtime import" in text
    assert "attribution = attribute_reset_event(event)" in text
    assert '"callsite": attribution' in text
    assert 'bool(attribution["ready"])' in text


def test_scalar_reset_probe_blocks_unattributed_events():
    text = PROBE.read_text(encoding="utf-8")

    assert 'event["capture_ready"] = (' in text
    assert '"capture_errors"' in text
    assert 'list(attribution.get("errors") or [])' in text


def test_provider_snapshot_carries_scalar_reset_counters():
    text = PROBE.read_text(encoding="utf-8")

    assert '"scalar_reset_event_count": _SCALAR_RESET_EVENT_COUNT' in text
    assert '"scalar_reset_events_since_frame_entry"' in text
    assert '"scalar_reset_start_count"' in text
    assert '"scalar_reset_end_count"' in text


def test_scalar_reset_probe_is_the_only_counter_increment_site():
    text = PROBE.read_text(encoding="utf-8")

    assert text.count('_SCALAR_RESET_EVENT_COUNT += 1') == 1
    assert '_LAST_FRAME_ENTRY["scalar_reset_end_count"] = _SCALAR_RESET_EVENT_COUNT' in text


def test_frame_entry_resets_per_frame_counter_baseline():
    text = PROBE.read_text(encoding="utf-8")

    marker = '_LAST_FRAME_ENTRY["frame_index"] = self.hit'
    start = text.index(marker)
    tail = text[start:start + 500]
    assert '_LAST_FRAME_ENTRY["scalar_reset_start_count"] = (' in tail
    assert '_LAST_FRAME_ENTRY["scalar_reset_end_count"] = (' in tail


def test_provider_reset_effect_probe_is_present_for_both_resets():
    text = PROBE.read_text(encoding="utf-8")

    assert "class ProviderResetProbe" in text
    assert "class ProviderResetReturnProbe" in text
    assert "get_provider(0).reset_function" in text
    assert "get_provider(1).reset_function" in text
    assert '"provider_reset_effects.jsonl"' in text


def test_provider_reset_effect_probe_reads_sentinel_cells():
    text = PROBE.read_text(encoding="utf-8")

    assert "get_row_pointers(self.provider_id)[selector]" in text
    assert "row_pointer + selector * 8" in text
    assert "addresses.output_vector_base + selector * 8" in text
    assert "diagonal_before = _doubles(" in text
    assert "output_before = _doubles(" in text


def test_provider_reset_effect_return_probe_keeps_lifetime_reference():
    text = PROBE.read_text(encoding="utf-8")

    assert "self.return_breakpoints: list[ProviderResetReturnProbe] = []" in text
    assert "self.return_breakpoints.append(return_probe)" in text


def test_provider_reset_effect_probe_uses_scalar_reset_counter():
    text = PROBE.read_text(encoding="utf-8")

    assert '"reset_event_count": self.reset_event_count' in (
        Path(
            Path(__file__).resolve().parents[1]
            / "src/physics/providers/specialized_provider_scalar_reset_effect_runtime.py"
        ).read_text(encoding="utf-8")
    )
    assert "_SCALAR_RESET_EVENT_COUNT" in text


def test_provider_reset_addresses_use_vtable_lifecycle_api():
    text = PROBE.read_text(encoding="utf-8")

    assert "from specialized_provider_vtable_lifecycle_runtime import" in text
    assert "get_vtable_lifecycle(0).reset_function" in text
    assert "get_vtable_lifecycle(1).reset_function" in text
    assert "get_provider(0).reset_function" not in text
    assert "get_provider(1).reset_function" not in text
