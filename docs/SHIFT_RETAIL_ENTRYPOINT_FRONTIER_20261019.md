# Retail entrypoint frontier follow-up — 2026-10-19

## Evidence

Probe v112 remains the latest full retail-entrypoint run. It used the retail
PE32 image with SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and
completed 600 host frames with Vulkan validation enabled and zero errors. The
guest entry point remained active after 155,507 dispatches across 1,417 unique
functions. Its saved main-thread stack ended at
`0x0090488a -> 0x009046aa -> 0x00a69160 -> 0x0040ba50 -> 0x006492d0 ->
0x00647500 -> 0x006472d0`; four worker threads were waiting and one thread was
ready. The full record is
[`entrypoint_probe_v112.json`](../evidence/retail_frontier_20261018/entrypoint_probe_v112.json).

Static disassembly of the same PE confirms that `0x006472d0` begins by calling
`0x00649760`, a thunk that jumps through the import slot for
`KERNEL32!SwitchToThread`. The function then updates the app's timer fields.
This is consistent with the cooperative yield/update path recorded by v112;
the scheduler snapshot does not prove that the main thread is stuck or that
the frontend has been reached. The v66 `Base System` allocation fatal is not
reproduced by v112 and is no longer the current observed blocker. Preserve its
diagnosis as historical evidence and revisit it only if it recurs.

## Capture decision

No additional dump from the original game is needed for this scheduler
frontier. The existing race captures already support draw-local state and
stream-0/index-buffer analysis. One shared dynamic stream-1 vertex buffer lacks
a payload; capture it only if offline analysis establishes that its exact
bytes are needed for a renderer translation. The existing buffer report
documents that bounded follow-up in
[`SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md`](SHIFT_D3D9_RACE_BUFFER_PAYLOAD_IDENTITIES_20261018.md).

## Next probe improvement

The frame-loop JSON records only the active guest call stack at shutdown, so it
cannot show whether repeated yield points are surrounded by changing function
calls. The scheduler now records the last 64 main-thread P-code function
entries in its snapshot. The next bounded entrypoint probe can use this history
to distinguish repeated update calls from progress into another startup
subsystem without changing the retail capture.

This is an observability improvement only. It does not assert entrypoint
completion, frontend rendering, D3D9-to-Vulkan integration, or playable
behavior.
