from pathlib import Path

from tools.ghidra.build_shift_pcode_linux_partial import split_delta_source

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
    assert "runtime_source, _ = compile_function(row, spaces)" in text
    assert "base shard function inventory does not match its build report" in text


def test_linux_elf_smoke_harness_checks_generated_function_behavior() -> None:
    runner = ROOT / "tools/ghidra/smoke_shift_pcode_elf.sh"
    harness = ROOT / "tools/ghidra/smoke_shift_pcode_elf.c"
    text = harness.read_text(encoding="utf-8")
    assert runner.stat().st_mode & 0o111
    assert 'dlsym(library, "rvi_00401000")' in text
    assert "state.last_call == 0x00685700" in text
    assert "eax == esi && stored == 0x00aa99d0" in text


def test_linux_delta_builder_repeats_runtime_across_bounded_shards(tmp_path: Path) -> None:
    source = tmp_path / "delta.c"
    source.write_text(
        "#include <stdint.h>\nstatic int runtime_helper(void) { return 0; }\n"
        "/* Generated from raw P-code for one (0x00401000). */\n"
        "int rvi_00401000(RviPcodeContext *ctx) { return runtime_helper() + (ctx != 0); }\n"
        "/* Generated from raw P-code for two (0x00401010). */\n"
        "int rvi_00401010(RviPcodeContext *ctx) { return runtime_helper() + (ctx != 0); }\n",
        encoding="utf-8",
    )
    shards = split_delta_source(source, tmp_path / "shards", 1)
    assert [shard["functions"] for shard in shards] == [1, 1]
    assert all("static int runtime_helper" in Path(shard["path"]).read_text() for shard in shards)
    assert "rvi_00401000" in Path(shards[0]["path"]).read_text()
    assert "rvi_00401010" in Path(shards[1]["path"]).read_text()
