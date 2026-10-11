# Process 1A / P1.3A — transformed absolute `.data` values before near transfer

## Scope

The preceding absolute-data contracts bound same-register use and identity-preserving GPR copies. This pass asks whether a value loaded from writable `.data` can be arithmetically or address-transformed inside the same 16-instruction straight-line window and then consumed by an indirect `call/jmp`.

The analysis is dependency-taint, not exact pointer-value recovery. It preserves identity across `mov`/`xchg`, and marks dependency-preserving transforms through selected arithmetic, bitwise, shift/rotate, `imul`, and `lea` forms. `xor reg,reg`, `sub reg,reg`, and `and reg,0` erase dependency. Control transfers and exhaustion retain the same fail-closed window boundary as the upstream scan.

## Retail result

Across **2,847,850** decoded instructions and the same **1,786** absolute `.data` loads from **434** slots:

- **179** transform events;
- **160** source loads participate in at least one transform;
- **164** unique transform instruction sites;
- `xor`: 84;
- `lea`: 45;
- `add`: 26;
- `and`: 9;
- `dec`: 4;
- `inc`: 4;
- `sub`: 3;
- `or`: 2;
- `shl`: 1;
- `imul`: 1.

No indirect `call/jmp` consumes any tainted register, including transformed values: **0** matches.

The broader dependency tracking extends more windows than the copy-only pass, ending with 1,430 unrelated control transfers, 336 all-tainted-register clobbers, and 20 window expirations. None reaches an indirect transfer.

## Boundary

Promoted only `p13a_fun005ffc50_absolute_data_transform_near_transfer_subset_complete=true`.

Still open: stack spill/reload, memory aliases, inter-block/phi carry, base/index-addressed writable sources, heap/runtime values, return-value provenance, and unmodelled transformations. Global writable-memory, callback/incoming-indirect, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_transform_near_transfer.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_copy_near_transfer.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_transform_near_transfer.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_transform_near_transfer.py
```

## Next step

Trace stack spill/reload and inter-block writable-memory provenance, then base/indexed/alias sources. Bounded same-block GPR copy plus selected arithmetic/LEA transform paths are now negative.
