# Process 2 — native Vulkan renderer foundation (2026-10-22)

## Result

The renderer and platform surface probe now declare Vulkan 1.1 as their minimum
API. Surface selection skips devices whose reported `apiVersion` is below 1.1
and returns a distinct status when no Vulkan 1.1 device is available. Android
and XCB continue to create surfaces through the shared platform-neutral probe.

This is a portability foundation, not an Xbox 360 renderer. The existing native
backend consumes captured D3D9 draws and neutral SHIFT render packets. It has no
Xenos PM4 decoder, guest resource cache, or Xenos shader-microcode translator,
so it cannot replace the ReXGlue Xenos GPU plugin yet.

## Verification

- Vulkan-focused Python suite: 139 passed.
- Linux native Vulkan CMake build: all targets built.
- Android NDK 28.2, `arm64-v8a`, API 29 native-activity target: built.
- Headless clear and SPIR-V triangle smoke paths submitted on a GTX 950.
- On-device Android `ANativeWindow` surface probe ran on a Redmi Note 8 Pro
  (`begonia`, MT6785, Android 13/API 33, `arm64-v8a`):
  `ANativeWindow Vulkan surface probe status=0`. In this probe, zero means
  Vulkan 1.1 instance creation, Android surface creation, and a Vulkan 1.1
  physical device with a graphics+present queue all succeeded. This validates
  device/WSI availability only; it does not submit a frame or exercise SHIFT.
- Synthetic bundle smoke with `VK_LAYER_KHRONOS_validation`: enabled, zero
  validation errors; three warnings report unused vertex attributes. This is
  renderer/API plumbing evidence only, not a retail frame or parity claim.
- The broad `pytest -k vulkan` collection is not green in this environment:
  four unrelated RevEngInstr test modules fail collection because `jsonschema`
  is not installed. The targeted Vulkan test selection passes.
- The Redmi Note 14 Pro+ 5G remains untested. No game draw, swapchain frame,
  shader support matrix, or retail parity result is claimed for the Note 8 Pro.

## Xenos renderer boundary

An owned Xenos frontend needs real draw-boundary input before its packet format
or feature requirements can be fixed. The next capture should preserve the raw
PM4 provenance, draw/index parameters, vertex/index bytes, bound Xenos shader
microcode and constants, texture snapshots, render-target/depth state, and the
associated swap/present event. The frontend can then translate that evidence
into host-neutral resources and draw state; Vulkan handles and WSI remain in the
native core.

`SHIFT.XenosDrawSnapshot/1` is a proposed capture name only, not an adopted or
implemented interface. Its required fields must be validated against the first
actual SHIFT Xenos draw before it becomes a cross-component contract.
