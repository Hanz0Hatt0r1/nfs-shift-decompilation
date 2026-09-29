from pathlib import Path


PROBE = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "gdb_sdf_solver_probe.py"
)


def test_provider_gdb_probe_contains_entry_and_return_hooks():
    text = PROBE.read_text(encoding="utf-8")

    assert "class ProviderSolveProbe" in text
    assert "class ProviderSolveReturnProbe" in text
    assert "gdb.FinishBreakpoint" in text
    assert "provider_pre_{self.provider_id}_{self.hit:06d}.json" in text
    assert "provider_post_{self.provider_id}_{self.hit:06d}.json" in text


def test_provider_gdb_probe_installs_both_specialized_solvers():
    text = PROBE.read_text(encoding="utf-8")

    assert "get_provider(0).solve_function" in text
    assert "get_provider(1).solve_function" in text
    assert 'stage="pre-solve-provider"' in text
    assert '"post-solve-provider"' in text


def test_frame_entry_state_is_carried_to_provider_snapshots():
    text = PROBE.read_text(encoding="utf-8")

    assert "_LAST_FRAME_ENTRY" in text
    assert '"frame_index": self.hit' in text
    assert '"physics_system": physics_system' in text

def test_provider_gdb_probe_has_low_stop_provider_only_mode():
    text = PROBE.read_text(encoding="utf-8")

    assert "--provider-only" in text
    assert "provider_only = False" in text
    assert "if not provider_only:" in text
    assert 'self.condition = _provider_vtable_condition(' in text
    assert 'pointer_expr="$ecx+0x48"' in text
    assert 'pointer_expr="$ecx",' in text

def test_provider_only_mode_does_not_use_builtin_breakpoints():
    text = PROBE.read_text(encoding="utf-8")

    start = text.index("        self.breakpoints = []")
    end = text.index("        print(", start)
    block = text[start:end]
    assert "if not provider_only:" in block
    assert "SolverEntryProbe(" in block
    assert "PostSolveProbe(" in block
    assert "ProviderSolveProbe(" in block
