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
the decoder, not a retail image. Run 058 below confirms that draw #28 now
resolves from the real guest-memory bytes; its rendered pixel values remain
unverified.

## Retail confirmation run (058)

Process 1 staged the exact Linux P2 plugin from the previous change:
`61779bef3ff386705b5f513e5af89c816586f98efa35f5ced1a19b133abc4617`. The
bounded 30-second smoke used host `nfs_shift`
`6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b`, runtime
`a324c4099ccc3d09462510f75d8a755721405f8b806c8657667ef4ef3019571b`, and
game root `/tmp/nfs_shift_xbox_game_root_20261023`. Log
`/tmp/p1-virtual-input-20261024/logs/nfs_shift_058.log` is 379,226 bytes,
SHA-256 `37d9bc618fb2916cfeb9b7b2b8e916fc056fe6838ff8f618d15a3105c8ba70e5`.

The log has 367 presenter-submit entries: 284 one-draw, 51 two-draw, and 32
four-draw frames, with zero Vulkan refresh failures. Its unresolved draw
outcomes are:

- #0 still lacks a complete raster snapshot; the captured register-valid mask
  is `0x17038`.
- #27 has viewport bounds x=392..888 and y=478..486 on a 1280-pixel surface
  pitch. Its screen scissor is broad (`0..8192`); window scissor is exactly
  `{392,478,888,486}`. The existing parser rejected any viewport smaller than
  the target.
- #28 has no unresolved diagnostic and the submitted batch grows from three
  draws in the prior run to four. This confirms the descriptor and real guest
  memory bytes passed the DXT2/3 resource path, not that the texture colors
  were correct or visible.
- #29 still fails captured target/raster-state decoding and its Copy/Convert
  check (`control=0`, destination `0x0975e000`, pitch `0x02d00500`, info 0).

The P2 source now decodes #27's viewport as 496x8 at `{392,478}`, retains the
1280x720 target extent from the prior guest swap, and sends both viewport and
scissor coordinates to Vulkan. The exact register tuple passes decoder and
offscreen-renderer regressions on host and on the Mali-G76 phone GPU. The
run 059 used Linux plugin
`e05ea50726caea536e25f0e3f76d052e56740bdc455fb26d0884ecab8e8adfdd` and
confirms #27 no longer appears as unresolved. Run 058 itself had no
Vulkan readback or screenshot, so it remains a state/submit milestone rather
than visible-scene parity.

## Retail confirmation run (059)

Process 1 staged the updated Linux plugin with partial-viewport support:
`e05ea50726caea536e25f0e3f76d052e56740bdc455fb26d0884ecab8e8adfdd`. The
30-second bounded smoke used host `nfs_shift`
`6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b` and
ReXGlue runtime `a324c4099ccc3d09462510f75d8a755721405f8b806c8657667ef4ef3019571b`.
Log `/tmp/p1-viewport-smoke-20261024/logs/nfs_shift_001.log` is 984,506 bytes,
SHA-256 `5fe1420422d420cae253b2f7d605f5c83ac0b634cc56c72a27e4c9c426765559`.

It contains 1,762 presenter submissions (1,436 one-draw, 257 two-draw, and
69 five-draw batches), plus 1,762 accepted source-0/sample-0 Copy/Convert
entries and zero Vulkan refresh failures. Only #0 and #29 remain in the
unresolved-draw list: #27's partial viewport is no longer rejected, and #28
remains non-rejected. The five-draw batch is consistent with #27 and #28
joining the accepted draws, but the log has no per-index success receipt. No
readback or screenshot was configured, so this run confirms state acceptance
and Vulkan submissions, not visible pixels.

Draw #29 still reports unsupported target/raster state and zero-control,
format-0 Copy/Convert registers. Run 059 used the prior binary, whose INFO
diagnostic did not include the complete raster tuple. The current working-tree
build adds surface, color/depth, mode, depth, blend, stencil, setup, viewport,
scissor, and window-offset values to that rejection; support remains fail
closed pending those captured values.

## Retail confirmation run (060)

Process 1 staged the diagnostic Linux plugin
`331794ec66bb3738aa3fae2c862952aa86283267c4a2b372736e5e813d42b892` for a
30-second retail smoke. It used host `nfs_shift`
`6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b` and
ReXGlue runtime `a324c4099ccc3d09462510f75d8a755721405f8b806c8657667ef4ef3019571b`.
The guest XEX SHA-256 was
`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58` under
game root `/tmp/nfs_shift_xbox_game_root_20261023`. Log
`/tmp/p1-p2-run060-20261024/logs/nfs_shift_001.log` is 806,235 bytes,
SHA-256 `6f55a095f1fad55eeb60bc47fd9d179596d464d32bc676695113714363342458`.

