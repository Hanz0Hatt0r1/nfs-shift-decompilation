# Process 2 live mixed-sample contract (2026-10-24)

## Observed runtime contract

Process 1's Linux retail smoke reached the ReXGlue Vulkan presenter with three
captured draws and a matching source-0/sample-0 `Copy/Convert` to the
1280x720 frontbuffer. The refresh diagnostic reported draw 0 at 4x MSAA with
surface pitch 640 and draw 1 at 1x with pitch 1280; both had color base 0,
depth base 720, color format 1, and a 1280x720 raster extent. The same failure
recurred in the subsequent 32-second run. This is runtime evidence for the
draw-state transition, not evidence of a visible game frame.

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

## Validation and limits

`VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation /usr/bin/ctest --test-dir
/home/pes/work/process2-vulkan-mixed-build --output-on-failure` passed 4/4.
The updated mixed-sample renderer check passed and produced a full readback.
Its shaders and geometry are test inputs, not retail graphics.

The current P2 plugin has not yet been run through the Linux retail smoke
after replacing the stale loaded library. The observed failure therefore
does not establish that the current mixed-sample implementation fails. It
also does not prove that the updated plugin will produce a visible menu or
race frame; those remain runtime and scene contracts to verify.
