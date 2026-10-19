#include "shift_recompiled_pcode_abi.h"

static int read_u32(RviPcodeContext *ctx, const char *space, uint64_t address,
                    uint32_t *value) {
    uint8_t bytes[4];
    if (ctx->read(ctx->opaque, space, address, sizeof(bytes), bytes) != 0)
        return -1;
    *value = (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
             ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
    return 0;
}

int rvi_005f1830(RviPcodeContext *ctx) {
    uint32_t receiver = 0;
    uint32_t vtable = 0;
    uint32_t target = 0;
    if (!ctx || !ctx->read || !ctx->write || !ctx->call ||
        read_u32(ctx, "register", 4, &receiver) != 0 ||
        read_u32(ctx, "ram", receiver, &vtable) != 0 ||
        vtable > UINT32_MAX - 8 ||
        read_u32(ctx, "ram", (uint64_t)vtable + 8, &target) != 0) {
        return -1;
    }

    const uint8_t eax[4] = {
        (uint8_t)vtable, (uint8_t)(vtable >> 8), (uint8_t)(vtable >> 16),
        (uint8_t)(vtable >> 24)};
    if (ctx->write(ctx->opaque, "register", 0, sizeof(eax), eax) != 0)
        return -1;
    return ctx->call(ctx->opaque, target);
}
