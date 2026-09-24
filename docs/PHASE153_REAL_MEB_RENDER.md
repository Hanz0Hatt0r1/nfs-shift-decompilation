# Phase 153: first real MEB render boundary

Phase 153 adds a thin integration adapter for the first end-to-end static
render from an original SHIFT archive:

    BFF -> XMem/LZX -> MEB -> neutral mesh -> reference_renderer -> PPM

Archive decompression remains in shift_importer.BFF, MEB semantics remain in
meb_format.read_meb, and rasterization remains in reference_renderer.

## BMW M3 command

    python bff_meb_render.py \
      BMW_M3_E36.bff \
      vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb \
      out/bmw_m3_e36_kit00_body_loda.ppm \
      --mesh-json out/bmw_m3_e36_kit00_body_loda.mesh.json

The default output is flat-gray geometry. This is deliberate: COLOR0/COLOR1
is still evidence-sensitive, so the first real render must not silently make
a byte-order or declaration choice.

To isolate one material primitive:

    python bff_meb_render.py \
      BMW_M3_E36.bff \
      vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb \
      out/bmw_m3_e36_paint.ppm \
      --primitive-index 1

The optional --vertex-colors mode is only a debug visualization of the parser's
current COLOR0 bytes; it does not change the project's ABI status.

## Provenance

The JSON report records the archive entry, compressed/uncompressed sizes,
decoded resource SHA-256, MEB summary, selected primitive, and deterministic
PPM SHA-256. This is enough to reproduce a render from the original archive
without embedding BFF contents in the renderer.

## Scope

This phase proves the real BFF-to-MEB-to-rasterizer boundary. It does not claim
final BMW paint shading, exact game camera, resolved COLOR0/1 ABI, full material
execution, or runtime D3D9 draw-instance correlation.
