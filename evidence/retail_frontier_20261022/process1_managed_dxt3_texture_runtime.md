# Process 1 — managed DXT3 texture producer support

## Retail evidence

The original Need for Speed SHIFT PC retail 1.02 `SHIFT.exe` (PE32 x86,
SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`)
was run under system Wine with the D3D9 capture proxy. The capture has SHA-256
`db71d32484c35d97c2aa8645d8f439376d7c1caaaca6041aa565f7549870625b`.

At event 2691/frame 20, the original game requested a managed DXT3 texture:
1024×512, one level, usage 0, format `861165636` (`D3DFMT_DXT3`), pool 1.
At event 37036/frame 281, it created a payload-backed 512×512, one-level
managed DXT3 texture. The following LockRect payload event reported pitch
2048 bytes and 262,144 bytes of compressed data; payload SHA-256 is
`3148e693a19b0d95a2a021dea80ff78c93b42ec366a4e1b6b31b9e14638e5f96`.
The capture details are preserved in the external Process 2 artifact
`PROCESS2_DXT3_HANDOFF.md` under the retail-run artifacts directory.

The capture is direct evidence that the original game uses this descriptor
and lock layout. It is not evidence that this Linux P-code runtime reached the
same call or rendered a racing scene.

## Runtime change

The managed D3D9 texture producer now accepts DXT3 in both the guest
`D3DXCreateTexture` entrypoint and `IDirect3DDevice9::CreateTexture`. Each mip
level uses `ceil(width/4)` blocks per row and `ceil(height/4)` block rows, with
16 bytes per 4×4 DXT3 block. `LockRect` returns the byte pitch and a pointer to
the requested block; partial rectangles must start on 4×4 boundaries, with
right/bottom edges allowed to terminate at the texture edge. Mip offsets use
the same layout as allocation. The existing 64 MiB guest allocation limit is
retained and size/pitch arithmetic is checked.

The official D3D9 references describe DXTn as 4×4 block-compressed, with
16-byte DXT3 blocks, byte pitches, and 4×4 LockRect alignment:
[Compressed Texture Formats](https://learn.microsoft.com/en-us/windows/win32/direct3d9/compressed-texture-formats),
[Locking Resources](https://learn.microsoft.com/en-us/windows/win32/direct3d9/locking-resources),
[D3DLOCKED_RECT](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dlocked-rect).
The D3D9 format reference also requires DXTn surface dimensions to be
multiples of four:
[D3DFORMAT](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat).

## Verification

The focused `shift_runtime_recompiled_pcode_module` regression exercises the
captured D3DX descriptor (512×512, DXT3, managed, one level), checks
`GetLevelDesc`, pitch 2048, the last byte of the allocated level, rejects a
non-block-aligned subrect, and verifies an aligned subrect pointer. A second
8×8, two-level DXT3 texture exercises level dimensions, base pitch, and the
level-1 data offset through COM `CreateTexture`; a 7×5 descriptor is rejected.

The runtime executable and regression target build successfully; the focused
test passes. The full Linux retail launch was not rerun for this change.

## Remaining limits

- This fixes the guest-side D3DX/D3D9 texture producer. It does not establish
  that an original game run through the current Linux P-code runtime reaches
  this descriptor or that a retail draw is translated.
- DXT3 managed levels must be explicitly nonzero and within the full mip
  chain; `levels == 0` remains unsupported by this guest path.
- The 64 MiB managed-texture cap remains in force.
- No Vulkan renderer files were changed.
