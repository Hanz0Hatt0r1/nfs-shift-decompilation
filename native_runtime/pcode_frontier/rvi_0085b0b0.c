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

static int write_u32(RviPcodeContext *ctx, const char *space, uint64_t address,
                     uint32_t value) {
    const uint8_t bytes[4] = {
        (uint8_t)value, (uint8_t)(value >> 8), (uint8_t)(value >> 16),
        (uint8_t)(value >> 24)};
    return ctx->write(ctx->opaque, space, address, sizeof(bytes), bytes);
}

int rvi_0085b0b0(RviPcodeContext *ctx) {
    uint32_t receiver, eax, esp, return_address;
    uint8_t value;
    if (!ctx || !ctx->read || !ctx->write ||
        read_u32(ctx, "register", 0x04, &receiver) != 0 ||
        read_u32(ctx, "register", 0x00, &eax) != 0 ||
        read_u32(ctx, "register", 0x10, &esp) != 0 ||
        ctx->read(ctx->opaque, "ram", (uint32_t)(receiver + 0x32f), 1,
                  &value) != 0 ||
        read_u32(ctx, "ram", esp, &return_address) != 0)
        return -1;

    eax = (eax & UINT32_C(0xffffff00)) | value;
    return write_u32(ctx, "register", 0x00, eax) != 0 ||
                   write_u32(ctx, "register", 0x10, esp + 4) != 0 ||
                   write_u32(ctx, "register", 0x284, return_address) != 0
               ? -1
               : 0;
}
