# Process 1 — `FUN_0074f560` collision-provider machine proof

## Result

PC-retail `SHIFT.exe` independently confirms the lower collision/world provider boundary that P1.2a was waiting on.

The verified executable is SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` (8,801,792 bytes, PE32 i386).

Inside `FUN_0074f560`:

```text
0x0074f566  cmp dword [0x00c133ac], 0
0x0074f5a1  mov ecx, dword [0x00c133ac]
0x0074f5e3  mov eax, dword [ecx]
0x0074f5eb  mov eax, dword [eax+0x1c0]
0x0074f600  call eax
```

This positively identifies the provider object/pointer domain as the global pointer at `0x00c133ac`, and the retail scene-query dispatch as virtual slot `+0x1c0` on that object. The physical class name is intentionally left unknown.

## 0x58-byte record provenance

The same function allocates the returned surface record from the retail ring:

```text
0x0074f579  mov esi, dword [0x00c1bbe8]
0x0074f584  imul esi, esi, 0x58
0x0074f587  add esi, dword [0x00c1bae0]
```

On the hit path it marks `record+0x44 = 1` and returns `esi`. `FUN_007b0710` reaches this lower path at `0x007b0c8e`, then projects the record back into the already-typed upper ABI, including contact height, normal, and `query+0x30 = returned_record`.

## P1.2a adjudication

P1.2a is now closed **as an explicit typed external provider boundary**:

- provider object/pointer domain: closed;
- exact indirect scene-query dispatch: closed;
- virtual slot: `+0x1c0`;
- provenance to the 0x58-byte surface record: closed;
- physical PhysX/engine class name: not claimed;
- implementation behind the virtual slot: still external;
- guessed track query: forbidden.

This is sufficient for Process 2 to preserve the collision provider as an explicit callback/interface rather than reopening the upper `FUN_007b0710` ABI.

## Remaining blocker

Only P1.2b remains: exhaustive classification of residual `FUN_00765c40` writes and side-effecting callees. Complete `FUN_00765c40` removal is still unauthorized and the external-provider count remains 7 until that audit closes.
