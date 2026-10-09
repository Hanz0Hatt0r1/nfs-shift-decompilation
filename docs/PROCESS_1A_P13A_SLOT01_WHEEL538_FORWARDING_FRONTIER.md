# Process 1A / P1.3A: slot0/slot1 wheel-local `+0x538` forwarding frontier

`FUN_00755950` consumes an f64 from local `wheel_runtime+0x538`, where the proven wheel receiver is `HDVehicle+0x400+slot*0xa80`. For P1.3A slot0/slot1 this normalizes to `HDVehicle+0x938` and `HDVehicle+0x13b8`.

The direct absolute-offset and exact-address layers are already closed. This slice closes the exact local `+0x538` address-materializer/callee subset without claiming full base-plus-delta or bulk-copy exhaustion.

## Whole-image local `+0x538` surface

PC retail 1.02 contains 43 exact scalar uses of `0x538`. The target consumer is `0x00755958 fld qword [edx+0x538]`. The only direct qword store is the already-rejected `0x00761b67 fstp qword [esi+0x538]`, whose proven base is `HDVehicle+0x748+slot*0xa80`, normalizing to `HDVehicle+0xc80/+0x1700/+0x2180/+0x2c00` rather than the consumer slots.

Four positive `LEA ...+0x538` materializers remain:

- `0x006c1b8a lea ebx,[ecx+0x538]`
- `0x008fe259 lea ecx,[esi+0x538]`
- `0x008fe2c4 lea ebx,[esi+0x538]`
- `0x00958c28 lea eax,[ebx+0x538]`

## `0x006c1b8a`: internal cursor only

`FUN_006c1b80` turns `ECX+0x538` into an internal cursor and advances it by `0x34` for 25 records. Before calls that need the containing object, the code reconstructs `ECX=EBX-0x538` (`0x006c1bb5`, `0x006c1bdd`). Other calls use `EBX-0x24`. The materialized `base+0x538` pointer is not forwarded as a destination and the function does not store a qword at `[EBX]`.

## `0x008fe259`: teardown reader, no target write

`FUN_008fe230` materializes `ESI+0x538` and calls `FUN_008fe130`. The callee walks ownership fields at local offsets `+0x7c/+0x84/+0x88`, `+0x68/+0x70/+0x74`, `+0x54/+0x5c/+0x60`, `+0x40/+0x48/+0x4c`, `+0x2c/+0x34/+0x38`, `+0x18/+0x20/+0x24`, and `+0x4/+0xc/+0x10`; it issues release callbacks for pointees but contains no store to the receiver block. It cannot produce the f64 at local `+0x538`.

## `0x008fe2c4`: real subobject initialization, wrong receiver domain

`FUN_008fe2a0` materializes `ESI+0x538`, passes it to `FUN_00a39210`, and later to `FUN_00a33000`. Those callees do write the beginning of the subobject, so receiver provenance is required.

The retail call surface is exact: `FUN_008fe2a0` has one direct caller, `0x008f8a66`. Immediately before it:

- `FUN_00894b60` returns the fixed global manager `0x00c2af60`;
- `0x008f8a45` derives allocator state `0x00c2af60+0x28c = 0x00c2b1ec`;
- `FUN_0062f6f0` allocates/returns a payload from that pool;
- `0x008f8a58` saves that returned payload in `EBX`;
- `0x008f8a64` sets `ECX=EBX` and calls `FUN_008fe2a0`.

The constructor also installs exact vptr `0x00b35e6c`. Therefore this writer targets a separately allocated pool object, not a receiver derived from `HDVehicle+0x400+slot*0xa80`.

## `0x00958c28`: FMOD IT Codec load buffer, wrong receiver domain

Inside `FUN_0095883f`, `EBX` is the callback receiver. `0x00958c28` passes `EBX+0x538` to `FUN_0093a188` with element size 1 and count `0x40`; the helper has a copy path whose destination is the supplied user buffer, so this is a real 64-byte load/write candidate.

Its receiver domain is independently fixed by the retail plugin descriptor. Initializer code stores:

- descriptor name pointer `0x00b47990` into `0x00b9bd40`; the pointed string is `FMOD IT Codec`;
- callback thunk `0x0095abdf` into descriptor field `0x00b9bd50`;
- object/state size `0x3e80` into descriptor field `0x00b9bd84`.

The thunk at `0x0095abdf` loads its first callback argument, recovers `ECX = arg1-0x1c`, and calls `FUN_0095883f`. Thus the `+0x538` destination belongs to FMOD IT Codec callback state, not to the selected HDVehicle wheel runtime.

## Adjudication

All four exact positive local `+0x538` address-materializer paths are now classified negative for P1.3A slot0/slot1. This closes only the wheel-local exact-displacement forwarding subset.

Still open are aliases that reach the same bytes without embedding literal `0x538`, plus overlapping bulk-copy/memory-initialization ranges. Slot0, slot1, aggregate P1.3, and provider removal remain fail-closed; provider count remains 7.