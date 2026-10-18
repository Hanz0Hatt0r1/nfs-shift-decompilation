#include "shift_recompiled_pcode_abi.h"

int rvi_00685700(RviPcodeContext *ctx) {
    const uint8_t value[4] = {0xd0, 0x99, 0xaa, 0x00};
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x20000), sizeof(value),
                      value);
}

int rvi_00401000(RviPcodeContext *ctx) {
    const uint8_t eax[4] = {0x34, 0x12, 0x00, 0x00};
    if (ctx->write(ctx->opaque, "register", 0, sizeof(eax), eax) != 0) {
        return -1;
    }
    return ctx->call(ctx->opaque, UINT64_C(0x00685700));
}

int rvi_00404000(RviPcodeContext *ctx) {
    uint8_t value[4] = {0};
    const uint8_t expected[4] = {'P', '3', '2', '!'};
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x00401000), sizeof(value),
                  value) != 0) {
        return -1;
    }
    if (value[0] != expected[0] || value[1] != expected[1] ||
        value[2] != expected[2] || value[3] != expected[3]) {
        return -2;
    }
    return ctx->call(ctx->opaque, UINT64_C(0x00685700));
}

int rvi_00405000(RviPcodeContext *ctx) {
    uint8_t iat[4] = {0};
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x00402080), sizeof(iat),
                  iat) != 0) {
        return -1;
    }
    const uint32_t target = (uint32_t)iat[0] | ((uint32_t)iat[1] << 8) |
                           ((uint32_t)iat[2] << 16) |
                           ((uint32_t)iat[3] << 24);
    return ctx->call(ctx->opaque, target);
}

int rvi_00406000(RviPcodeContext *ctx) {
    const uint32_t stack_top = UINT32_C(0x00030020);
    const uint32_t esp = stack_top - 8;
    const uint32_t output_address = UINT32_C(0x00030100);
    const uint32_t return_address = UINT32_C(0x00406005);
    uint8_t bytes[8] = {0};
    if (ctx->write(ctx->opaque, "ram", stack_top - 4, 4,
                   (const uint8_t *)&output_address) != 0 ||
        ctx->write(ctx->opaque, "ram", esp, 4,
                   (const uint8_t *)&return_address) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x10), 4,
                   (const uint8_t *)&esp) != 0) {
        return -1;
    }
    uint8_t iat[4] = {0};
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x00402088), sizeof(iat),
                  iat) != 0) {
        return -2;
    }
    const uint32_t target = (uint32_t)iat[0] | ((uint32_t)iat[1] << 8) |
                           ((uint32_t)iat[2] << 16) |
                           ((uint32_t)iat[3] << 24);
    if (ctx->call(ctx->opaque, target) != 0) return -3;
    uint8_t restored_esp[4] = {0};
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x10),
                  sizeof(restored_esp), restored_esp) != 0 ||
        restored_esp[0] != (uint8_t)stack_top ||
        restored_esp[1] != (uint8_t)(stack_top >> 8) ||
        restored_esp[2] != (uint8_t)(stack_top >> 16) ||
        restored_esp[3] != (uint8_t)(stack_top >> 24)) {
        return -4;
    }
    if (ctx->read(ctx->opaque, "ram", output_address, sizeof(bytes), bytes) !=
        0) {
        return -5;
    }
    for (size_t index = 0; index < sizeof(bytes); ++index) {
        if (bytes[index] != 0) return 0;
    }
    return -6;
}

int rvi_00407000(RviPcodeContext *ctx) {
    const uint32_t stack_top = UINT32_C(0x00030040);
    const uint32_t esp = stack_top - 4;
    const uint32_t null_pointer = 0;
    const uint32_t return_address = UINT32_C(0x00407005);
    uint8_t iat[4] = {0};
    if (ctx->write(ctx->opaque, "ram", stack_top, 4,
                   (const uint8_t *)&null_pointer) != 0 ||
        ctx->write(ctx->opaque, "ram", esp, 4,
                   (const uint8_t *)&return_address) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x10), 4,
                   (const uint8_t *)&esp) != 0 ||
        ctx->read(ctx->opaque, "ram", UINT64_C(0x00402088), sizeof(iat),
                  iat) != 0) {
        return -1;
    }
    const uint32_t target = (uint32_t)iat[0] | ((uint32_t)iat[1] << 8) |
                           ((uint32_t)iat[2] << 16) |
                           ((uint32_t)iat[3] << 24);
    return ctx->call(ctx->opaque, target);
}

int rvi_00402000(RviPcodeContext *ctx) {
    return ctx->call(ctx->opaque, UINT64_C(0x00deadbeef));
}

int rvi_00403000(RviPcodeContext *ctx) {
    uint64_t output = 0;
    return ctx->userop(ctx->opaque, 7, NULL, NULL, 0, &output, 4);
}
