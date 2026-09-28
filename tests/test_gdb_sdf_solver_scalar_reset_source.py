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
            / "specialized_provider_scalar_reset_capture_runtime.py"
        ).read_text(encoding="utf-8")
    )
