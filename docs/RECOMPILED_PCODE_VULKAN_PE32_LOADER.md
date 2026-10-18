# Recompiled P-code PE32 guest image loading

The Linux Vulkan runtime can load an x86 PE32 image into the 32-bit guest RAM
used by the recompiled P-code module:

```bash
shift_runtime \
  --mesh scene.mgeo \
  --shader-dir native_runtime/build/shaders \
  --recompiled-module libnfs_shift_pcode.so \
  --pe-image SHIFT.exe \
  --recompiled-step 0x00401000
```

The loader checks the DOS and PE signatures, I386 machine type, PE32 optional
header, section table, image bounds, and non-overlapping mapped section ranges.
It maps headers at `ImageBase`, copies section raw bytes to `ImageBase + RVA`,
and leaves virtual section tails zero-filled. It reports the mapped base, image
size, entry point, and section count in the runtime JSON.

When the PE32 optional header contains an import directory, the loader reads
named and ordinal imports and rewrites each IAT slot to a unique guest address.
The runtime implements the hash-locked retail image's first observed startup
import, `KERNEL32.dll!GetSystemTimeAsFileTime`: it writes an eight-byte Windows
FILETIME through the guest stack argument and applies the x86 stdcall stack
cleanup. Other imported APIs still stop with an error naming the `DLL!function`
or ordinal.

The module currently accepts one image-load attempt per guest address space and
loads only at the image's preferred base. The configured P-code step is invoked
by the native fixed-step loop; the PE entry point is reported but not executed
automatically. Most imported APIs, TLS, Windows process initialization, guest
page permissions, retail timing, and game startup are not implemented. A
missing generated-function export or an unhandled userop still fails closed.
The Vulkan scene and this P-code loop are therefore a runtime integration
probe, not a playable NFS Shift build.

The focused fixture test creates a small PE32 image and verifies header/section
mapping, zero-fill, named and ordinal IAT mapping, FILETIME output and stdcall
stack cleanup, null-pointer rejection, diagnostic import dispatch,
duplicate-load rejection, and generated P-code reads from guest memory. The
Linux Vulkan CI smoke runs the P-code read for three rendered frames and checks
that Vulkan validation reports zero errors. Results are recorded in
[`evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json`](../evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json)
and
[`evidence/recompiled_pcode_pe32_import_boundary_20261018.json`](../evidence/recompiled_pcode_pe32_import_boundary_20261018.json).
The first retail entry-point API step is recorded in
[`evidence/recompiled_pcode_kernel32_startup_20261018.json`](../evidence/recompiled_pcode_kernel32_startup_20261018.json).
