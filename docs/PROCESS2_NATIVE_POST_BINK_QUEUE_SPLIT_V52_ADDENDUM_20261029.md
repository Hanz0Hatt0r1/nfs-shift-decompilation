# Process 2 Native worker-ring writer provenance — v52 addendum

Date: 2026-10-29
Status: the capped ring writes are joined to synchronous source-1 callbacks; source-0/source-1 callback overlap is confirmed, but corruption by that overlap is not.

## Capture identity

The v52 Native run used XEX
`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`, host
`ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178`, runtime
`693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd`, and
Native plugin
`f213f4ca9b679660e18e17b68aa1cc6f64667388c8f0375ecd80b245db13f1c9`. It ran
85.301 seconds, reached Bink 281/281, had no controller input or probe guest
memory writes, and exited GDB successfully. The GDB trace script hash is
`f991c334a6596bfa25406484782018e591b52e630e5aacd40e12cc967379b63c`; the
captured GDB output hash is
`b69e1964ccc9d4228f5511dda0433e34141fc5dee236f1547c5fa2971a7556b3`.

The read-only source artifacts are `run_metadata.json`, `gdb.log`, and
`bin/logs/nfs_shift_001.14.log` under
`/home/pes/work/nfs-shift-p1-counter-ring-writers-v142-native-v52-20261029/`.
The Native log SHA-256 is
`1e1a4f78d7934239fc0a0890a18040129a84d0d286b935498228c340d5efd311`.

## Producer writes occur inside PM4 callbacks

The first worker-ring `+56` write (`0 -> 1`) is at 04:09:21.900. Its GDB stack
is:

```text
sub_823B8C60 + 333
  <- sub_823B37B8
  <- FunctionDispatcher::ExecuteInterrupt
  <- ShiftNativeGraphicsSystem::DispatchGuestInterrupt
  <- RingWorkerLoop
```

At the same timestamp, Native starts source-1 PM4 event #1213 / dispatch
`0x0EE9`: generation 1, ring `0x09752580`, root batch `6230/6233`, expanded
packet source `0x096EC0A0+0x5C`, raw words `[0xC0005400, 0x4]`, CPU 2, callback
`0x823B37B8(data=0xB7365F00)`. `ExecuteInterrupt` returns at 04:09:21.907.
Thus the first ring producer write occurs inside that synchronous guest
callback and before the Native PM4 handler returns from `ExecuteInterrupt`.

The next producer write (`1 -> 2`) is at 04:09:21.922. It falls inside source-1
event #1214 / dispatch `0x0EEB`, from
`0x096D8F80+0xA44`, raw words `[0xC0005401, 0x4]`; that callback starts at
04:09:21.921 and returns at 04:09:21.930. The remaining capped `+56` writes
also have the `sub_823B8C60 -> sub_823B37B8 -> ExecuteInterrupt` writer stack.

This is the guest worker-ring producer at `0xB7368BE0+56`, written by
`sub_823B8C60` inside interrupt callback execution. It is distinct from the
v51 `sub_823B31A0` / `manager+11012` producer probe. The v51 single increment
and v52's 16 ring-index writes describe different state and must not be
treated as contradictory observations.

The first worker active-record write sets
`0xB73689C4+76 = 0xC96E4C80` in `sub_823B87B0+1569`. About 32 ms later,
`sub_823B8C60+314` writes the same pointer to ring slot
`0xB7368BE0+76`. This proves the value flows through both observed locations;
it does not establish that the guest reused a stale record.

## Callback overlap

The v52 log contains source-0 vblank and source-1 PM4 callbacks executing at
the same time on different Native host workers. Both invoke
`0x823B37B8(data=0xB7365F00)` on CPU 2. For example:

- Source 1 dispatch `0x0EEB` executes from 04:09:21.921 through 04:09:21.930.
- Source 0 dispatch `0x0EEC` has logged completion at 04:09:21.926 and reports
  `dispatch_elapsed_ns=1,684,765`, placing its execution approximately within
  04:09:21.924–04:09:21.926.
- Source 0 dispatch `0x0EEE` overlaps source 1 dispatch `0x0EEF` around
  04:09:21.942–04:09:21.946. A `+56` write (`3 -> 4`) is observed at
  04:09:21.944 on the source-1 callback stack during this overlap.

The overlap is real, and Native has no per-CPU lock around
`FunctionDispatcher::ExecuteInterrupt`; its mutex protects only callback
pointer lookup. However, all capped `+56` writes are attributed to the source-1
thread, all capped `+60` writes to the guest consumer thread, and no source-0
write to the watched `+56/+60/+76` fields appears in that window. The trace
therefore proves concurrent access to the same guest callback and manager, but
does not prove that source 0 corrupted those particular queue fields or caused
the long-window counter underflow.

## Minimal causal join and diagnostic

The Native plugin already exports
`shift_native_gpu_trace_dispatch_id_v1()`; `nm -D` confirms it is a public
symbol in the v52 plugin. It returns the current thread-local interrupt
dispatch ID while `ExecuteInterrupt` is active. The smallest additional field
for the next GDB capture is that function's return value at each capped
`sub_823B8C60` and queue-field watchpoint. A nonzero ID joins the write directly
to its source-0 vblank or source-1 PM4 log record; the consumer thread should
normally report zero. This avoids timestamp-only assignment when callback
intervals overlap.

If a diagnostic A/B is needed, add only a temporary per-CPU serialization
around source-0/source-1 callback execution. Keep guest memory, counters, waits,
and callback payloads unchanged. Compare writer IDs, field values, and the
first backend-dependent split. Do not treat a changed result as a fix until a
separate original-game run confirms it.

## Limits

This is an evidence-only assessment; no Native runtime, guest state, tests, or
capture were changed. The callback-before-return order is established for the
capped writes. Callback overlap is established, but its effect on the watched
queue values and `manager+11012` remains unresolved.
