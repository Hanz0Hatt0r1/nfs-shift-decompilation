# Process 1B — resolve escaped `Participants Manager` virtual clear writers

## Scope

The previous frontier proved that `manager+0x20` is the embedded `"Participants Manager"` object and that it escapes into registry/container state rooted at `FUN_0065bf80()+0x24/+0x44`. This pass resolves the embedded object's concrete vtable and follows the live `+0x44` dispatch paths far enough to classify writes to the target relative offset `+0x354 == manager+0x374`.

## Exact vtable bytes

`FUN_004891b0` installs `PTR_LAB_00ab916c` at `manager+0x20`. The Ghidra static-table export records nine consecutive `.rdata` pointers beginning at `0x00ab916c`:

```text
slot 0  0x00ab916c -> 0x00489190
slot 1  0x00ab9170 -> FUN_00485a20
slot 2  0x00ab9174 -> FUN_004871f0
slot 3  0x00ab9178 -> FUN_0048a7f0
slot 4  0x00ab917c -> FUN_00488a10
slot 5  0x00ab9180 -> FUN_00488970
slot 6  0x00ab9184 -> FUN_0048ade0
slot 7  0x00ab9188 -> FUN_0048aee0
slot 8  0x00ab918c -> 0x0048b9a0
```

The pointer values are recovered from the raw little-endian `.rdata` bytes, not inferred from function proximity.

## Escaped-alias dispatch reaches exact clears

The `FUN_0065bf80()+0x44` registry iterates the same escaped `manager+0x20` object. Two dispatch families reach virtual entries that write the target field:

```text
FUN_0065b990
  -> FUN_00648640
  -> vslot +0x8
  -> FUN_004871f0
  -> [subobject+0x354] = 0
  == [manager+0x374] = 0
```

and:

```text
FUN_0065ba90 / FUN_0065bbc0
  -> FUN_00647c60
  -> vslot +0x14
  -> FUN_00488970
  -> [subobject+0x354] = 0
  == [manager+0x374] = 0
```

`FUN_00485a20` also writes `subobject+0x354 = 0` on its initialization-style entry. The resolved targets `FUN_0048a7f0`, `FUN_00488a10`, `FUN_0048ade0`, and `FUN_0048aee0` contain no decompiler reference to `+0x354/+0x358`.

This proves that the escaped Participants Manager lifecycle can clear `manager+0x374`; it does **not** prove publication of a selected HDVehicle pointer.

## Stronger helper candidate discovered

A separate helper-mediated path is now the highest-value frontier:

```text
FUN_00465860 @ 0x00465bae \
                              -> thunk_FUN_00d60660 @ 0x00487240 -> FUN_00d60660
FUN_00468ed0 @ 0x004690b5 /
```

Both callers obtain the receiver from `FUN_00489ad0()`, i.e. the exact manager root. Ghidra decompiler output for `FUN_00d60660` contains an assignment to `this+0x374` after selection through `this+0x2a0`, making it a direct candidate for the missing selected-pointer producer.

However, the decompiled conditional surrounding that assignment is internally suspicious: the same decompilation appears to require an entry discriminator value and then tests a contradictory value before the store. This contract deliberately does not promote the assignment. Exact instruction/value-flow proof is required first.

## Result

Promoted:

- concrete `Participants Manager` vtable pointer table;
- escaped alias reaches exact `manager+0x374 = 0` clear writers;
- helper-mediated exact-manager-root candidate `thunk_FUN_00d60660` is bounded to two direct callers.

Still open:

- nonzero `manager+0x374` publication;
- `manager+0x374 == HDVehicle+0x4330`;
- selected non-sentinel `HDVehicle+0x64e8` provenance;
- retail input/control provenance.

Provider count remains 7.

## Next step

Recover exact instructions/value flow around `FUN_00d60660`'s apparent `manager+0x374` assignment and determine whether it is reachable and whether the stored pointer is the selected `manager+0x2a0` entry. Do not promote the decompiler's contradictory branch literally without machine evidence.
