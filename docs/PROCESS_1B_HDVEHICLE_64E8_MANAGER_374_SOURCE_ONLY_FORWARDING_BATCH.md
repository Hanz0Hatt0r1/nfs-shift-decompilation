# Process 1B: source-only computed `+0x374` forwarding batch

After the returned-pointer closure, 17 computed-address paths remained because their materialized pointer was forwarded to another routine. Eleven of those can be closed without identifying the base object: exact callee ABI proves the computed pointer is read-only source data.

The batch contains four families:

- `0x0052aac0`: the pointer is `FUN_0051b370` arg2 and ultimately `FUN_00531fc0` only reads the pointed dword before OR-ing it into a separate ECX destination.
- `0x0075070b` and `0x0075096d`: the pointer is EDX/param2 to `FUN_00632c10`; EDX is captured as source while ECX is the separate destination object.
- Six `0x0060d580` callsites (`0x005f4e86`, `0x005f548e`, `0x005f5d0a`, `0x005f5ebb`, `0x005f61c8`, `0x005f6593`): the computed pointer is stdcall arg2. The body reads arg2 as formatting/source input and writes only local buffers or arg1-owned service state. The extra `0x008f3df0` call on the `0x005f6593` path is a one-byte `ret`.
- `0x005f569b` and `0x005f5a3e`: the pointer is stdcall arg3 to `FUN_0060d9c0`; the body copies from arg3 into arg1-owned `+0x1b0` state and never writes through arg3.

Thus the forwarding frontier reduces from 17 to six paths. Those six are destination/receiver forwards and require exact ownership/provenance rather than source-direction analysis:

`0x005292db`, `0x005f4ffa`, `0x005f6eda`, `0x0070f62d`, `0x0070fb45`, `0x0070fdeb`.

No manager/HDVehicle identity is inferred from `+0x374` equality. `0x004b86cf`, P1.3 completion and provider removal remain fail-closed; provider count remains 7.
