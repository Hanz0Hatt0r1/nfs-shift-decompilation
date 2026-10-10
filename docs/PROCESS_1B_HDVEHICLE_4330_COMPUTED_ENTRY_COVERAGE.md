# Process 1B — computed/loader exact-carrier entry coverage

This aggregate composes three already-proven ways runtime control flow could obtain or publish a code address without an ordinary direct call.

| Class | Bounded surface | Exact P1B carrier hits |
| --- | --- | ---: |
| canonical `CALL next` / `POP` EIP capture | 1 candidate | 0 |
| x87 `FSTENV/FNSTENV` saved-EIP extraction | 4 decoded sites, 2 real env saves | 0 |
| PE loader-published entry surfaces | entrypoint + 509 exports + TLS/load-config | 0 |

The sole canonical call/pop candidate derives `.secu` base `0x00d31000`, not a carrier pointer. The two real x87 environment saves never extract the saved instruction pointer. The PE entrypoint is not a carrier, none of 509 exports targets a carrier, TLS callback count is zero, and load-config is absent.

## Reproduce

```bash
python3 tools/ghidra/build_p1b_hdvehicle_4330_computed_entry_coverage.py \
  evidence/p1b_hdvehicle_4330_canonical_eip_capture_surface.json \
  evidence/p1b_hdvehicle_4330_x87_eip_capture_surface.json \
  evidence/p1b_hdvehicle_4330_pe_loader_entry_surface.json \
  --output evidence/p1b_hdvehicle_4330_computed_entry_coverage.json
```

The builder fails closed if any upstream format/readiness/provider state changes, if canonical call/pop begins deriving an exact carrier, if x87 saved-EIP extraction appears, or if PE entry/export/TLS surfaces gain an exact carrier.

## Gate discipline

This is not a complete runtime-computed-pointer closure. It leaves open noncanonical non-x87 address synthesis, transformed constants, runtime copied/encoded pointers, runtime patching and opaque indirect dispatch.

```text
bounded computed/loader entry coverage composed = true
bounded exact-carrier hit = false
canonical call/pop surface complete = true
x87 saved-EIP surface complete = true
PE loader-published entry surface complete = true

noncanonical non-x87 EIP/address synthesis complete = false
runtime computed carrier pointers ruled out = false
runtime copied/encoded carrier pointers ruled out = false
generic function-pointer stores/copies ruled out = false
runtime callback registration ruled out = false
indirect entry into carriers ruled out = false
manager+0x374 identity join complete = false
final 0x004b86cf rejection = false
P1.3 complete = false
provider count = 7
```
