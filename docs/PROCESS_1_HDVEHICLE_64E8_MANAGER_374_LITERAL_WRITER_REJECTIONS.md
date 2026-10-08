# Process 1 — reject residual literal `+0x374` writer domains

The residual global literal `+0x374` store inventory contained three non-constructor function bodies after the direct manager-root/vtable surfaces were exhausted. Two are rejected outright as writers of `FUN_00489ad0()` singleton `manager+0x374`, and one major forwarded alias of the third is now rejected.

## `FUN_0051efa0`

```text
0x0051effd mov [ESI+0x374],EAX
```

Exact receiver chain:

```text
0x004567a3 call FUN_00518de0
0x00518de0 mov EAX,0x00be1680
0x00518de5 ret
0x004567a8 mov ECX,EAX
0x004567aa call FUN_0051f8f0
...
0x0051f92b call FUN_0051efa0
```

The writer receiver is `0x00be1680`, not manager singleton `0x00bc9fc0`. No semantic name is assigned to that object.

## `FUN_005dec70`

```text
0x005ded7e mov [ESI+0x374],EBP
```

Its direct constructor path allocates exactly `0x37c` bytes:

```text
0x005df730 push 0x37c
0x005df735 call FUN_005862a0
...
0x005df746 mov ECX,EAX
0x005df748 call FUN_005dec70
```

This is not the manager object: the proven manager constructor writes `manager+0x37c`, requiring valid storage through at least `+0x37f`, while a `0x37c`-byte object ends at `+0x37b`.

## `FUN_00481e20` bulk-copy path

The copy includes:

```text
0x004826a0 fld  dword [EDI+0x374]
0x004826a6 fstp dword [ESI+0x374]
0x004826ac fld  dword [EDI+0x378]
0x004826b2 fstp dword [ESI+0x378]
0x004826b8 fld  dword [EDI+0x37c]
0x004826be fstp dword [ESI+0x37c]
```

The previously open forwarded path is now bounded:

```text
FUN_0070dcc0
 -> trampoline 0x0047af96
 -> FUN_0070dccf
 -> FUN_0070db00
 -> FUN_00481e20
```

The Ghidra direct-call surface of `FUN_0070dcc0` has 21 callsites. Every one forms incoming `ECX` with `LEA [EBP-negative]`, i.e. stack-local storage. `FUN_0070dcc0` preserves that receiver through the trampoline split; `FUN_0070dccf` forwards it to `FUN_0070db00`, which reloads it into `ECX` before calling `FUN_00481e20`. Therefore this direct-call surface cannot target fixed manager singleton `0x00bc9fc0`.

`FUN_00481e20` still has two direct embedded-subobject destinations that remain open:

```text
0x004848f5  ECX = parent + 0xa00
0x0081d335  ECX = parent + 0x2d0
```

Their parent provenance must be closed before the entire bulk-copy literal-writer surface can be rejected.

## Gates

No semantic gate changes. `manager+0x374 == HDVehicle+0x4330` remains unproven, retail control/input provenance remains incomplete, and provider count remains **7**.
