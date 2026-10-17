from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shift_native_pcode_runner_delegates_to_shared_lowerer() -> None:
    runner = ROOT / "tools/ghidra/run_shift_pcode_native_lowering.sh"
    text = runner.read_text(encoding="utf-8")
    assert "REVENGINSTR_REPO" in text
    assert "src/revenginstr/pcode/c_lowering_corpus.py" in text
    assert "revenginstr.pcode.c_lowering_corpus" in text
    assert '"$CORPUS" "$MANIFEST" "$ADDRESS_SPACES" "$OUTPUT_DIR" "$@"' in text
    assert runner.stat().st_mode & 0o111


def test_shift_pcode_delta_emitter_reuses_the_shared_lowerer() -> None:
    emitter = ROOT / "tools/ghidra/emit_shift_pcode_delta.py"
    text = emitter.read_text(encoding="utf-8")
    assert "from revenginstr.pcode.c_lowering import" in text
    assert "compile_function(row, spaces, include_runtime=False)" in text
    assert "base shard function inventory does not match its build report" in text


def test_linux_elf_smoke_harness_checks_generated_function_behavior() -> None:
    runner = ROOT / "tools/ghidra/smoke_shift_pcode_elf.sh"
    harness = ROOT / "tools/ghidra/smoke_shift_pcode_elf.c"
    text = harness.read_text(encoding="utf-8")
    assert runner.stat().st_mode & 0o111
    assert 'dlsym(library, "rvi_00401000")' in text
    assert "state.last_call == 0x00685700" in text
    assert "eax == esi && stored == 0x00aa99d0" in text
