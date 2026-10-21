# Process 2 — managed DXT3 capture capability (2026-10-21)

## Patch

Apply this P2-only patch after Process 1 adds
`RecompiledGuestD3d9AdapterInfo::supports_dxt3_texture` to its public header.
It changes only the capture adapter and its focused regression check.

```diff
diff --git a/native_vulkan/src/d3d9_packet_capture_adapter.cpp b/native_vulkan/src/d3d9_packet_capture_adapter.cpp
--- a/native_vulkan/src/d3d9_packet_capture_adapter.cpp
+++ b/native_vulkan/src/d3d9_packet_capture_adapter.cpp
@@
-    // This adapter captures managed DXT5 bytes from guest memory; it does not
-    // advertise DXT5 support on the live Vulkan texture-upload path.
+    // This adapter captures guest-managed DXT3/DXT5 bytes; neither capability
+    // advertises support on the live Vulkan texture-upload path.
     adapter.supports_dxt5_texture = true;
+    adapter.supports_dxt3_texture = true;
@@
diff --git a/native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp b/native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp
--- a/native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp
+++ b/native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp
@@
     require(info.supports_dxt5_texture,
             "capture adapter enables guest-managed DXT5 packet snapshots");
+    require(info.supports_dxt3_texture,
+            "capture adapter enables guest-managed DXT3 packet snapshots");
```

The capture adapter already copies compressed DXT3 mip bytes from packet-owned
guest memory and serializes DXT3 snapshots. This change only advertises that
capture capability. It does not enable native BC2/DXT3 upload or otherwise
change live Vulkan texture support.

## Retail evidence

The pinned original `SHIFT.exe` was captured through system Wine. In
`shift_d3d9_capture.jsonl` (SHA-256
`db71d32484c35d97c2aa8645d8f439376d7c1caaaca6041aa565f7549870625b`):

- Event 2691/frame 20: `CreateTexture(1024, 512, levels=1, usage=0,
  format=861165636, pool=1)`. Format `861165636` is FOURCC DXT3
  (`0x33545844`); pool 1 is managed.
- Event 37037/frame 281: a captured 512×512 managed DXT3 level, pitch 2048,
  262,144 bytes. Payload SHA-256:
  `3148e693a19b0d95a2a021dea80ff78c93b42ec366a4e1b6b31b9e14638e5f96`.

This is actual managed DXT3 data from the original game capture. The P1
frontier’s `unsupported D3D9 managed texture description` corresponds to the
producer-side format guard: P1 currently gates managed DXT5 through its
capability bit and rejects DXT3 unless the new independent bit is set.

## Verification

The existing P2 adapter check already asserts DXT5 capture capability. The
patch adds the matching DXT3 assertion. Run after the P1 header field lands:

```bash
cmake -S native_vulkan -B /tmp/nfs-shift-d3d9-packet-build \
  -DSHIFT_RECOMPILED_RUNTIME_INCLUDE_DIR=/tmp/p1-d3d9-contract/native_runtime/include
cmake --build /tmp/nfs-shift-d3d9-packet-build \
  --target shift_vulkan_d3d9_packet_capture_check -j2
/usr/bin/ctest --test-dir /tmp/nfs-shift-d3d9-packet-build \
  -R shift_vulkan_d3d9_packet_capture_adapter --output-on-failure
```

The available delegated workspace did not expose a local checkout for running
that target. The prior P2 adapter PR #2141 reports the same focused CTest
passing with the DXT5 capability assertion. The added DXT3 assertion remains
to be run after integration.

## Ownership

This report is on branch `work/process-reports`. Only these P2 paths are in
the patch:

- `native_vulkan/src/d3d9_packet_capture_adapter.cpp`
- `native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp`

No P1 runtime/P-code/scheduler/Ghidra files, renderer upload code, or Vulkan
format capabilities are changed by this patch.
