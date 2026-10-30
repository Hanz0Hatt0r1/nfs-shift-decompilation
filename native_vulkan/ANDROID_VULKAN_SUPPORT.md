# Android Vulkan profile

## Device evidence

Read-only ADB `cmd gpu vkjson` on 2026-10-22 reported the connected handset as
Redmi Note 8 Pro (`begonia`), ARM64 (`arm64-v8a`), Android API 33, with Mali-G76
MC4. Its physical-device Vulkan API version is 1.1.131. The top-level
`vkjson` API version describes the instance/loader and is not the physical
device version. This measurement does not verify a Redmi Note 14 Pro+ 5G.

| Vulkan feature | Reported |
| --- | --- |
| `independentBlend` | supported |
| `fragmentStoresAndAtomics` | supported |
| `vertexPipelineStoresAndAtomics` | unsupported |
| `geometryShader` | supported |
| `fillModeNonSolid` | unsupported |

## Backend behavior

The shared XCB/Android surface probe now requests Vulkan 1.1 and admits only a
Vulkan 1.1 physical device with a queue that supports both graphics and
presentation. It does not enable or require optional device features. The
current captured-draw executor uses solid fill and creates its logical device
without enabling optional features, so the two reported unsupported features
do not block this current backend path.

The Android NativeActivity still proves only native-window surface creation
and queue compatibility. It does not execute a captured D3D9 draw or establish
retail NFS SHIFT frame parity on the handset. The local environment has no
Android NDK installation, so Android ARM64 compilation remains covered by the
repository's `android-vulkan` CI job rather than a local cross-build.