The run recorded 1,349 presenter submissions (1,175 one-draw, 110 two-draw,
64 five-draw), 1,715 aggregate draw submissions, 1,349 accepted Copy/Convert
entries, and no Vulkan refresh failures. Draw #27 and #28 remain resolved;
#0 still lacks a complete raster snapshot (`valid_mask=0x17038`). Draws #25
and #29 were rejected with Xenos mode 5 and the captured depth-only register
tuple. This old diagnostic binary predates the mode-5 decoder now in the
working tree.

The first submitted frame readback was 1280x720 A2B10G10R10 (3,686,400 bytes),
SHA-256 `cd6226f8bf299d3ab51cfc10af0b585167106d7caa356e8604bfe48ad9a49de5`,
FNV-1a `B161DE6EEC272325`. All RGB pixels were black (one RGB value; only the
alpha channel varied). Therefore this is direct negative evidence: Vulkan
presenter submissions are happening, but the selected early retail frame has
no visible game color.

Xenia classifies Xenos EDRAM mode 5 as depth-only and suppresses color writes
for that mode ([mode enum](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/xenos.h),
[raster-state normalization](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/draw_util.cc)).
The current P2 decoder accepts that captured form, preserves depth/stencil
state, and forces the Vulkan color-write mask to zero. Exact run-060 registers
now have decoder and offscreen-renderer regressions.

## Retail confirmation run (061, requested)

Process 1 was asked to stage the current Linux plugin
`0aa45b48882146e6bddc0a0747f0e83abc4be21be662d151a017b7687b3ed949` and run a
bounded retail smoke with readback explicitly selected at submitted presenter
frame 100 (`/tmp/p2-run061-retail-output.a2b10g10r10`). This binary includes
the depth-only mode-5 decoder and selectable frame readback. The result is
pending; the frame-060 black readback means no retail-visible output has yet
been demonstrated.

A separate P2-side attempt used the same host, runtime, and current plugin
hashes from `/tmp/p2-run061-20261024`, with the same 30-second bound and
frame-100 readback setting. It did not reach a Vulkan presenter: its 40-byte
log (`c848530a35e0d41b82034e1221ea6ce931b239251fb36b13b8769e6ed8776aea`)
contains only `SDL video driver: wayland`, no readback file was created, and
the host required SIGKILL after the 30-second timeout plus 5-second grace
period. This is a launch failure, not a renderer result. The Process 1 retail
smoke request remains pending and the phone app was not touched.

## Validation and limits

`VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation /usr/bin/ctest --test-dir
/home/pes/work/process2-vulkan-mixed-build --output-on-failure` passed 4/4.
The updated mixed-sample renderer check passed and produced a full readback.
The current Linux ReXGlue plugin CTest passed 3/3 under forced Vulkan
validation, including the live-ring presenter and synthetic readback checks.
The current Android ARM64 Debug plugin also rebuilt successfully; its hash is
recorded below. The installed retail APK was not replaced or restarted.

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

After the partial-viewport change, the Android ARM64
`xbox_live_vulkan_renderer_check` also passed on the same Mali-G76 device. It
executed the offscreen run-058 496x8 viewport/scissor case, sample-zero
Copy/Convert, and rectangle-list path with synthetic shader/resource inputs.
After adding the run-060 mode-5 case, both ARM64 standalone regressions were
rebuilt from the current source and passed again on-device. The renderer check
reported Vulkan 1.1 AutoIndex point and rectangle-list submission plus
sample-zero Copy/Convert on Mali-G76 MC4; it also verifies that the synthetic
depth-only draw produces no color writes. These are Vulkan/device regressions,
not game screenshots; `NfsShiftActivity` stayed foreground and was not
restarted.

The latest Linux plugin build SHA-256 is
`0aa45b48882146e6bddc0a0747f0e83abc4be21be662d151a017b7687b3ed949`; the
latest Android Debug plugin build SHA-256 is
`7fcba9bc3587f46f0293535fcbbb9141c3dc49b51f068d5c3ecf4a490beef67a`. The
Linux run 061 is pending. The previous Linux build `61779bef…` resolved
DXT2/3 from real guest memory in run 058; the subsequent runs no longer report
#27 or #28 as unresolved.

The mixed-sample renderer and live-ring readback tests use smoke shaders,
synthetic resource bytes, and synthetic geometry; neither is a retail image.
The successful refresh count likewise does not prove that a visible menu or
race frame was produced. DXT2/3 support is unit-validated but has not yet been
confirmed for visible color output, though run 058 confirms the real #28 guest
bytes resolve. Run 059 no longer reports #27 as rejected, but its pixels were
not read back. Run 060 readback was entirely black. Draw #0 remains incomplete;
the current mode-5 implementation awaits retail confirmation in run 061.
Visible menu/race output remains an open contract.
