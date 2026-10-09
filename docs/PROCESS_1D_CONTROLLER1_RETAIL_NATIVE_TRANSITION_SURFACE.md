# Process 1D — Controller #1 retail native-transition surface

## Result

PR #1699 added a Ghidra function-scoped primitive exporter for `SYSENTER`, `INT 0x2e`, and manual PEB/export-walk hints. The authoritative PC retail 1.02 `SHIFT.exe` exposes one important coverage gap in that approach: one real instruction-aligned native transition lies outside every sized Ghidra function record.

Whole-PE `objdump -Mintel -d` over the hash-pinned executable finds exactly one instruction-aligned native transition:

```text
0x004209c8  0f 34  sysenter
```

No instruction-aligned `INT 0x2e` exists.

The local machine context is:

```text
0x004209bc  pop edi
0x004209bd  pop esi
0x004209be  pop ebp
0x004209bf  ret 0x4
0x004209c2..0x004209c7  int3 padding
0x004209c8  sysenter
0x004209ca  jmp 0x00400739
```

The `0x004209c8` address is outside all 41,538 sized functions in the current Drive Ghidra SQLite index. The function-scoped #1699 exporter therefore cannot emit it.

## Raw byte cross-check

Raw signature scanning alone would overcount native transitions:

```text
0f 34 hits: 0x004209c8, 0x00943f07
cd 2e hits: 0x004d15e8, 0x008b9a2b, 0x008ba262
```

Only `0x004209c8` is an instruction boundary. The other `0f 34` bytes occur inside a `MOV` displacement, while all `cd 2e` hits are bytes of the absolute address `0x00be2ecd` embedded in ordinary `CMP`/`MOV` instructions.

## Static entry bound

The whole disassembly contains zero direct `CALL` or `Jcc/JMP` references to `0x004209c8`.

That is a useful negative bound, but not an unreachable theorem. The candidate may still be entered through an indirect pointer, computed transfer, callback, generated code, or an external control-flow mechanism. No such indirect entry is currently proven or ruled out.

## Gate

```text
whole-PE SYSENTER/INT2E instruction surface bounded = true
function-scoped Ghidra coverage complete            = false
direct static entry to 0x004209c8 present           = false
indirect entry ruled out                             = false
native service identity proven                       = false
Controller #1 target-thread join complete            = false
native/syscall APC injection ruled out               = false
Controller #1 timing exhaustive                      = false
P1.3D complete                                       = false
provider count                                       = 7
```

A `SYSENTER` instruction is not itself APC evidence. Promotion requires exact service setup/identity plus exact Controller #1 thread-handle provenance.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_controller1_retail_native_transitions.py \
  /path/to/SHIFT.exe \
  /path/to/shift_ghidra.sqlite \
  --output out/p1d_controller1_retail_native_transition_surface.json
```

The analyzer requires GNU `objdump` and refuses a PE whose SHA-256 differs from the authoritative PC retail 1.02 hash.

## Next step

Recover every pointer/data reference or computed entry path that can target orphan `0x004209c8`. If a path is reachable from the Controller #1 worker, recover the exact native service setup and target thread. In parallel, continue the manual PEB/export-walk branch from #1699/#1712.
