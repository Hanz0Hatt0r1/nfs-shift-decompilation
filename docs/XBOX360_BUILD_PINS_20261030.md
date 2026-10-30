# Xbox 360 build pins — 2026-10-30

Scope: this document pins what produced the Linux x86-64 ReXGlue host
artifacts used by the Xbox 360 SHIFT retail runs, and states the rule that
makes those pins usable as evidence. The machine-readable form is
[`tools/xbox360/build/pins.json`](../tools/xbox360/build/pins.json); the verifier
is [`tools/xbox360/build/verify_pins.py`](../tools/xbox360/build/verify_pins.py);
the full recipe is [`tools/xbox360/build/README.md`](../tools/xbox360/build/README.md).

## Why this exists

An audit of the run tree on 2026-10-30 found the anti-pattern this task targets:

- 96 distinct run directories under `/home/pes/work/nfs-shift-p1-*` load a
  plugin with the **same** SHA-256 and nothing in the repository said which
  source or which SDK commit produced it.
- 344 plugin copies exist across the local trees.
- For `librexgpu-xenos.so` alone, 10 distinct hashes were observed; the most
  common one (`19053b69…`) appears 32 times, while the pinned one (`8b5abe7a…`)
  appears in the runs being cited as evidence.
- No tracked build recipe existed at all.

A hash with no recorded producer is not evidence: it cannot be re-derived and
cannot be checked. The ledger closes that gap.

## What was pinned

Every value below was recomputed with `sha256sum` on this host during this
pass. Status values follow the ledger vocabulary: `verified` means recomputed
and matched here; `unverified` means the value is recorded but was **not**
re-established in this pass; `unavailable` means the file is absent locally.

| Artifact | Class | SHA-256 | Status |
| --- | --- | --- | --- |
| `librexruntime.so` | runtime | `693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd` | verified |
| `nfs_shift` | host executable | `ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178` | verified |
| `librexgpu-shift-native.so` | Native Vulkan plugin | `fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490` | verified |
| `librexgpu-xenos.so` | Xenos plugin | `8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de` | verified |
| `default.xex` | retail dump (outside Git) | `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58` | **unverified** |

The retail XEX hash is deliberately marked `unverified`: the dump is user-owned
and kept outside Git, and it was not re-hashed at a known local path in this
pass. The recorded value comes from
[`evidence/xbox360_rexglue_preflight_20261022.md`](../evidence/xbox360_rexglue_preflight_20261022.md).
Title ID `454108B4`, Media ID `60DAC9C5`. Re-hash the dump before citing it as
verified.

### How each was verified

```sh
sha256sum /home/pes/work/nfs-shift-p1-v100-native-same-script-20261029/bin/librexruntime.so
sha256sum /home/pes/work/nfs-shift-p1-v100-native-same-script-20261029/bin/nfs_shift
sha256sum /home/pes/work/nfs-shift-p1-native-predicate-after-p2-pr2161-v73-20261029/bin/librexgpu-shift-native.so
sha256sum /home/pes/work/nfs-shift-p1-action-consumer-v96-v262-xenos-20261029/bin/librexgpu-xenos.so
sha256sum /home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-xenos-20261029/bin/librexgpu-xenos.so
```

The second xenos sample is the check that the pinned xenos hash is stable
across independent run directories, not an artifact of one staged copy.

Provenance of the native plugin was confirmed by three independent facts, not
one: the run directory's `run_metadata.json` records
`plugin_path = /home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/linux-amd64/librexgpu-shift-native.so`
with the matching `plugin_sha256`, and that file on disk hashes identically.

## Recovered build configuration

Recovered from the build trees that produced the pinned artifacts:

- Generator **Ninja Multi-Config**; `/usr/bin/cmake`; `CMAKE_BUILD_TYPE=Release`.
- `clang` / `clang++` (`/usr/bin/clang`, `/usr/bin/clang++`).
- `CMAKE_CXX_FLAGS = -march=x86-64-v2`.
- `REXGLUE_USE_VULKAN=ON`, `REXGLUE_USE_D3D12=OFF`, `REXGLUE_BUILD_TESTS=OFF`,
  `REXGLUE_ENABLE_SANITIZERS=OFF`, `REXGLUE_ENABLE_TRACY=ON`,
  `REXGLUE_ENABLE_PERF_COUNTERS=ON`, `REXGLUE_ENABLE_FIDELITYFX=OFF`.
- `SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME=500`,
  `SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON=OFF`.
- Vulkan headers and glslang are vendored in the SDK (`thirdparty/`); no system
  Vulkan SDK is needed for the Linux host build.
