# Process 1D — Controller #1 retail PEB-walk surface

## Result

PR #1699 defined a conservative manual-resolver candidate as a function that combines:

```text
FS:[0x30] PEB access
PE +0x3c e_lfanew hint
PE32 +0x78 export-directory hint
```

A whole-PC-retail instruction scan now closes the first conjunct globally for the static executable image: there are **0** instruction-level accesses to `FS:[0x30]`.

The hash-pinned `SHIFT.exe` disassembly contains 2,845,103 parsed instructions and 3,458 instructions whose textual form contains an `FS:` segment override, but none addresses offset `0x30`.

Therefore the classic direct x86 path:

```text
FS:[0x30] -> PEB -> module list -> PE +0x3c -> export +0x78
```

is absent from the static PC retail instruction stream.

## What this closes

```text
whole-PE FS:[0x30] surface bounded       = true
standard direct FS:[0x30] PEB entry      = absent
standard FS30 PEB export walk ruled out  = true
```

This is stronger than relying on the function-scoped #1699 exporter because the scan covers the whole disassembled PE rather than only Ghidra-defined functions.

## What remains open

This result is intentionally narrow. It does **not** prove that every form of manual export resolution is absent. A module base can still be obtained through:

- `GetModuleHandle*` / `LoadLibrary*` or another loader path;
- an import/global/caller-provided module handle;
- an alternate TEB/PEB derivation that does not contain a direct `FS:[0x30]` instruction;
- generated/runtime code;
- another resolved pointer followed by manual PE export parsing.

Consequently:

```text
all manual export resolution ruled out   = false
hashed/generated resolution ruled out    = false
native/syscall APC injection ruled out   = false
Controller #1 timing exhaustive          = false
P1.3D complete                            = false
provider count                            = 7
```

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_controller1_retail_peb_walk_surface.py \
  /path/to/SHIFT.exe \
  --output out/p1d_controller1_retail_peb_walk_surface.json
```

The analyzer requires GNU `objdump` and refuses any executable whose SHA-256 differs from the authoritative PC retail 1.02 binary.

## Next step

Bound manual export parsing whose module base comes from non-PEB sources, especially the already-recovered loader/GetProcAddress neighborhoods. In parallel, continue the single orphan `SYSENTER` candidate `0x004209c8` from `SHIFT.P1D.Controller1RetailNativeTransitionSurface/1`.
