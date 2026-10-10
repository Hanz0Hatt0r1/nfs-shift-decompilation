# Process 1A / P1.3A — `FUN_0067b660` static-vtable object identity

## Scope

The direct `FUN_00a62f60` registration frontier leaves one source unresolved: `0x0067b69e` inside `FUN_0067b660`. The upstream frontier proves the function is reached only through static data, but does not identify the object class behind that callback.

This pass closes the class/layout identity without guessing the callback's explicit argument.

## Vtable identity

`FUN_0067b7b0` installs vptr `0x00af7544` into its receiver. The retail table is exactly:

```text
+0x0  0x0067b8c0  destructor-like method
+0x4  0x0067b660  unresolved queue-registration callback
+0x8  0x0067b330  state method
```

Thus `FUN_0067b660` is exactly slot `+0x4` of this concrete class, not merely a nearby `.rdata` pointer.

## Constructed layout

The constructor creates seven embedded source records:

```text
first source = this + 0x130
stride       = 0x30
count        = 7
source vptr  = 0x00af74f4
```

The source-record table is exactly `0x0067b300, 0x0067b730`. The same constructor initializes the queue manager at `this+0x2b0`, matching the offsets used by `FUN_0067b660` when it registers `param_1+0x130+index*0x30` into `param_1+0x2b0`.

The constructor has exactly three direct machine entry sites, embedding this class at:

- parent `+0x8a0` (`0x00489171`);
- parent `+0x2c0` (`0x0067b180`);
- parent `+0x320` (`0x00d4b54e`).

The destructor path restores the same vptr and tears down the queue plus seven source records.

## Remaining ABI gap

The layout coincidence is strong but insufficient to identify the callback argument. Ghidra and machine code agree that `FUN_0067b660` reads its working object from explicit stack parameter `[EBP+0x8]`; it does not consume ECX as the queue/source base.

Therefore this contract deliberately does **not** assume:

```text
param_1 == virtual-dispatch receiver (`this`)
```

The indirect slot `+0x4` dispatcher must be recovered and its pushed argument traced before the `0x0067b69e` registration can be classified as non-wheel or selected-wheel-derived.

## Gate effect

Promoted only:

- `p13a_fun0067b660_static_vtable_object_identity_complete = true`;
- exact slot `+0x4` identity;
- constructor/source-record layout completeness.

Still false:

- callback argument provenance;
- callback argument selected-wheel rejection;
- callback/incoming-indirect global closure;
- runtime-generated selected-wheel pointer-store closure;
- stored aliases, slot0, slot1, aggregate P1.3.

Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun0067b660_static_vtable_object.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_queue_registration_frontier.json \
  --output evidence/p1a_p13a_fun0067b660_static_vtable_object.json
pytest -q tests/test_process1a_p13a_fun0067b660_static_vtable_object.py
```

## Next step

Recover an indirect dispatch to vtable `0x00af7544` slot `+0x4` and prove the identity of its explicit stack argument. That is the remaining direct `FUN_00a62f60` source-classification blocker.
