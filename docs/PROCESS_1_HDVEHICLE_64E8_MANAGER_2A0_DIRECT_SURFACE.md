# Process 1 — manager+0x2a0 direct registration surface

## Result

The already-proven direct singleton-manager method surface and the manager vtable surface do not contain a direct registration path for `manager+0x2a0`.

Across the bounded surfaces inherited from `SHIFT.HDVehicle64e8ManagerDirectSetterFrontier/1`:

- 44 direct manager-root calls collapse to 12 unique target functions;
- manager vtable `0x00ab9190` contains 18 slots / 17 unique code targets;
- only `FUN_00488a60` contains a literal `+0x2a0` reference;
- no manager-vtable target contains a literal `+0x2a0` reference.

`FUN_00488a60` does not register or replace collection entries. It forms `manager+0x2a0` and iterates it using a stack-local iterator descriptor.

## Exact machine path

```text
0x00488a6a lea esi,[ecx+0x2a0]
0x00488a72 lea edx,[ebp-0x0c]
0x00488a75 mov ecx,esi
0x00488a80 call FUN_0052cce0
...
0x00488ab5 lea edx,[ebp-0x0c]
0x00488ab8 mov ecx,esi
0x00488aba call FUN_0052cce0
```

The helper entry is:

```text
0x0052cce0 push edx
0x0052cce1 xor  edx,edx
0x0052cce3 call FUN_0052ca50
```

`FUN_0052ca50` advances/initializes the descriptor supplied through the stack argument. Its manager-collection receiver accesses are reads such as receiver `+0x18`, `+0x30`, and `+0x00`; the writes target the iterator descriptor, not the collection receiver.

Therefore this bounded direct-manager path is an iteration/consumption path, not the missing registration producer.

## Consequence for P1.3

Repeating scans of ordinary direct manager methods or vtable methods is no longer productive for `manager+0x2a0` registration. The remaining plausible classes are:

- escaped/pre-adjusted aliases of `manager+0x2a0`;
- helper-mediated mutation after the subobject pointer is passed away;
- callbacks or non-vtable function pointers;
- computed-offset paths;
- bulk-copy/registration helpers.

No entry identity is promoted. In particular, this does not prove that any manager collection element equals `HDVehicle+0x4330`.

## Gates

Unchanged:

- `manager+0x2a0` entry -> `HDVehicle+0x4330`: unproven;
- `manager+0x374` -> `HDVehicle+0x4330`: unproven;
- selected non-sentinel `HDVehicle+0x64e8` writer: unproven;
- retail input/control provenance: incomplete;
- P1.3: incomplete;
- external provider count: **7**.

## Next step

Trace pre-adjusted/escaped `manager+0x2a0` aliases and the helpers that receive them. Do not repeat the direct manager-root or `0x00ab9190` vtable literal-offset scans unless new evidence expands those bounded surfaces.
