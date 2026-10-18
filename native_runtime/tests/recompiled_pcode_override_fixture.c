#include "shift_recompiled_pcode_abi.h"

int rvi_00685700(RviPcodeContext *ctx) {
    const uint8_t override[4] = {'O', 'V', 'R', 'D'};
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x20000),
                      sizeof(override), override);
}
