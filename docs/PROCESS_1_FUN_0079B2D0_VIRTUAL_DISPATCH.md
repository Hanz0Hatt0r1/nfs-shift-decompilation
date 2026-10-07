# Process 1 — exact `FUN_0079b2d0` virtual-dispatch closure

The previous Process 1 indirect-dispatch frontier deliberately left the second
caller of `FUN_00770e80` unresolved:

```text
UNKNOWN/INDIRECT OWNER -?-> FUN_0079b2d0 -> FUN_00770e80
```

That uncertainty is now closed for the pinned PC retail 1.02 executable. The
proof below uses the exact PC `SHIFT.exe` and the matching full Ghidra decompile
`SHIFT.exe.c`. Xbox 360 recompilation output is not required for this promotion.

## Pinned PC inputs

```text
SHIFT.exe MD5    705af8b420e5eb1e3834ac43d5533c6b
SHIFT.exe SHA256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
SHIFT.exe.c SHA256
                 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

No runtime capture is used.

## 1. Exact subobject continuity

`FUN_007125e0` allocates the parent vehicle object and constructs it through
`FUN_0072ed20`. The parent constructor builds the relevant polymorphic subobject
at byte offset `+0x340`:

```text
0x0072ed48  lea  ecx,[esi+0x340]
...
0x0072ed57  call FUN_0079c1c0
```

The exact span `0x0072ed48..0x0072ed5c` hashes to:

```text
51b27814cec2a52aaf58891cf2c6772a7568effa38759f72a9ff97bde507951b
```

The matching parent destructor calls `FUN_0079b1d0(parent+0x340)`, preserving the
same subobject identity through construction and destruction.

## 2. Exact final vtable

The final constructor and destructor both assign vtable `0x00b0b744`:

```text
0x0079c203  mov dword ptr [esi],0x00b0b744
0x0079b1f2  mov dword ptr [esi],0x00b0b744
```

Both six-byte stores hash to:

```text
ccd62dfc71559499eb70f4d838ccaf6220bf02bf47cc353b8e2c0371e4370f12
```

The first two vtable cells are exactly:

```text
0x00b0b744  0x0079bee0
0x00b0b748  0x0079b2d0
```

The eight-byte table span hashes to:

```text
ce9191514ac44fe254f65909f3918f3d6b7b5a474dfeeb54bc51036b9f16a00e
```

`0x0079b2d0` appears exactly once as a little-endian static pointer in the whole
pinned executable, at `0x00b0b748`, which is exactly vtable offset `+0x4`.

The base/intermediate vtables (`0x00b66cfc` and `0x00b0b7b8`) contain runtime
stub `0x00900e65` in the same `+0x4` slot. The final vtable replaces that slot
with `FUN_0079b2d0`, so the function is the concrete virtual implementation of
that interface slot. This is stronger than the former heuristic-vtable evidence.

Slot zero is independently consistent with lifecycle semantics: `FUN_0079bee0`
calls `FUN_0079b1d0` and conditionally frees `this`.

## 3. Queue registration from `FUN_00713050`

The previously verified direct outer-update path already showed that
`FUN_00713050` works on the same `parent+0x340` subobject. On its final update
branch it also registers that exact subobject into the task queue:

```text
selected record:
0x00713117  mov edx,[ebx]
0x00713119  add edx,0x340
0x0071311f  lea ecx,[esi+0x20]
0x00713122  call FUN_00a62f60

vehicle loop:
0x007131ba  mov edx,[esi+0x140]
...
0x007131c3  add edx,0x340
0x007131c9  lea ecx,[esi+0x20]
0x007131cc  call FUN_00a62f60
```

The two exact spans are hash-locked in
`SHIFT.Process1Fun0079b2d0VirtualDispatch/1`.

After registration the same function executes the queue:

```text
0x007131e5  lea ecx,[esi+0x20]
0x007131e8  mov edx,1
0x007131ed  call FUN_00a62940
```

This proves queue ownership of the same subobject pointer at this callsite; it
does not assign a semantic class name to the parent or queue.

## 4. Queue record preserves the object pointer

`FUN_00a62f60` accepts the subobject as `param_2`, allocates a queue record,
clears it, and stores the object pointer in the first cell:

```text
FUN_00a62f60(..., param_2)
...
*_Dst = param_2;
```

PC machine span `0x00a62f9d..0x00a62fc2` hashes to:

```text
ee304e2e353101249bf91f9f756461a47332f56e9e8f0312af1bf05a65751b66
```

`FUN_00a62940` later walks those queue records. It copies the stored object
pointer and task parameters into a fiber record and creates a fiber whose entry
is `lpStartAddress_00a62710`. The exact machine span
`0x00a62a03..0x00a62a49` hashes to:

```text
d6f3db2b085fd4660c68f8f4b79c908bcb8029f293747dbbe532ebd542b3e474
```

## 5. Fiber dispatcher calls vtable slot `+0x4`

`lpStartAddress_00a62710` is the missing generic indirect dispatcher. Its exact
machine sequence is:

```text
0x00a62718  mov ecx,[edi+0xc]
0x00a6271b  mov esi,[edi]       ; queued object
0x00a6271d  mov edx,[edi+0x8]
0x00a62720  mov eax,[esi]       ; vptr
0x00a62722  mov eax,[eax+0x4]   ; virtual slot +4
0x00a62725  push ecx
0x00a62726  push edx
0x00a6272a  mov ecx,esi         ; this = queued object
0x00a6272c  call eax
```

Span `0x00a62718..0x00a6272e` hashes to:

```text
1b663770eda4394194ef84e8f42de8ee9a52d548e83042be17e2bc5d293090c0
```

Because the queued object is the exact `parent+0x340` subobject whose final
vtable is `0x00b0b744`, slot `+0x4` resolves to `FUN_0079b2d0`.

## Promoted Process 1 path

The old unknown branch is therefore replaced by the exact PC-static path:

```text
FUN_00713050
  -> FUN_00a62f60             queue parent+0x340
  -> FUN_00a62940             materialize fiber task
  -> lpStartAddress_00a62710  call [vptr+0x4]
  -> FUN_0079b2d0
  -> FUN_00770e80
```

The former statement “`FUN_0079b2d0` has no direct incoming call, therefore its
owner is unresolved” is no longer the current Process 1 conclusion. It still has
no normal direct `CALL` edge because the actual edge is virtual/fiber dispatch.

## What is not promoted

This proof intentionally does **not** claim:

- a recovered retail class name for the parent or subobject;
- that the task queue itself is the top-level scheduler;
- rendered-frame cadence;
- one update per rendered frame;
- controller/input ownership;
- equivalence between fiber execution and a render tick.

Those remain separate evidence questions.

## Next Process 1 blocker

With the alternate `FUN_0079b2d0` branch closed, Process 1 can now move upward
from the already verified chain around `FUN_007155e9 -> FUN_00715380 ->
FUN_00713050` and prove the exact lifecycle/scheduling owner that invokes this
queue work. Any cadence promotion must remain independent from rendered-frame
cadence until a static or runtime join proves that relationship.
