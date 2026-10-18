#include "shift_recompiled_pcode_abi.h"

int rvi_00401020(RviPcodeContext *ctx) {
    const uint8_t expected_esp[4] = {0x00, 0xf0, 0xfd, 0x7f};
    const uint8_t expected_return_address[4] = {0};
    const uint8_t marker[4] = {'S', 'U', 'P', 'P'};
    uint8_t esp[4] = {0};
    uint8_t return_address[4] = {0xff, 0xff, 0xff, 0xff};
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x10), sizeof(esp),
                  esp) != 0 ||
        ctx->read(ctx->opaque, "ram", UINT64_C(0x7ffdf000),
                  sizeof(return_address), return_address) != 0) {
        return -1;
    }
    if (esp[0] != expected_esp[0] || esp[1] != expected_esp[1] ||
        esp[2] != expected_esp[2] || esp[3] != expected_esp[3] ||
        return_address[0] != expected_return_address[0] ||
        return_address[1] != expected_return_address[1] ||
        return_address[2] != expected_return_address[2] ||
        return_address[3] != expected_return_address[3]) {
        return -2;
    }
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x32c00), sizeof(marker),
                      marker);
}
