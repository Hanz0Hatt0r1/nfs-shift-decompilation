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

int rvi_00402000(RviPcodeContext *ctx) {
    return ctx->call(ctx->opaque, UINT64_C(0x00deadbeef));
}

int rvi_00403000(RviPcodeContext *ctx) {
    uint64_t output = 0;
    return ctx->userop(ctx->opaque, 7, NULL, NULL, 0, &output, 4);
}
