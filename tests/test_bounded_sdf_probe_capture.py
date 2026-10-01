from pathlib import Path


def test_phase642_gdb_probe_parses_positive_capture_frame_budget():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")

    assert '"--capture-frames" in args' in source
    assert 'capture_frames = int(raw_capture_frames)' in source
    assert 'capture_frames <= 0' in source
    assert '"--capture-frames is not supported in provider-only mode"' in source


def test_phase642_post_solve_writes_snapshot_before_bounded_stop():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")
    start = source.index("class PostSolveProbe(_BaseProbe):")
    end = source.index("\nclass SDFProbeCommand", start)
    block = source[start:end]

    write_index = block.index(
        'self.write_json(f"post_solve_{self.hit:06d}.json", payload)'
    )
    stop_index = block.index("self.hit >= self.stop_after_hit")
    assert write_index < stop_index
    assert "stop_after_hit: int | None = None" in block
    assert "self.stop_after_hit = stop_after_hit" in block


def test_phase642_probe_installs_post_solve_terminal_budget():
    source = Path("tools/gdb_sdf_solver_probe.py").read_text(encoding="utf-8")
    start = source.index("class SDFProbeCommand")
    block = source[start:]

    assert "stop_after_hit=capture_frames" in block
    assert 'f"capture_frames={capture_frames},"' in block
