#include "shift_recompiled_pcode_abi.h"

static uint32_t load_u32(const uint8_t bytes[4]) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void store_u32(uint32_t value, uint8_t bytes[4]) {
    for (unsigned index = 0; index < 4; ++index)
        bytes[index] = (uint8_t)(value >> (index * 8));
}

int rvi_0090e50d(RviPcodeContext *ctx) {
    uint8_t esp_bytes[4];
    if (!ctx || !ctx->read || !ctx->write || !ctx->fill ||
        ctx->read(ctx->opaque, "register", UINT64_C(0x10), 4,
                  esp_bytes) != 0)
        return -1;

    const uint32_t entry_esp = load_u32(esp_bytes);
    uint8_t stack[16];
    if (ctx->read(ctx->opaque, "ram", entry_esp, sizeof(stack), stack) != 0)
        return -1;

    const uint32_t return_address = load_u32(stack);
    const uint32_t destination = load_u32(stack + 4);
    const uint8_t value = (uint8_t)load_u32(stack + 8);
    const uint32_t size = load_u32(stack + 12);
    if (ctx->fill(ctx->opaque, "ram", destination, value, size) != 0)
        return -1;

    uint8_t result[4];
    store_u32(destination, result);
    if (ctx->write(ctx->opaque, "register", 0, sizeof(result), result) != 0)
        return -1;
    store_u32(entry_esp + 4, result);
    if (ctx->write(ctx->opaque, "register", UINT64_C(0x10), sizeof(result),
                   result) != 0)
        return -1;
    store_u32(return_address, result);
    return ctx->write(ctx->opaque, "register", UINT64_C(0x284), sizeof(result),
                      result);
}
