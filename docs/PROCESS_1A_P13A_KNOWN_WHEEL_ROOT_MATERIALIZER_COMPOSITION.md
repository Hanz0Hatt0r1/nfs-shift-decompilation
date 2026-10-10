# Process 1A / P1.3A — known wheel-root materializer composition

## Scope

This handoff composes the merged P1.3A wheel-root construction/lifetime work into one bounded frontier. It does not add a new machine claim; each machine conclusion remains owned by its upstream retail-PC-1.02 contract.

The composition consumes seven contracts:

- the slot0/slot1 known wheel-root materialization/persistence handoff;
- `FUN_00757d2c` runtime-indexed exact-root lifetime;
- fixed four-wheel handoffs through `FUN_007582f0` and `FUN_0076ed60`;
- the trampolined `FUN_007653f9 -> FUN_00760d70/FUN_00760d93` family;
- the `FUN_00760d93` child/interior alias closure;
- the indexed `FUN_007572f0/FUN_00757318` exact-root lifetime;
- the five `FUN_00757318` interior-alias consumers.

## Result

The bounded surface now contains six normalized exact-root materializer families. Collectively they cover all four canonical wheel roots:

```text
slot 0  HDVehicle+0x400
slot 1  HDVehicle+0xe80
slot 2  HDVehicle+0x1900
slot 3  HDVehicle+0x2380
stride  0xa80
```

Within those already-proven families there are **zero persistent exact-wheel-root escapes**. Positive transient handoffs are retained rather than hidden: the two fixed families contribute 4+4 leaf handoffs, the trampolined family contributes 6 handoffs, and the indexed `FUN_007572f0` family has one exact-root forward into its complete leaf.

Two derived-alias groups are also composed. `FUN_00760d93` contributes four child/interior aliases and `FUN_00757318` contributes five interior aliases. Across these nine positive aliases the merged consumer proofs find zero pointer persistence and zero reconstruction back to the wheel root.

## Gate effect

Promoted only:

- `p13a_known_wheel_root_materializer_surface_composed = true`;
- `p13a_known_materializer_all_four_wheel_slots_covered = true`.

The composition records zero persistent escape/reconstruction inside this bounded surface, but **does not** promote the global reconstructed-pointer gate. Unknown materializer families may still exist outside the enumerated surface, and runtime-generated/copied stores remain a separate blocker.

Therefore these remain fail-closed:

- `reconstructed_wheel_pointers_ruled_out`;
- `runtime_generated_selected_wheel_pointer_stores_ruled_out`;
- callback/incoming-indirect entry;
- global stored/escaped aliases;
- slot0, slot1, and aggregate P1.3.

Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/build_p1a_known_wheel_root_materializer_composition.py \
  --output evidence/p1a_p13a_known_wheel_root_materializer_composition.json
pytest -q tests/test_process1a_p13a_known_wheel_root_materializer_composition.py
```

## Next step

Enumerate residual exact-wheel-root construction/store sites outside this composed surface. Any positive site must be joined to its later consumers before changing the global runtime-generated/reconstructed pointer gates. Runtime callback and incoming-indirect entry remain independent work.
