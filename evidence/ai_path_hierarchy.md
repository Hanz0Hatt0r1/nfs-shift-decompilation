# SHIFT AIPath base hierarchy evidence

This note records the source and PE evidence for the base hierarchy shared by
the concrete track-path containers.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Registry hierarchy

The recovered class registry gives:

```text
BPersistent
└── AIPathObj
    └── AIPath
        ├── AIPolylinePath
        └── AISegmentPath
```

The relevant descriptors are:

| Class | Descriptor | Parent |
|---|---:|---|
| `AIPathObj` | `0x00c0dc64` | `BPersistent` |
| `AIPath` | `0x00c0d698` | `AIPathObj` |
| `AIPolylinePath` | `0x00c0d608` | `AIPath` |
| `AISegmentPath` | `0x00c0d668` | `AIPath` |

`FUN_00a85300` registers `AIPathObj`; `FUN_00a84730` registers
`AIPath`. The two concrete path registrations point at the `AIPath`
descriptor as their parent.

## AIPathObj vtable

The retail PE vtable at `0x00afc630` has second entry `0x006cc220`.
That six-byte getter is:

```text
b8 64 dc c0 00    mov eax,0x00c0dc64
c3                ret
```

so the table identifies `AIPathObj` directly.

`FUN_006d0ef0` also writes `PTR_FUN_00afc630` before calling the
`BPersistent` destructor path `FUN_006383f0`. This is a source anchor
independent of the PE getter scan.

## AIPath boundary

No dedicated descriptor-returning getter or vtable is present for
`AIPath` descriptor `0x00c0d698`. This matches the source hierarchy:
`AIPath` adds the conceptual/path interface layer but does not introduce a
separate concrete class-identity table through this RTTI mechanism.

This absence must not be filled by guessing a neighboring vtable.

## Concrete destructor chain

The concrete container destructors converge on the same base transition:

- `FUN_006cc390` writes `AIPolylinePath` vtable `0x00afc678`, performs
  its array cleanup, then calls `FUN_006d0ef0`;
- `FUN_006ce660` writes `AISegmentPath` vtable `0x00afc930`, performs
  its node-array cleanup, then calls `FUN_006d0ef0`;
- `FUN_006d0ef0` writes `AIPathObj` vtable `0x00afc630` and continues
  to `BPersistent` teardown.

This source chain independently agrees with the registry inheritance.

## Verifier

`verify_track_path_source_anchors.py` now checks all of the above:

- registry parent links;
- the source-only `AIPathObj` vtable anchor;
- the PE `AIPathObj` getter/vtable;
- the absence of a dedicated `AIPath` getter/vtable;
- both concrete destructor-to-base transitions.

The `AIPathObj` table is PE/source evidence for the hierarchy and is not added
to the analyzer's concrete candidate filters, because the current runtime
scanner does not claim standalone `AIPathObj` objects.
