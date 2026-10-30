# Reproducible Xbox 360 host build recipe

This directory makes one question cheap:

> **Which SDK commit and which plugin source commit produced this `.so`?**

Before this recipe existed, 96 run directories under `/home/pes/work/nfs-shift-p1-*`
shared one unlabelled plugin SHA-256 and nothing in Git said what produced it.
The ledger and verifier here replace that with a tracked, checkable answer.

| File | Purpose |
| --- | --- |
| [`pins.json`](pins.json) | machine-readable pin ledger: xex, SDK fork commit, artifact hashes, producer commits, per-entry `verified`/`unverified`/`unavailable` status |
| [`verify_pins.py`](verify_pins.py) | recomputes hashes of locally present artifacts, exits non-zero on mismatch, tolerates absence, `--json` / `--explain` |
| `../../test_build_pins.py` | regression test for the ledger schema and verifier behaviour |

Human-readable companion: [`docs/XBOX360_BUILD_PINS_20261030.md`](../../../docs/XBOX360_BUILD_PINS_20261030.md).

## Answering the question in one command

```sh
# from the repository root
python3 tools/xbox360/build/verify_pins.py --explain plugin_native_vulkan
```

which prints the pinned sha256, the artifact it names, the SDK commit that
produced it, the plugin source commit when known, the producer path and the
original note. To check every artifact against the ledger:

```sh
python3 tools/xbox360/build/verify_pins.py            # human readable
python3 tools/xbox360/build/verify_pins.py --json     # machine readable
python3 tools/xbox360/build/verify_pins.py \
  --search-root /home/pes/work --require runtime      # locate missing + hard-require one
```

Exit codes: `0` all located artifacts matched; `1` a located artifact did not
match; `2` the ledger is unreadable or fails schema validation. A missing
artifact is reported as `unavailable` and is **not** a failure.

To answer "what produced the `.so` in this run directory", hash the file and
look it up:

```sh
sha256sum /home/pes/work/<run>/bin/librexgpu-shift-native.so
python3 tools/xbox360/build/verify_pins.py --json | grep -B4 -A4 <hash>
```

A hash that matches no ledger entry is unlabelled evidence: either add the
entry (with the producer commit actually resolved) or do not cite it.

## Prerequisites

Recovered from the build trees that produced the pinned artifacts, not from
upstream documentation:

- `cmake` — `/usr/bin/cmake`, generator **Ninja Multi-Config**
  (`CMAKE_GENERATOR:INTERNAL=Ninja Multi-Config`).
- `ninja`.
- `clang` / `clang++` — `/usr/bin/clang` and `/usr/bin/clang++`
  (`CMAKE_C_COMPILER:UNINITIALIZED=clang`, `CMAKE_CXX_COMPILER:UNINITIALIZED=clang++`).
- Vulkan headers — vendored inside the SDK at `thirdparty/vulkan-headers`
  (`-DREXGLUE_USE_VULKAN=ON`); no system Vulkan SDK package is required for
  the Linux host build.
- `glslang` — vendored inside the SDK at `thirdparty/glslang`; it is compiled as
  part of the tree, so `glslangValidator` does not have to be installed
  separately.

## Recovered real configuration

From `/home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/build/linux-amd64/CMakeCache.txt`
(the tree that produced the pinned native plugin):

```
CMAKE_GENERATOR            = Ninja Multi-Config
CMAKE_C_COMPILER           = clang
CMAKE_CXX_COMPILER         = clang++
CMAKE_CXX_FLAGS            = -march=x86-64-v2
REXGLUE_USE_VULKAN         = ON
CMAKE_HOME_DIRECTORY       = /home/pes/work/rexglue-sdk-rexui-vulkan-20261023
```

From the sibling plugin build cache
`/home/pes/work/.build-process2-p2161-vulkan-plugin-20261027/CMakeCache.txt`:

```
CMAKE_BUILD_TYPE                  = Release
REXGLUE_USE_VULKAN                = ON
REXGLUE_USE_D3D12                 = OFF
REXGLUE_BUILD_TESTS               = OFF
REXGLUE_ENABLE_SANITIZERS         = OFF
REXGLUE_ENABLE_TRACY              = ON
REXGLUE_ENABLE_PERF_COUNTERS      = ON
REXGLUE_ENABLE_FIDELITYFX         = OFF
SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON = OFF
SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME  = 500
SHIFT_REXGLUE_PLUGIN_OUTPUT_DIR   = <build>/output
```

Per-translation-unit flags exactly as recorded in
`.build-process2-p2161-vulkan-plugin-20261027/compile_commands.json`
(first entry, a glslang thirdparty TU — the plugin TU is not present in that
file because the plugin was built from a different tree):

```
/usr/bin/clang++ -DENABLE_OPT=0 -DGLSLANG_OSINCLUDE_UNIX \
  -DREXGLUE_BUILD_CONFIG=\"Release\" -DREX_PLATFORM_LINUX=1 \
  -march=x86-64-v2 -O3 -DNDEBUG -std=c++11 -fPIC -mcmodel=large \
  -fno-strict-aliasing -ffp-model=strict -O3 -DNDEBUG -fno-char8_t \
  -Wall -Wuninitialized -Wunused -Wunused-local-typedefs \
  -Wunused-parameter -Wunused-value -Wunused-variable -Wno-reorder \
  -fno-exceptions
```

