#include "shift_recompiled_pcode_abi.h"

/* Retail 0x00509e60 is a two-byte tail alias: JMP 0x00509e40. */
int rvi_00509e60(RviPcodeContext *ctx) {
    return ctx && ctx->call
               ? ctx->call(ctx->opaque, UINT64_C(0x00509e40))
               : -1;
}
