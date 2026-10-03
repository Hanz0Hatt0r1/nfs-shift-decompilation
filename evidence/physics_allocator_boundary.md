# MWL PhysicsAllocator static boundary

`tools/ghidra/build_physics_allocator_boundary.py` captures the retail static
boundary around the PhysX allocator adapter without promoting unproven argument
or ownership semantics.

The output format is `SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1`.

## Paired functions

The structured Ghidra export contains two adjacent non-thunk functions:

| function | exact method string | physical entry shape |
| --- | --- | --- |
| `FUN_0079cd90` | `MWL::Core::PhysicsAllocator::malloc` | `__thiscall`, `ECX:4 (auto)`, `Stack[0x4]:4` |
| `FUN_0079ce30` | `MWL::Core::PhysicsAllocator::free` | `__thiscall`, `ECX:4 (auto)`, `Stack[0x4]:4` |

Both functions also reference the same three strings:

- `pPool`;
- `.\Source\System\PhysXSupport.cpp`;
- `No BMemPool available`.

The method-specific names resolve only to their respective functions. The shared
pool/source strings resolve to both functions.

This establishes a strong paired API boundary around `PhysicsAllocator` while
leaving the detailed implementation semantics open.

## Direct-call neighborhoods

The tool records the complete direct-call neighborhood seen in the same Ghidra
export. These edges are preserved for later analysis but their targets are not
assigned semantics by this boundary layer.

Observed retail calls include:

```text
FUN_0079cd90
  -> FUN_0063ba50
  -> FUN_00710860
  -> FUN_0062e1a0
  -> FUN_0062de20
  -> FUN_0062de50
  -> FUN_00638300

FUN_0079ce30
  -> FUN_0063bce0
  -> FUN_0063bc60
  -> FUN_0063bb60
  -> FUN_00710860
  -> FUN_0062e1a0
  -> FUN_0062de20
  -> FUN_0062de50
  -> FUN_0062efb0
  -> FUN_0064f250
```

The shared calls strengthen that the pair belongs to the same support layer, but
this report deliberately does not guess which callee acquires a pool, reports an
assertion or performs the final allocation/free operation.

## Promotion rule

A member is confirmed only when all of these direct observations agree:

1. the exact function exists;
2. its method-name string occurs exactly once and resolves only to that function;
3. its calling convention is `__thiscall`;
4. physical parameter storage is exactly `ECX:4 (auto)` plus
   `Stack[0x4]:4`;
5. all three shared pool/source strings occur in that function.

The paired boundary is confirmed only when both members pass and their physical
entry shapes agree.

Ghidra semantic parameter types are retained in the JSON for audit but never
participate in promotion.

## Run

```bash
python3 tools/ghidra/build_physics_allocator_boundary.py \
  out/shift_ghidra_database \
  --json-out out/physics_allocator_boundary.json
```

## Evidence boundary

A confirmed report proves the existence of a paired retail
`MWL::Core::PhysicsAllocator::malloc/free` interface boundary and its physical
entry-storage shape. It does **not** yet prove:

- that the explicit `Stack[0x4]` value is byte count for `malloc`;
- that the explicit `Stack[0x4]` value is the pointer being freed for `free`;
- return-value ABI or allocation-result semantics;
- the meaning of the `this` object or its layout;
- which direct callee performs the underlying allocation/free;
- pool ownership, reference counting, failure policy or thread-safety behavior.

Those require raw instruction forwarding, source/call-site evidence, object
layout evidence or runtime observations. The contract is intentionally useful
before those questions are resolved: it provides stable function identities and
an exact ABI boundary without inventing the missing roles.