- Recovered TU flags (glslang thirdparty TU from
  `compile_commands.json`): `-march=x86-64-v2 -O3 -DNDEBUG -fPIC -mcmodel=large
  -fno-strict-aliasing -ffp-model=strict -fno-char8_t -fno-exceptions`.

`-ffp-model=strict`, `-mcmodel=large` and `-fno-exceptions` are load-bearing:
the guest PPC→C++ lowering assumes strict floating-point semantics. A rebuild
that drops them is not the pinned artifact even when it links and runs.

## Known divergence: two SDK trees

This is the most important honest finding of the pass, and the ledger states it
instead of smoothing it over.

- The recorded integration target is the fork
  `https://github.com/Hanz0Hatt0r1/rexglue-sdk`, local clone
  `/home/pes/work/rexglue-sdk-xbox360-memory-lifecycle-20261025`, HEAD
  abbreviation `32afce4` ("fix(input): route retail keyboard keystrokes"),
  stacked on `58e4d4b`, `ede359f`, `097e9f1`, `fb151b9`, `b3648b0`, over release
  `c94f5eb` (tag `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`).
- **The pinned native plugin was produced by a different tree**:
  `/home/pes/work/rexglue-sdk-rexui-vulkan-20261023` at
  `b3648b013b02770fa5ca8d4618235b2326c911ca`, which is an ancestor of the fork
  HEAD, not the fork HEAD itself. That commit is `verified` in the ledger.
- The pinned `librexruntime.so` cannot be attributed to either tree: the rexui
  tree ships a *fourth* runtime hash (`be70fe8e…`), which is not the pinned one.
  The runtime entry therefore records `built_from_commit: unverified`.
- `librexgpu-xenos.so` hashes identically to a locally renamed build copy
  (`librexgpu-xenos-pm4-trace.so` in
  `nfs-shift-p1-v86-xenos-dispatch-join-20261028/runtime-build/`), so its source
  commit cannot be inferred from the hash; it stays `unverified`.
- Only the short id `32afce4` was captured for the fork HEAD, so
  `sdk.fork_commit_full` is `null` and `sdk.fork_commit_status` is `unverified`.
  Filling it in needs `git -C <clone> rev-parse HEAD`.

Consequence: rebuilding at fork HEAD will **not** byte-reproduce the pinned
runtime or plugin. Reconciling all four artifacts onto one recorded SDK commit
is open work, tracked here as an unresolved divergence rather than a solved
problem.

## Verifying

```sh
python3 tools/xbox360/build/verify_pins.py           # human readable, exit 0/1/2
python3 tools/xbox360/build/verify_pins.py --json    # machine readable
python3 tools/xbox360/build/verify_pins.py --explain plugin_native_vulkan
python3 tools/xbox360/build/verify_pins.py --search-root /home/pes/work --require runtime
```

Behaviour, as tested by [`tools/xbox360/test_build_pins.py`](../tools/xbox360/test_build_pins.py):

- A located artifact whose SHA-256 differs from the pin produces `mismatch`,
  a non-zero exit and a loud `FAIL` line. This is the primary contract.
- A missing artifact is reported `unavailable` and does **not** fail the run,
  so the ledger is verifiable on a machine that has never built the project.
  `--require name` is how CI turns a specific artifact into a hard requirement.
- A structurally invalid ledger (unknown status, short or uppercase digest,
  missing required key) exits `2` rather than silently passing.
- `--json` emits the per-artifact observed and pinned digests, so a CI job can
  gate on exact values.
- Pins that are asserted but not proven appear under `unverified_pins` in every
  run, so an `unverified` never hides behind an overall `PASS`.

Current result on this host: 4 artifacts checked, 4 matched, 0 mismatched,
0 unavailable, with five entries explicitly listed as unverified
(`sdk.fork_commit`, the producer commits for runtime/host/xenos, and the XEX).

## Rule

> **Any evidence citing a plugin or runtime hash must be reproducible from a
> `pins.json` entry.**

Operationally:

1. Quote a hash in a document or evidence JSON only if that hash appears in
   `tools/xbox360/build/pins.json` with `status: verified`, or the entry records
   the producer commit that makes it re-derivable.
2. If the hash is not in the ledger, either add it with a resolved producer
   commit, or mark it explicitly `unverified` next to the claim. Do not present
   an unlabelled hash as though it identifies a build.
3. Run directory `run_metadata.json` files remain the local record, but they are
   not evidence on their own: they were exactly the source of the 96-dirs-one-hash
   confusion. The ledger plus `verify_pins.py` is the tracked answer.
4. Never write `verified` without running `sha256sum` in the same pass.
   Never commit build outputs, SDK copies, XEX bytes or dumps — only hashes,
   commits and the recipe are tracked.
