# Process 1B — render-manager `outer+0x780` runtime-item alias closure

## Scope

The cross-block exact-root replay exposed exactly two `outer+0x780` derived paths, both feeding `FUN_0070e1c0`. This slice follows those paths through the runtime-item machinery and asks one narrow question: can the persisted/recovered derived pointer ever reconstruct the exact outer root?

## Entry paths

The two root-derived materializations are:

- `FUN_00498b80`: `0x00498b93 lea ecx,[edi+0x780]` -> `0x00498b9b call FUN_0070e1c0`;
- `FUN_00499240`: `0x004995bf lea ecx,[ebx+0x780]` -> `0x004995c5 call FUN_0070e1c0`.

`FUN_0045ef50` independently constructs that exact subobject by calling `FUN_00633080` with `ECX=outer+0x780` at `0x0045f0f8`. `FUN_00633080` installs vptr `0x00aebdbc` and initializes fields through roughly `+0x25c`.

## Runtime-item encapsulation

`FUN_0070e1c0` briefly pushes incoming ECX at entry, then overwrites the local slot with zero before forwarding the same receiver to `thunk_FUN_00d66440`.

`FUN_00d66440 -> FUN_00633290` allocates a runtime item. `FUN_00633290` stores incoming ECX in the allocation header at `header+0x4`, then returns `header+0x10`; therefore the persisted `outer+0x780` pointer lives at `item-0x0c`.

`FUN_00632fe0` is the corresponding recovery helper. When the item flags permit, it returns `[item-0x0c]`, so it recovers the same derived `outer+0x780` pointer, not the outer root.

## Consumers

`FUN_00498b80` passes the item through `FUN_0070b880` before final recovery. `FUN_0070b880` does not read the item header pointer and never reconstructs the derived receiver. Both root-derived callers eventually use `thunk_FUN_00632fe0` and pass the recovered pointer to `FUN_004987c0`.

`FUN_004987c0` treats the pointer as the standalone `0x260`-class subobject. It never subtracts `0x780`, never stores/returns the exact outer root, and its only virtual receiver call is vslot `+0x08`. With vptr `0x00aebdbc`, that slot resolves to `0x008f3df0`, whose body is a single `ret`.

Its same-receiver helper `FUN_006333f0` also never performs `this-0x780`. The only same-receiver descendant, `FUN_0064fef0`, accesses fields `+0x88/+0x90` and likewise does not reconstruct outer root. Recursive calls back through `thunk_FUN_00d66440` preserve the same derived pointer identity and can create another item, but never transform it back into the outer object.

## Adjudication

The two root-derived `outer+0x780` paths are closed-negative as exact outer-root reconstruction sources. Together with the `outer+0x4` closure, all three derived-subobject transitions from the independent exact-root CFG replay are now bounded.

Callee-created/external exact-root aliases and two-unknown-origin/cross-control-flow `HDVehicle+0x4330` aliases remain open. `manager+0x374 -> HDVehicle+0x4330`, literal `0x004b86cf`, P1.3 completion and provider-count reduction remain fail-closed. Provider count remains 7.
