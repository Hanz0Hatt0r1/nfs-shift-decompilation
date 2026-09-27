# Phase 380 — vehicle rate/response runtime

This phase reconstructs FUN_0075ada0, FUN_007595d0 and FUN_007682c0 using the
supplied decompiler output plus the retail machine code.

The machine code resolves a decompiler loss in FUN_007682c0: its initial square
root is over the three body velocity doubles at +0x78, +0x80 and +0x88.

FUN_0075ada0 normalizes the X/Z velocity when speed >= 4, forms
direction x (0,1,0), projects it against fields +0x4084/+0x408c, and returns
the visible radius/reciprocal pair.

FUN_007595d0 applies the signed steering-angle response. FUN_007682c0 gates on
speed >= 5, computes (speed-5)/15, selects the 40-degree or 55-degree limit from
DAT_00c128cc, calls FUN_007595d0, multiplies the result by its caller scalar and
adds only to body accumulator +0x50.

Physical field names and units remain unresolved.
