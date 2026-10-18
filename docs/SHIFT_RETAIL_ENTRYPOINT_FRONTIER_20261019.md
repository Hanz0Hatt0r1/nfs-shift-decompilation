# Retail entrypoint frontier follow-up — 2026-10-19

## Evidence

Probe v113 used the retail PE32 image with SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and
completed 600 host frames with Vulkan validation enabled and zero errors. It
ran 155,506 guest dispatches across 1,417 unique functions. Its saved main-thread
stack ended at `0x0090488a -> 0x009046aa -> 0x00a69160 -> 0x0040ba50 ->
0x006492d0 -> 0x00647500 -> 0x006472d0`; four worker threads were waiting and
one thread was ready. The complete machine-readable record and log are
[`entrypoint_probe_v113.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v113.json)
and
[`shift-probe-v113-function-history-600-validation.log`](../evidence/retail_frontier_20261019/shift-probe-v113-function-history-600-validation.log).

The 64-entry history shows calls through `0x00637840`, `0x00508ea0`,
`0x0054be00`, `0x0082db70`, `0x00894b60`, `0x00833670` and a cluster around
`0x00807030`, followed again by `0x006492d0 -> 0x00647500 -> 0x006472d0`.
Static disassembly confirms that `0x006472d0` calls `0x00649760`, which jumps
through the retail `KERNEL32!SwitchToThread` import before updating timer
fields. The history now supplies an exact call sequence to classify, but it does
not prove a hang or frontend progress.

The first branch-level candidate is the state gate at `0x0050ceb0`, called
from `0x0054be00` on the object at the `0x00545d90` singleton plus `0x108`.
It tests the object at `0x0082f3c0` (`[this+0x24] == 0`) and then
`0x0050c880`; a true result branches through `0x0048fb36` and returns true.
The false path may call a virtual method at offset `0x24c` through the object
at `[this+0x48]`, then returns false. `0x0050c880` also dispatches through a
function pointer at `0x00ac59d0`, whose image value points to internal code at
`0x005460c0`, rather than a Win32 import. The history reaches `0x0050c8a9`,
which is the `[this+0x0c] == 0` path in `0x0050c880`; it then records
`0x00833670`. That ordering is consistent with the false result continuing to
the later virtual callback in `0x0050ceb0`, but the history does not record the
object pointer or return values. The field meanings and whether this state gate
explains the later return to the scheduler remain unresolved.

The old v66 `Base System` allocator fatal did not recur in v112 or v113 and is
historical unless observed again. The current software frontier is identifying
which startup helper returns to the yielding update path and whether a missing
portable runtime service or state transition explains that return.

## Capture decision

No additional dump from the original game is needed for this scheduler
frontier. The existing race captures already support draw-local state and
stream-0/index-buffer analysis. One shared dynamic stream-1 vertex buffer lacks
a payload; capture it only if offline analysis establishes that its exact
bytes are needed for a renderer translation. The existing buffer report
documents that bounded follow-up in
[`SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md`](SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md).

## Next engineering step

Continue from the newly identified state gate: resolve the owning object and
state fields around `0x0050ceb0` / `0x0050c880`, then follow the caller path
from `0x0054be00` back to `0x006492d0`. The observed gate uses internal PE code,
so first establish whether its object state or scheduler handoff is wrong before
changing runtime services. Implement the smallest generic runtime correction
supported by evidence and run another bounded probe. Keep generated binaries
and supplements in the external artifact cache.

The existing race capture still lacks one shared dynamic stream-1 vertex-buffer
payload. Do not capture it unless renderer-side static analysis shows those
exact bytes are needed.
