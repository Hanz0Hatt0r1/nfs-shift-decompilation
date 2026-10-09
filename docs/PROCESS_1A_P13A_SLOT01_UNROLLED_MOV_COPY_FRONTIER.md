# Process 1A / P1.3A — shallow unrolled ordinary-MOV copy frontier

## Scope

After the merged REP, bare-string, receiver-loop and ordinary-MOV-loop closures, slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` still have an acyclic compiler-unrolled copy class: ordinary `MOV` load/store sequences that do not call a named memory helper and do not execute inside a backward-branch loop.

The analyzer follows direct calls from the four recovered wheel/physics roots to depth four. A cluster is retained only when all of the following hold:

- the source is loaded from memory into a register and that carrier is not clobbered before the store;
- the destination is non-stack memory;
- at least two stores share the same destination base expression;
- the stores occur within a narrow straight-line window;
- their destination ranges contain a contiguous span of at least eight bytes;
- instructions covered by backward-branch loops are excluded;
- zero-initialization is excluded and will be inventoried separately.

## Retail result

Authoritative PC retail 1.02 plus the Drive Ghidra index produce exactly **11** shallow candidate functions:

`FUN_0076e560`, `FUN_007b0710`, `FUN_00403d00`, `FUN_004e9380`, `FUN_00633290`, `FUN_006333f0`, `FUN_0075a8d0`, `FUN_007b0580`, `FUN_0064fef0`, `FUN_007b0450`, `_LocaleUpdate`.

The evidence records the shortest direct path, destination-base expression, contiguous coverage and exact store sites for every candidate. This is a navigation frontier only: membership does not establish selected-HDVehicle identity.

## Gate

```text
shallow unrolled MOV copy frontier captured = true
candidate functions                         = 11
candidate semantics complete                = false
zero-init included                          = false
loop-body transfers included                = false
slot0 complete                              = false
slot1 complete                              = false
P1.3 complete                               = false
provider count                              = 7
```

## Next step

Adjudicate these 11 functions by exact receiver/destination provenance. After that, inventory straight-line zero-initialization separately, then widen only concrete selected-HDVehicle-derived deeper or indirect alias carriers.
