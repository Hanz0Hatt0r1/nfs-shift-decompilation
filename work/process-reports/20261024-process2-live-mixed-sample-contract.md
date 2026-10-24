# Process 2 live mixed-sample contract (2026-10-24)

## Observed runtime contract

Process 1's Linux retail smoke reached the ReXGlue Vulkan presenter with three
captured draws and a matching source-0/sample-0 `Copy/Convert` to the
1280x720 frontbuffer. The refresh diagnostic reported draw 0 at 4x MSAA with
surface pitch 640 and draw 1 at 1x with pitch 1280; both had color base 0,
depth base 720, color format 1, and a 1280x720 raster extent. The same failure
recurred in the subsequent 32-second run while it used a stale staged plugin.
This is runtime evidence for the draw-state transition, not evidence of a
visible game frame.

## Loaded plugin identity

The shared Linux smoke environment staged
`/tmp/p1-virtual-input-20261024/librexgpu-shift-native.so`, SHA-256
`54348dd521b97b15be963d0b9f680172dbfb83c3ef5f2fbb979f618dc9c32aaa`.
That binary does not contain the current mixed-sample renderer diagnostic or
the 4x-to-1x mixed-frame implementation string; its error is the generic
sample-count fallback used when mixed-frame handling is not reached. The run
log does not include a dynamic-loader hash, so attribution to the staged file
is strong but not independently proven. The current CMake output is
`/home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/linux-amd64/librexgpu-shift-native.so`,
SHA-256
`ad5027c86712be52cc9df78213319be6262ac0999c30def3b34de89a419a01ad`; it
contains both. `ldd -r` resolves the current plugin against the shared
ReXGlue Debug runtime without undefined symbols.

In the current source, `submit_captured_vulkan_frame` routes a mixed sample
sequence through the existing 4x-MSAA-to-1x path when the matching captured
Copy/Convert target is present. That path permits the observed surface-pitch
change while retaining the same color/depth target identities. The renderer
regression now fixes the reported 4x/pitch-640 to 1x/pitch-1280 transition.

## Current plugin integration run

Process 1 confirmed that run 050 loaded the current `ad5027c8…` P2 plugin
against Debug runtime `680d98b9…`. Its 1,091,626-byte log has SHA-256
`b8bef4263007b40cc4a729aabe944830c4f6f667eaf4dd6d89cf5cb89215f117`. It
contains 1,980 successful Vulkan submit lines, 1,980 accepted
source-0/sample-0 Copy/Convert lines, and no Vulkan frame-refresh failures.
The earlier sample-count rejection is resolved when the current plugin is
loaded.

The same run reports four unique unresolved retail draws: the initial draw
has incomplete raster registers; draw #27 fails viewport/surface decoding;
draw #28 has an unsupported texture-fetch descriptor; draw #29 has an
unsupported color Copy/Convert state. The bounded log contains no screenshot
or Vulkan readback, and Process 1 did not confirm a menu transition. These
submits therefore do not establish visible retail parity.

The latest P2 plugin adds raw viewport, texture descriptor, and Copy/Convert
register values to those fail-closed diagnostics. Linux and Android ARM64
plugin builds succeeded; a new run is still needed to capture those fields.

## Validation and limits

`VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation /usr/bin/ctest --test-dir
/home/pes/work/process2-vulkan-mixed-build --output-on-failure` passed 4/4.
The updated mixed-sample renderer check passed and produced a full readback.
Its shaders and geometry are test inputs, not retail graphics.

The mixed-sample renderer test uses smoke shaders and geometry; it is not a
retail image. The successful refresh count likewise does not prove that a
visible menu or race frame was produced. Current unresolved draws and the
missing visual capture remain open renderer/runtime contracts.
