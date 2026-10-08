# Process 1 — manager+0x378 selected collection element

## Result

`FUN_0045da80` is now rooted exactly to the `FUN_00489ad0()` singleton manager. The retail machine code proves that this function selects an element from the manager's `+0x2a0` collection and caches the returned element address in `manager+0x378`.

This narrows P1.3, but it does **not** yet prove that the selected collection element is `HDVehicle+0x4330`, nor that `manager+0x374` is that pointer.

## Exact retail path

`FUN_0045da80` (`0x0045da80..0x0045dab8`) begins with:

```text
0x0045da84 call FUN_00489ad0
0x0045da89 mov  edx,[ebp+0x0c]
0x0045da8c mov  esi,eax
0x0045da8e cmp  edx,[esi+0x2c4]
0x0045da94 jb   0x0045daa3
```

Because `ESI` is assigned directly from the singleton getter return, all following `ESI+offset` accesses in this function are exact manager-root accesses.

The out-of-primary-range path clears the cache:

```text
0x0045da96 xor eax,eax
0x0045da98 mov [esi+0x378],eax
```

The in-range path is:

```text
0x0045daa3 lea  ecx,[esi+0x2a0]
0x0045daa9 call FUN_0054ed00
0x0045daae mov  [esi+0x378],eax
```

Thus `manager+0x378` receives the return of `FUN_0054ed00(manager+0x2a0, index)`.

## Collection accessor

The exact body of `FUN_0054ed00` is:

```text
0x0054ed00 cmp  edx,[ecx+0x28]
0x0054ed03 jb   0x0054ed0a
0x0054ed05 jmp  FUN_0054da60
0x0054ed0a mov  eax,[ecx]
0x0054ed0c imul eax,edx
0x0054ed0f add  eax,[ecx+0x30]
0x0054ed12 ret
```

On the normal path the return value is therefore:

```text
collection.base + index * collection.stride
```

For a collection rooted at `manager+0x2a0`, the normalized container fields are:

- stride: `manager+0x2a0`
- count: `manager+0x2c8`
- base: `manager+0x2d0`

The outer function separately compares the index against `manager+0x2c4`. That is a different field from the accessor's own count at `manager+0x2c8`; no equivalence between those counts is claimed.

## Relation between manager+0x374 and manager+0x378

Several exact singleton-root consumers read `+0x378` and compare its value with `+0x374`. Two representative sites are enough to establish that the fields are distinct and are compared as pointer-like values:

```text
FUN_004326e0:
0x004326f9 call FUN_00489ad0
0x004326fe mov  esi,[eax+0x378]
0x00432704 call FUN_00489ad0
0x00432709 cmp  esi,[eax+0x374]
```

```text
FUN_00434eb0:
0x00435134 call FUN_00489ad0
0x00435139 mov  edi,[eax+0x378]
0x0043513f call FUN_00489ad0
0x00435144 cmp  edi,[eax+0x374]
```

This proves only that the two manager slots may hold values whose identity matters to consumers. It does not prove that they are always equal, nor that either equals `HDVehicle+0x4330`.

## Ghidra-index corroboration

The whole-export index records `FUN_0045da80` at `0x0045da80`, size 57 bytes. The heuristic vtable candidate `0x00ab563c` contains it in slot 0, followed by `FUN_00459070`, `FUN_0066d450`, and `FUN_004692e0`. The candidate has no recorded function xrefs, so this remains navigation evidence rather than a class-identity proof.

## Adjudication

Proven:

- `FUN_0045da80` operates on the exact `FUN_00489ad0()` singleton manager.
- It calls `FUN_0054ed00` on `manager+0x2a0` using its second argument as the index candidate.
- On the normal accessor path, the selected element address is cached in `manager+0x378`.
- The primary out-of-range path clears `manager+0x378`.
- `manager+0x374` and `manager+0x378` are separate fields whose values are directly compared by retail consumers.

Still not proven:

- selected `manager+0x2a0` element == `HDVehicle+0x4330`;
- `manager+0x374` == `HDVehicle+0x4330`;
- any non-sentinel selected `HDVehicle+0x64e8` producer;
- retail input/control semantics;
- P1.3 completion.

External provider count remains **7**.

## Next step

Trace the exact producer/mutator of `manager+0x374` and the dispatch/caller path that supplies `FUN_0045da80`'s second argument. Only promote an identity join to `HDVehicle+0x4330` after exact pointer provenance is demonstrated.
