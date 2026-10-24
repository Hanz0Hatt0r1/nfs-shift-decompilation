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

## Follow-up retail state capture (run 054)

Process 1 reports run 054 used the instrumented Debug `natived.so` build
`49796434995a13b35529c5690f484ad75b08505b15d784cc7e8bbe9f10c869d4`. The
staging directory also contained an older release-name plugin, so this identity
is attributed from the raw diagnostic fields and Process 1's selected Debug
path; the older sibling was not removed. The log is
`/tmp/p1-virtual-input-20261024/logs/nfs_shift_054.log`, SHA-256
`c0d1cd924d4d7d554e8ed3f854addb174529e3bdb2df9b3a83d3955fd11116a9`.

The four unresolved contracts were:

- Draw #0: incomplete captured raster register state.
- Draw #27: surface `0x14000500`; viewport floats `{248, 640, -4, 482}`. The
  existing decoder only accepts a viewport covering the complete target.
- Draw #28: texture fetch constant 0, descriptor
  `{0x8800d8fe, 0x09e57053, 0x003fe3ff, 0x01280d10, 0x3, 0xa10}`. This is a
  tiled 1024x512 Xenos format-19 (DXT2/3) image with endian mode 1 and a
  524,288-byte compressed base level.
- Draw #29: Copy/Convert registers `{control=0, base=0x0975e000,
  pitch=0x02d00500, info=0, valid=0xf}`. The frame also has accepted
  source-0/sample-0 Copy/Convert operations. This zero-control state is not
  treated as a supported conversion.

The 1,122,407-byte run-054 log contains 2,050 successful Vulkan submits,
2,050 accepted source-0/sample-0 Copy/Convert lines, and zero frame-refresh
failures. It reached title shader-storage initialization. Start/A was sent
through the virtual pad, but the bounded run did not confirm a menu or race
image. The raw data selects the next renderer work; it does not establish
visible parity.

## Captured DXT2/3 texture support

The P2 decoder now accepts the observed format-19/endian-1 descriptor, untile
alignments of 32x32 compressed blocks, byte-swaps each captured 16-bit word,
and expands DXT2/3 blocks on the CPU to RGBA8 for the Vulkan upload. The
software expansion avoids requiring optional Vulkan BC compression support on
Mali/ARM devices. This supports the observed base-level form only; mip chains,
unaligned tiling, and other compressed formats remain rejected.

The target regression checks the exact run-054 descriptor and a tiled 128x128
DXT2/3 conversion fixture, including block positions across tile/bank/pipe
boundaries, mode-1 byte order, endpoint colors, and alpha. The fixture tests
the decoder, not a retail image. The next retail smoke must confirm draw #28
resolves from the real guest-memory bytes.

## Validation and limits

`VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation /usr/bin/ctest --test-dir
/home/pes/work/process2-vulkan-mixed-build --output-on-failure` passed 4/4.
The updated mixed-sample renderer check passed and produced a full readback.
The latest Linux ReXGlue plugin CTest passed 3/3. The latest Android ARM64
plugin and native runtime built successfully, and its factory plus live-ring
checks passed on the Redmi Note 8 Pro (Mali-G76, Vulkan 1.1.131).

The Android synthetic readback initially missed its capture because the Debug
plugin was configured for submitted frame 4, while the live-ring fixture
submits its three MMIO batches as one Vulkan frame. An explicit
`SHIFT_NATIVE_VULKAN_READBACK_PATH` now selects the first submitted frame; the
configured Android debug fallback still honors its selected frame. The Debug
Android plugin was rebuilt with the fallback still set to frame 4 and the
explicit-path regression passed on the Redmi Note 8 Pro: 921,600 non-black
pixels were read back from a synthetic magenta Vulkan frame on Vulkan
1.1.131/Mali-G76. The raw readback SHA-256 is
`bac5569a33a5dbff11ac418a9c89bd18824c1bc0c862420c8da1d7598fc328f2`.
This validates the readback trigger and Vulkan output path, not retail
graphics. The installed retail APK was not replaced or restarted, and
`NfsShiftActivity` remained foreground. The standalone ARM64
`shift_xbox_draw_input_check` was also built from this branch and passed
on-device, exercising the DXT2/3 decoder on the phone CPU.

The latest Linux plugin build SHA-256 is
`61779bef3ff386705b5f513e5af89c816586f98efa35f5ced1a19b133abc4617`; the
latest Android Debug plugin build SHA-256 is
`9b88077e3ec871d2693291db2c8d5188ec7cfd0abdf76186a13fefef88ca2d37`. Process
1 has been sent the Linux plugin identity for a bounded retail run. This new
DXT2/3 path still awaits confirmation against the real guest-memory payload.

The mixed-sample renderer and live-ring readback tests use smoke shaders,
synthetic resource bytes, and synthetic geometry; neither is a retail image.
The successful refresh count likewise does not prove that a visible menu or
race frame was produced. DXT2/3 support is unit-validated but has not yet been
confirmed against the real #28 guest-memory payload. Draw #0, #27, #29 and
visible menu/race output remain open contracts.