Note `-ffp-model=strict`, `-mcmodel=large` and `-fno-exceptions`: the SDK
build deliberately keeps strict floating-point semantics, because the guest
PPC→C++ lowering depends on them. Do not "optimise" these away in a rebuild —
a rebuild with `-ffast-math` or a default code model is not the pinned artifact
even if it links.

## Build steps (Linux x86-64, Release)

```sh
export REXGLUE_SRC=/path/to/rexglue-sdk          # clone of the pinned fork
export WORK=/path/to/build-root                   # outside the repo

git clone https://github.com/Hanz0Hatt0r1/rexglue-sdk "$REXGLUE_SRC"
git -C "$REXGLUE_SRC" checkout <pin from pins.json: sdk.fork_commit_full>

cmake -G "Ninja Multi-Config" -S "$REXGLUE_SRC" -B "$WORK/out/build/linux-amd64" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_FLAGS=-march=x86-64-v2 \
  -DREXGLUE_USE_VULKAN=ON \
  -DREXGLUE_USE_D3D12=OFF

cmake --build "$WORK/out/build/linux-amd64" --config Release --target rexruntime
cmake --build "$WORK/out/build/linux-amd64" --config Release --target rexgpu-xenos
```

Multi-config target names are phony aliases over the per-config outputs:

```
librexgpu-xenos.so        -> out/linux-amd64/{Debug,RelWithDebInfo,Release}/librexgpu-xenos[d|rd].so
librexruntime.so          -> out/linux-amd64/{Debug,RelWithDebInfo,Release}/librexruntime[d|rd].so
```

## Where the native Vulkan plugin comes from

The SHIFT native Vulkan plugin is **not** an SDK target. Its source lives in the
nfs-shift repository at `native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp`
(branch `work/process2-xbox-live-ring-20261023`, PR #2161) and it is built
against an SDK tree pointed at by `SHIFT_REXGLUE_SDK_ROOT` /
`REXGLUE_SDK_PATH`:

```sh
cmake -G "Ninja Multi-Config" -S <nfs-shift>/native_vulkan/rexglue_plugin \
  -B "$WORK/plugin" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DREXGLUE_USE_VULKAN=ON \
  -DREXGLUE_SDK_PATH="$REXGLUE_SRC" \
  -DSHIFT_REXGLUE_SDK_ROOT="$REXGLUE_SRC" \
  -DSHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME=500 \
  -DSHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON=OFF \
  -DSHIFT_REXGLUE_PLUGIN_OUTPUT_DIR="$WORK/plugin/output"
cmake --build "$WORK/plugin" --config Release --target rexgpu-shift-native
```

Artifacts land in `SHIFT_REXGLUE_PLUGIN_OUTPUT_DIR` (observed:
`<build>/output/librexgpu-shift-native.so`) and in the SDK's
`out/linux-amd64/` install tree, which is where the pinned copy lives.

## Known divergence — read this before trusting the recipe

The pinned artifacts were produced by **two different SDK trees**, and the
ledger says so explicitly rather than pretending otherwise:

| Artifact | Producer tree | Commit |
| --- | --- | --- |
| `librexgpu-shift-native.so` (`fd615ada…`) | `rexglue-sdk-rexui-vulkan-20261023` | `b3648b013b02770fa5ca8d4618235b2326c911ca` (verified) |
| `librexruntime.so` (`693abc48…`) | not resolved | `unverified` |
| `nfs_shift` (`ff4278b3…`) | not resolved | `unverified` |
| `librexgpu-xenos.so` (`8b5abe7a…`) | `rexglue-sdk-retail-lwsync-20261027` (from `xenos-build.log`) | `unverified` |

The fork HEAD recorded as the integration target is `32afce4` on
`rexglue-sdk-xbox360-memory-lifecycle-20261025`; the ref itself was confirmed
with `git log --oneline -1`, but only the short id was captured, so
`sdk.fork_commit_full` stays `null` until someone runs
`git -C <clone> rev-parse HEAD`.

Consequences, stated plainly:

1. Rebuilding at fork HEAD `32afce4` will **not** byte-reproduce the pinned
   runtime or the pinned native plugin. Two SDK trees are in play.
2. `librexgpu-xenos.so` hashes identically to a locally renamed build copy
   (`librexgpu-xenos-pm4-trace.so` in
   `nfs-shift-p1-v86-xenos-dispatch-join-20261028/runtime-build/`), so its
   source commit cannot be asserted from the hash alone.
3. 32 copies of a *different* xenos hash (`19053b69…`, SDK
   `rexglue-sdk-retail-lwsync-20261027`) exist in `/home/pes/work`. Those runs
   are not the pinned configuration.

Reconciling the runtime, host and xenos artifacts onto one recorded SDK commit
is open work; the ledger marks every unresolved field `unverified` on purpose
so no citation can accidentally inherit an unearned "verified".

## Rules

- Build outputs, SDK copies, XEX bytes and dumps are **never** committed. Only
  hashes, commits and this recipe are tracked.
- Any evidence file citing a plugin or runtime hash must be reproducible from a
  `pins.json` entry. If it is not, add the entry or drop the hash from the claim.
- Never write `verified` in the ledger without having run `sha256sum` in the
  same pass; otherwise use `unverified`.
