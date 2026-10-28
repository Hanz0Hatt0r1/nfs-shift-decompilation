# Process 2 audit of P1 v50 interrupt frontier

The source capture is `/dev/shm/nfs-shift-p1-v50-native-p2-96169-20261028-r1`.
Its finalized event cutoff is 18:47:15.196 +0300. The first Native ring WPTR
write and first ring snapshot appear at 18:47:15.257, 61 ms after that cutoff.
There are no WPTR updates in the finalized live window. The three source-1
PM4 packets at 18:47:15.436, .438, and .472 are shutdown-tail activity and are
excluded from the finalized event set. They each decode CPU mask `0x04` and
return from callback `0x823B37B8` with status `invoked`.

The first tail packet is generation 1, batch `[25,46)`, packet ordinal 108,
source IB `0x095D0120` + byte offset 1304, with raw words
`[0xC0005400, 0x00000004]` and dispatch ID `0x21AF`. This confirms PM4 decode,
CPU-mask routing, callback lookup, and synchronous dispatch for that tail
packet; it says nothing about live-window callback delivery.

The v52 stop snapshot places the guest main thread in
`sub_823B9DA0 -> sub_823B90F0 -> ObReferenceObjectByHandle_entry ->
ObjectTable::LookupObject -> pthread_mutex_lock`. ReXGlue's
`global_critical_region::mutex()` returns a single static `std::recursive_mutex`;
both `ObjectTable::LookupObject` and `FunctionDispatcher::ExecuteInterrupt`
use it. The sampled mutex state (`lock=0`, `owner_lwp=0`) does not identify a
holder, so a deadlock or direct causal link is not proven. The earliest observed
missing stage in v50 is before ring submission/MMIO, not PM4 interrupt decode.

P1's v55 follow-up strengthens the mutex-frontier evidence: at 25 seconds, the
guest main thread, an XThread in `RetainHandle`, and an XThread in
`KernelState::OnThreadExecute` were all waiting on that same mutex address.
Their RDI values matched the mutex address, and each sample showed futex op 128
with expected value 2. The sampled lock word and owner were still zero, so this
snapshot does not establish a persistent owner or deadlock. The first 32 guest
atomic-lock helper calls returned in 1–3 ms with the guest word transitioning
`0 -> 1`; they do not explain the sustained startup stall. v55 also had no Bink
completion or live source-1 packet in its 25-second window. This moves the
priority toward ReXGlue startup/global-lock progress before GPU ring submission,
while leaving lock ownership unresolved for Process 1.

Before this change, the plugin logged `ring trace PM4_INTERRUPT` only after
`ExecuteInterrupt` returned. A blocked synchronous callback could therefore
leave no packet-completion row. The Native plugin now emits bounded
`PM4_INTERRUPT_BEGIN`, `guest interrupt dispatch begin`, `guest interrupt
execute begin`, and `guest interrupt execute return` records under the
existing ring-trace flag. The existing completion-row format, CPU mask,
callback invocation order, waits, and dispatch semantics remain unchanged.
These stage records will let a subsequent P1 capture distinguish no ring
submission, a callback-lock wait, a pre-Execute rejection, and a blocked
`ExecuteInterrupt` call.

Structured capture facts: [`process2_p1_v50_interrupt_stage_audit_20261028.json`](../evidence/process2_p1_v50_interrupt_stage_audit_20261028.json).

## Diagnostic plugin build

Commit `39509daf59f1a067e1a2831d068525e3eb7856ac` adds the stage records. The
Linux x86-64 DSO is
`/home/pes/work/process2-interrupt-stage-trace-39509daf/linux-x86_64/librexgpu-shift-native.so`,
SHA-256 `7237f08fede61d1d56e4dfa558be7a14c9b4c994ce9b6e77646139563a750976`,
Build ID `9ca94bcf0bfb4dff841c57c92b0011f5428451c4`. The matching Android
ARM64 compile-only DSO is at
`/home/pes/work/process2-interrupt-stage-trace-39509daf/android-arm64/librexgpu-shift-natived.so`,
SHA-256 `a875d791769daebcf188c903eb94922f232c63fec46f7c950b61ee9afdaf066e`,
Build ID `6c845f8dc19f78fc5477f742a9d77baf06455039`. The Android compile used
NDK 28.2.13676358 and API 29; it was not run on a device. It reports the
existing `fpscr.h` AArch64 operand-width warning.

The Linux live-ring write-trace CTest, factory CTest, two guest-ring/draw-input
CTests, and all nine interrupt-join parser tests pass. The live-ring fixture
needs a 4.5 GiB ReXGlue guest mapping; because host `/dev/shm` did not have that
capacity available, only the test process redirected `xenia_memory_*` backing
files to local disk with a temporary preload shim. The plugin artifact itself
does not include that shim. No retail run has consumed this build yet. Build
and check identities: [`process2_p1_v50_interrupt_trace_build_39509daf_20261028.json`](../evidence/process2_p1_v50_interrupt_trace_build_39509daf_20261028.json).
