# Phase 340: raw DDS base-level parity

Phase 339 introduced optional raw level-0 D3D9 texture payload capture. Phase 340
makes that payload authoritative for compressed-resource identity.

## Raw comparison

`runtime_texture_content_parity.py` now accepts both existing PPM snapshots and
the new `texture_payload` records.

For a captured 2D texture with a level-0 raw payload, the comparator:

1. resolves the exact retail DDS entry from `BMW_M3_E36.bff`;
2. extracts the DDS level-0 compressed block payload;
3. reads the captured `texture_payload` binary;
4. requires exact byte equality and identical byte count.

For DXT1/DXT3/DXT5 this compares compressed block bytes, not a decoded RGB
representation.

## Lifetime rule

Pointer reuse is handled strictly. A payload candidate is eligible only when its
event occurred after the current texture object's latest `CreateTexture` event.
Older payloads from an earlier object lifetime are ignored.

## Strength of the result

A raw level-0 byte match proves the runtime surface payload equals the retail DDS
base level for that resource. It does not by itself prove equality of every DDS
mipmap level when those levels were not captured.

PPM RGB matching remains a secondary visual/content check. PPM still cannot prove
alpha because the capture format stores RGB only.

## Boundary

The phase still does not infer the source resource path from the pointer. The
mapping direction is always:

`BMT sampler -> expected retail DDS` + `draw-local runtime pointer` +
`ordered CreateTexture lifecycle` + `raw payload equality`.

