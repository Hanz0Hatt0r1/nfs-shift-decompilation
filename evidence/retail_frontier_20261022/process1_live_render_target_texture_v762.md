# Process 1 — live retail render-target texture callback, v762

## Run identity

- Original SHIFT PC retail 1.02 PE32 SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Local runtime binary SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`.
- Base startup P-code module: `libnfs_shift_pcode_startup_20261018.so` under the local startup-probe artifacts directory.
- Probe supplements and overrides were replayed from the recorded v759 module manifest evidence. A temporary manifest was reconstructed from its recorded module paths and SHA-256 values; its SHA-256 is `c96b3f9f43ba16ed1d6f9d0b1110659f5902a993e78b3b7d40bfab3ad1fd3dd0`.
- Game data: `pcode-game-data-v661`.
- v762 guest trace log SHA-256: `cccbf4360da2f2bd257128a7fd7eaa76b4c4a0b49e630f372372a61923dca5bd`.
- Trace selection: `SHIFT_TRACE_D3D9_RESOURCES=1`; guest imports `d3dx9_41.dll!D3DXCreateTexture` and `d3d9.dll!IDirect3DDevice9::CreateTexture` with stack slots `+0x4..+0x24`.

The original PE was loaded by the Linux P-code runtime. This is not a native Windows/Wine launch.

## Positive bounded observation

At guest dispatch 432964, caller `0x008391b0` called `d3dx9_41.dll!D3DXCreateTexture` (return address `0x00839b53`) with:

| Argument | Observed value |
|---|---:|
| Wrapper | `0x2002d614` |
| Width × height | `1024 × 4096` |
| Levels | `1` |
| Usage | `1` (`D3DUSAGE_RENDERTARGET`) |
| Format | `21` (`D3DFMT_A8R8G8B8`) |
| Pool | `0` (`D3DPOOL_DEFAULT`) |
| Output pointer | `0x27f7ddb8` |

The import returned `EAX=0`. The runtime resource trace then recorded the actual Vulkan callback result:

~~~text
guest D3D9 Vulkan image created texture=0x10477190 device=0x10476ed0 extent=1024x4096 format=21 levels=1 usage=0x1 pool=0
~~~

This proves that this bounded replay reached guest texture creation and that the configured backend created a Vulkan image for this descriptor. It does not prove that a draw bound or used that image.

## Replay result and limits

- Result: `host-frame-loop`, no blocker, 360 host frames, 1,752,571 P-code dispatches, 4,729 unique P-code functions, zero Vulkan validation errors.
- The bridge recorded 1,123 clear requests and 1,121 present requests; `guest_draw_translation=false` and `retail_rendering_proven=false`.
- Host-frame, clear, present and dispatch counts do not establish a menu, a retail draw, gameplay or race entry.
- The separate v759 observation `unsupported D3D9 managed texture description` was not reproduced in this v762 run. This does not establish that every texture path or descriptor is now supported.
- Raw logs, P-code modules and game data remain in local external artifact directories; they are not copied into this repository.

## Next renderer boundary

The positive render-target callback is a concrete Process 2 input. Process 2 is checking the image's layout/lifetime and whether the stored guest image is ever looked up by a draw or render-target path. The next upstream readiness evidence remains a real guest `DrawIndexedPrimitive` event with an accepted renderer packet; v762 did not provide one.
