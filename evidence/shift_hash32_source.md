# SHIFT 32-bit string/byte hash: FUN_0063ad50

This note records the source/PE reconstruction of the retail 32-bit hash used
by `TrackDetails` and other runtime systems.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function identity

- recovered function: `FUN_0063ad50`
- PE address: `0x0063ad50`
- initial A/B constant: `0x9e3779b9`
- block width: 12 bytes
- output width: 32 bits

The function receives an explicit byte length, seed, and a flag controlling
whether an uppercase normalization copy is made before hashing.

## PE byte semantics

The retail PE is important because the decompiler's `char *` type alone does
not establish signedness. The hash body uses `MOVSX` for every input-byte
load, including full 12-byte blocks and the tail switch. Therefore bytes
`0x80..0xff` are sign-extended before accumulation.

Four-byte groups are accumulated in source order by repeated
`value = value * 256 + signed_byte`, i.e. a big-endian-style accumulation,
not little-endian word loading.

All arithmetic wraps at 32 bits. After every block the state executes the
recovered nine-step subtract/xor/shift mix. The original total byte length is
added to the third accumulator before the final tail mix.

## Case-normalization flag

When the final flag is zero, retail code:

1. copies at most `0xff` bytes into a 256-byte stack buffer;
2. calls CRT `strupr_s`;
3. hashes that temporary buffer.

That branch is code-page/locale dependent for non-ASCII input. The recovered
runtime therefore provides exact raw-byte parity for the case-sensitive path
and an ASCII-only convenience wrapper for uppercase mode; it does not claim
non-ASCII CRT locale parity.

The `TrackDetails` load path first lowercases and slash-normalizes its source
path itself and then calls `FUN_0063ad50(..., seed=0, flag=1)`, so its numeric
hash does not depend on this uppercase branch.

## Frozen vectors

The Python implementation is checked against a literal 32-bit C transliteration
of the recovered source/PE operation order.

| Input bytes | Seed | Hash |
|---|---:|---:|
| empty | `0` | `0xbd49d10d` |
| `a` | `0` | `0x29eec818` |
| `trackdetails` | `0` | `0x0c1f0c8b` |
| `tracks\\silverstone\\era3.trd` | `0` | `0x0a1a5c1e` |
| `tracks\\brands\\brands.trd` | `0` | `0x8be38aaa` |
| `abcdefghijkl` | `0` | `0xf7cd38dd` |
| `abcdefghijklm` | `0` | `0x2d60a941` |
| bytes `80 ff 41` | `0` | `0xadd9bf77` |
| `abc` | `0x12345678` | `0x4648dcca` |

The 12/13-byte vectors freeze the block transition; the high-byte vector freezes
the PE-proven signed-byte behavior.

## Runtime implementation

`src/core/shift_hash_runtime.py` exposes:

- `shift_hash32(bytes, seed)` for exact case-sensitive raw-byte parity;
- `shift_hash32_ascii(..., case_sensitive=False)` for the ASCII subset of the
  retail uppercase branch;
- a machine-readable report describing the signed-byte and locale boundary.

`src/track/track_details_load_runtime.py` now uses this implementation to
produce the numeric hash stored at `TrackDetails+0x120` for ASCII source
paths.

## Boundary

No claim is made that the optional uppercase branch has byte-for-byte parity
for non-ASCII strings under every Windows CRT locale/code page. That behavior
remains outside the portable runtime contract.
