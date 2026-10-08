# Process 1 — reject two residual literal `+0x374` writers

The remaining global literal `+0x374` store inventory contained three non-constructor function bodies worth adjudicating after the direct manager-root/vtable surfaces were exhausted. Two are now rejected as writers of `FUN_00489ad0()` singleton `manager+0x374` by exact receiver provenance.

## `FUN_0051efa0`

Its store is:

```text
0x0051effd mov [ESI+0x374],EAX
```

The receiver chain is exact:

```text
0x004567a3 call FUN_00518de0
0x00518de0 mov EAX,0x00be1680
0x00518de5 ret
0x004567a8 mov ECX,EAX
0x004567aa call FUN_0051f8f0
...
0x0051f92b call FUN_0051efa0
```

`FUN_0051f8f0` preserves its receiver in `ESI`, so the `+0x374` store belongs to `0x00be1680`, not manager singleton `0x00bc9fc0`.

No semantic name is assigned to `0x00be1680`.

## `FUN_005dec70`

Its store is:

```text
0x005ded7e mov [ESI+0x374],EBP
```

The only direct constructor path allocates exactly `0x37c` bytes:

```text
0x005df730 push 0x37c
0x005df735 call FUN_005862a0
...
0x005df746 mov ECX,EAX
0x005df748 call FUN_005dec70
```

This cannot be the manager object. The proven manager constructor `FUN_00488dc0` writes `manager+0x37c`, so the manager requires valid storage through at least offset `+0x37f`. A freshly allocated `0x37c`-byte object ends at `+0x37b`.

Again, no class identity is inferred.

## Remaining literal writer

`FUN_00481e20` remains open. It performs a large field-by-field copy and includes:

```text
0x004826a0 fld  dword [EDI+0x374]
0x004826a6 fstp dword [ESI+0x374]
0x004826ac fld  dword [EDI+0x378]
0x004826b2 fstp dword [ESI+0x378]
0x004826b8 fld  dword [EDI+0x37c]
0x004826be fstp dword [ESI+0x37c]
```

Two direct callsites clearly target embedded subobjects, but the `FUN_0070dccf -> FUN_0070db00` path forwards a destination argument into `FUN_00481e20`; that alias must be rooted before this last candidate can be rejected.

## Gates

No semantic gate changes. `manager+0x374 == HDVehicle+0x4330` remains unproven, retail control/input provenance remains incomplete, and provider count remains **7**.
