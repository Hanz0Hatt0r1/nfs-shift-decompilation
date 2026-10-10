# Process 1A / P1.3A — `FUN_00757318` interior-alias closure

## Scope and authority

Consumes the merged `SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1` contract. The exact wheel root is `vehicle + 0x400 + index*0xa80`; the five pointers below are **interior field addresses**, not new exact wheel roots. The analyzer pins PC retail 1.02 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and SHA-256 of the full indexed body and both complete callees.

## Five positive handoffs

| Interior address | LEA site | Callsite | Exact ECX receiver callee |
| --- | --- | --- | --- |
| `wheel+0x610` | `0x007573bc` | `0x007573fd` | `FUN_007a06a0` |
| `wheel+0x638` | `0x0075740f` | `0x00757428` | `FUN_007a06a0` |
| `wheel+0x5e8` | `0x0075743a` | `0x00757453` | `FUN_007a06a0` |
| `wheel+0x6a0` | `0x007577b8` | `0x007577e4` | `FUN_007a0420` |
| `wheel+0x6c0` | `0x007577f6` | `0x0075780f` | `FUN_007a0420` |

No instruction between each LEA and call overwrites ECX or crosses a separate call/control-flow transfer. Ghidra identifies both callees as `__thiscall` with receiver in ECX.

## Callee lifetimes

`FUN_007a06a0` is a complete **279-byte** function. At `0x007a06b1` it captures the interior receiver in ESI. It performs nine branch-dependent FPU QWORD scalar writes at receiver-relative offsets `+0x20`, `+0x0`, `+0x8`, `+0x10`, `+0x18`. Its only two direct calls (`0x007a06d2 -> FUN_00753620`, `0x007a0777 -> FUN_007af310`) receive **stack-local ECX addresses**, not the interior receiver. After ESI capture, no instruction stores, forwards, or returns that pointer; `pop esi` only restores the saved register on exit.

`FUN_007a0420` is a complete **49-byte** leaf. Its only ECX-relative uses are four FPU QWORD scalar stores at `+0x0/+0x8/+0x10/+0x18`; it has no nested call or pointer copy/return.

The five interior aliases are therefore **positive address materializations with no pointer persistence in these bounded callees**. This is not evidence that other derived or runtime-reconstructed wheel pointers are absent.

## Gates

Promoted only:

```text
p13a_fun00757318_interior_alias_subset_complete       = true
p13a_fun00757318_interior_alias_persistent_escape_found = false
```

Remain false: broad reconstructed/runtime-generated selected-wheel pointer-store and stored/escaped-alias closures, callback and incoming-indirect closure, slot0, slot1, aggregate P1.3. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun00757318_interior_alias.py \
  /path/to/SHIFT.exe evidence/p1a_p13a_fun007572f0_indexed_wheel_root_lifetime.json \
  --output evidence/p1a_p13a_fun00757318_interior_alias_closure.json
pytest -q tests/test_process1a_p13a_fun00757318_interior_alias.py
```

Next: compose the separately closed indexed and trampolined exact wheel-root materializer families, then continue independent runtime callback/incoming-indirect evidence without promoting global gates prematurely.