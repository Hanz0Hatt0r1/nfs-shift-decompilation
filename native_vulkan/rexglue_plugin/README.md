# ReXGlue native SHIFT GPU input plugin

`rexgpu-shift-native` implements ReXGlue's `IGraphicsSystem` ABI and consumes
the guest PM4 ring without loading the `rexgpu-xenos` renderer. It creates the
SDK's Vulkan presentation provider with GPU emulation disabled and reads the
ring through `InitializeRingBuffer` and `CP_RB_WPTR`.

The write-pointer callback only queues work. A worker snapshots bounded ring
intervals, resolves the captured indirect-buffer packet form, frames PM4, and
decodes recognized register writes and `DRAW_INDX` packets. It does not apply
the register writes, resolve guest resources into Vulkan objects, or submit a
draw. A live game window therefore does not yet display game frames; the
captured bundle runner remains the only path that submits the observed SHIFT
logo draw. Guest GPU interrupts are not implemented, and reads from MMIO
registers other than the ring read/write pointers currently return zero.

## Build and smoke check

Configure against a ReXGlue SDK checkout that provides `rexui-vulkan`:

```sh
cmake -S native_vulkan/rexglue_plugin -B build/rexgpu-shift-native \
  -DSHIFT_REXGLUE_SDK_ROOT=/path/to/rexglue-sdk \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_FLAGS=-march=x86-64-v2 -DCMAKE_BUILD_TYPE=Release
cmake --build build/rexgpu-shift-native --target rexgpu_shift_native_factory_check
ctest --test-dir build/rexgpu-shift-native --output-on-failure
```

The smoke test loads the shared object, checks its exported ABI and factory,
constructs/destroys the frontend, and checks rejection of an unsupported
backend, undersized create info, and ABI mismatch.

The frontend is currently a Linux ReXGlue integration target. The SDK presenter
uses Vulkan 1.3 and SDL with X11/Wayland. The project-owned native renderer core
remains Vulkan 1.1 and is separately exercised on Android ARM64; this plugin
does not establish Android presentation support. ReXGlue's common runtime also
contains generic Xenos format utilities, but this plugin does not link the
`rexgpu-xenos` GPU renderer or command processor.
