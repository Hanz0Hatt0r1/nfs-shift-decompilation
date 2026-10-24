# Process 2 Xbox retail draw frontier — 2026-10-25

The latest Linux retail run advances past two captured draw blockers: draw #27
now passes its previously unsupported DP3 vector operation, and draw #28's
captured DXT4/5 base and mip addresses are accepted as one base-level image.
The preserved run log and machine-readable observations are in
[`process2_retail_draw27_scalar_and_resolve_20261025.json`](../evidence/process2_retail_draw27_scalar_and_resolve_20261025.json)
and
[`process2_retail_draw27_scalar_and_resolve_20261025.log.gz`](../evidence/process2_retail_draw27_scalar_and_resolve_20261025.log.gz).

## Remaining blockers

1. Draw #27's pixel shader reached an unsupported scalar-result operation in
   the latest run, whose loaded plugin did not report the opcode number. The
   source now translates Xenos scalar `FLOOR` (opcode 13) and reports the
   opcode and instruction slot for other unsupported operations. The floor
   semantics follow the Xenos opcode definition in the public
   [Xenia `ucode.h`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/ucode.h).
   A later retail run must establish whether opcode 13 was the observed
   operation or identify the next unsupported opcode; the already-running
   process has not loaded these changes.
2. The 24-draw frame fails refresh when it needs to preserve depth and stencil
   across 4x-to-1x sampling. The existing SDK checkout lacks an opt-in resolve
   capability. The separate [ReXGlue provider contract PR #2](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/2)
   exposes a `depthStencilResolveSampleZero` property only when the provider
   has enabled the required Vulkan path and both aspects support
   `VK_RESOLVE_MODE_SAMPLE_ZERO_BIT`. Process 2's plugin feature-detects that
   contract and remains fail-closed with older providers.

The provider PR is an independent integration. A separate Process 2 plugin
build against its branch now passes all four Linux plugin tests. The targeted
provider check ran with `VK_LAYER_KHRONOS_validation` on the GTX 950 and
reported `resolve pair=1`, `SAMPLE_ZERO=1`, and GPU-emulation features disabled.
The live retail process still uses the older provider build, so this does not
yet prove that a retail frame refreshes through the new path. Process 2 does
not modify the guest runtime or scheduler to work around that integration
boundary.

## Verified boundary

- Linux native Vulkan tests: 4/4 pass, including the Vulkan validation
  regression.
- Linux ReXGlue plugin tests: 3/3 pass against the current SDK checkout and
  4/4 pass against the separate resolve-capability branch.
- ARM64 shader translation regression: passed on the Redmi Note 8 Pro over
  Wi-Fi ADB. This does not exercise the retail Android runtime.
- The saved genuine retail loading frame has yellow-orange fill and a dark-gray
  empty track, matching the user-confirmed colors. It is not a menu/race frame.
- This latest Xbox retail run has no accepted retail readback. Logged draw
  submissions do not prove the frame was refreshed or displayed, and synthetic
  Vulkan regressions do not establish retail visual parity.

Both existing NFS Shift windows were left running for this diagnostic-only
change.
