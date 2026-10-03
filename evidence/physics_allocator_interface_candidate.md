# PhysicsAllocator heuristic interface candidate

`tools/ghidra/build_physics_allocator_interface_candidate.py` joins the exact
`SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1` evidence to the deliberately weaker generic
Ghidra vtable-candidate inventory.

The output format is `SHIFT-PHYSICS-ALLOCATOR-INTERFACE-CANDIDATE/1`.

## Retail observation

The current heuristic vtable scan contains one six-slot `.rdata` candidate at
`0x00b0bb50` with this raw layout:

| slot | target | current Ghidra name | semantic status |
| ---: | --- | --- | --- |
| 0 | `0x0079cd90` | `FUN_0079cd90` | exact boundary member `PhysicsAllocator::malloc` |
| 1 | `0x008cb240` | `FUN_008cb240` | unknown |
| 2 | `0x0079d130` | `FUN_0079d130` | unknown |
| 3 | `0x0079ce30` | `FUN_0079ce30` | exact boundary member `PhysicsAllocator::free` |
| 4 | `0x008f3df0` | `GetHashSize` | unknown; current auto-name is not trusted |
| 5 | `0x0079db20` | `FUN_0079db20` | unknown |

Only slots 0 and 3 inherit semantics, because those targets were independently
proven by exact `MWL::Core::PhysicsAllocator::malloc/free` strings plus their
shared pool/source diagnostics and physical ABI shape.

The other four slots deliberately remain unnamed.

## Why the unknown slots stay unknown

The current Ghidra metadata itself demonstrates type/name contamination risks.
For example slot 4 points at a one-byte function which is currently named
`AptFrameStack::GetHashSize`. That label is not credible evidence that the
PhysicsAllocator interface contains a hash-size method.

Likewise, the neighboring functions have heterogeneous observed conventions and
parameter counts. Those shapes are useful targets for raw instruction analysis,
but not enough to infer source-level method names.

## Promotion rule

The report gets `physics_allocator_interface_candidate=true` only when:

1. the input exact allocator boundary is confirmed;
2. `vtables.json` explicitly identifies itself as `heuristic-candidates`;
3. exactly one heuristic table contains both proven allocator member addresses.

If zero or multiple tables contain both members, the interface candidate remains
unresolved.

This rule intentionally does **not** feed back into the allocator boundary. The
exact-string boundary is independently valid even if the heuristic vtable scan
changes or disappears.

## Run

```bash
python3 tools/ghidra/build_physics_allocator_boundary.py \
  out/shift_ghidra_database \
  --json-out out/physics_allocator_boundary.json

python3 tools/ghidra/build_physics_allocator_interface_candidate.py \
  out/physics_allocator_boundary.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/physics_allocator_interface_candidate.json
```

## Evidence boundary

A positive interface candidate means only that the two independently proven
allocator methods co-occur in exactly one generic six-slot function-pointer-table
candidate. It does not prove:

- the table's class identity;
- that runtime dispatch actually uses this table;
- constructor/vptr assignment;
- source-level method order beyond the two known targets;
- semantics of slots 1, 2, 4 or 5;
- allocator argument roles, return ABI or ownership policy.

The next useful step is targeted instruction analysis of all six slot targets and
independent search for constructor/vptr references, while retaining the generic
vtable layer as heuristic evidence.
