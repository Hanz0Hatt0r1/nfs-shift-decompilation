# Process 0 — native P-code lowering

The initial generic C lowerer accepted **35,004 of 41,538** functions in the
hash-pinned SHIFT PC retail 1.02 instruction corpus (84.27%). Those functions
contain 1,288,871 machine instructions and 4,970,468 P-code operations. The
coverage report is
[`evidence/pcode_native_lowering_coverage_20261017.json`](../evidence/pcode_native_lowering_coverage_20261017.json);
it pins the corpus, manifest, and
[`evidence/shift_language_address_spaces_20261017.json`](../evidence/shift_language_address_spaces_20261017.json)
hash.

The lowerer supports scalar integer and floating operations, memory callbacks,
direct and computed control flow, P-code-relative branches, calls, tail calls,
and generic `CALLOTHER` callbacks. Each generated function keeps its language
userop index and address spaces; the game-specific implementations remain in
this repository.

The initial 6,534 rejected functions included 65 repeat-string instructions
whose conditional P-code branch targets the same machine instruction even
though Ghidra labels the machine flow as fallthrough. `revenginstr` PR #126
adds that exact self-repeat case while still rejecting unrelated branch
targets. This raises the current lowerable count to **35,069 of 41,538**
(84.43%); 6,469 still fail closed: 6,440 use 10-byte x87 values, 28 use
16-byte values, and one has a computed call terminator whose P-code sequence
needs further inspection. The 10-byte values include x87 arithmetic and
conversions, so treating them as C `long double` without target-precision
checks would not be a verified lowering.

The NFS wrapper
[`tools/ghidra/run_shift_pcode_native_lowering.sh`](../tools/ghidra/run_shift_pcode_native_lowering.sh)
delegates to the generic `revenginstr-pcode-c-lowering-corpus` CLI. For a
reproducible run, pass the hash-pinned corpus, manifest, and address-space
table, then set the target compiler and shard limits:

```bash
REVENGINSTR_REPO=/path/to/revenginstr tools/ghidra/run_shift_pcode_native_lowering.sh /path/to/shift-functions.jsonl.gz /path/to/shift-functions.manifest.json evidence/shift_language_address_spaces_20261017.json /path/to/shift-pcode-native-shards --compiler i686-w64-mingw32-gcc --shard-size 500 --jobs 4
```

The Windows cross-build compiles lowerable functions with
`i686-w64-mingw32-gcc` into bounded COFF object shards. Its initial build report
is recorded in
[`evidence/pcode_native_lowering_build_20261017.json`](../evidence/pcode_native_lowering_build_20261017.json).
The original 71 COFF objects also link into a 1.3 GB PE32 partial DLL exporting
35,004 lowerable P-code functions. Its hash and PE export evidence are recorded
in [`evidence/pcode_windows_partial_dll_20261018.json`](../evidence/pcode_windows_partial_dll_20261018.json).
The native Linux build uses the same wrapper and inputs with `gcc` and PIC
objects:

```bash
REVENGINSTR_REPO=/path/to/revenginstr tools/ghidra/run_shift_pcode_native_lowering.sh \
  "$CORPUS" "$MANIFEST" evidence/shift_language_address_spaces_20261017.json \
  "$LINUX_OUT" --compiler gcc --shard-size 500 --jobs 4 --compiler-arg=-fPIC
gcc -shared -o "$LINUX_OUT/libnfs_shift_pcode_partial.so" "$LINUX_OUT"/shard-*.o -lm
tools/ghidra/smoke_shift_pcode_elf.sh "$LINUX_OUT/libnfs_shift_pcode_partial.so"
```

The harness calls generated function `0x00401000` with sparse register and
RAM callbacks and checks its result, direct call target, EAX value, and memory
write. This library executes native host code while
representing guest x86-32 state through callbacks; it is not a 32-bit Linux
game executable.

The original Linux shard build report is
[`evidence/pcode_native_lowering_linux_build_20261018.json`](../evidence/pcode_native_lowering_linux_build_20261018.json).
The linked library hash, ELF metadata, exported-function count, and smoke result
are recorded in
[`evidence/pcode_linux_native_smoke_20261018.json`](../evidence/pcode_linux_native_smoke_20261018.json).
The original 982 MB `.so` remains in the persistent artifact directory named
by that evidence record and is not stored in Git.

After `revenginstr` PR #126 merged, the NFS adapter
[`tools/ghidra/emit_shift_pcode_delta.py`](../tools/ghidra/emit_shift_pcode_delta.py)
compared generated exports with the hash-pinned corpus and emitted only the 65
newly lowerable functions. The supplemental source and its rejection counts
are recorded in
[`evidence/pcode_repeat_cbranch_delta_20261018.json`](../evidence/pcode_repeat_cbranch_delta_20261018.json).
The Linux and PE libraries were relinked with this shard and smoke/export
checked; their hashes are in
[`evidence/pcode_repeat_cbranch_build_20261018.json`](../evidence/pcode_repeat_cbranch_build_20261018.json).
The refreshed libraries remain outside Git in persistent artifact directories.

Generated C, objects, the partial DLL, and the partial `.so` stay in the
persistent artifact directory rather than Git. Linking and the Linux smoke
test do not provide complete function coverage, the original game's startup
and platform runtime, a reconstructed game link map, or behavioral parity.
Full NFS Shift recompilation remains open.
