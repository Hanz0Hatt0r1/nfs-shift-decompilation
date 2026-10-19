#include "shift_recompiled_pcode_abi.h"

static uint32_t fixture_load_u32(const uint8_t bytes[4]) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void fixture_store_u32(uint32_t value, uint8_t bytes[4]) {
    for (unsigned i = 0; i < 4; ++i) bytes[i] = (uint8_t)(value >> (i * 8));
}

static int fixture_return_cleanup(RviPcodeContext *ctx, uint32_t cleanup) {
    uint8_t esp_bytes[4], return_bytes[4], next_esp_bytes[4];
    uint8_t next_eip_bytes[4];
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x10), 4, esp_bytes) != 0)
        return -1;
    const uint32_t esp = fixture_load_u32(esp_bytes);
    if (ctx->read(ctx->opaque, "ram", esp, 4, return_bytes) != 0) return -1;
    fixture_store_u32(esp + 4 + cleanup, next_esp_bytes);
    fixture_store_u32(fixture_load_u32(return_bytes), next_eip_bytes);
    return ctx->write(ctx->opaque, "register", UINT64_C(0x10), 4,
                      next_esp_bytes) != 0 ||
                   ctx->write(ctx->opaque, "register", UINT64_C(0x284), 4,
                              next_eip_bytes) != 0
               ? -1
               : 0;
}

static int fixture_return(RviPcodeContext *ctx) {
    return fixture_return_cleanup(ctx, 0);
}

static int fixture_record_call_cleanup(RviPcodeContext *ctx, uint32_t id,
                                       uint32_t cleanup) {
    uint8_t count_bytes[4], ecx_bytes[4];
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x20180), 4, count_bytes) != 0 ||
        ctx->read(ctx->opaque, "register", UINT64_C(0x04), 4, ecx_bytes) != 0)
        return -1;
    const uint32_t count = fixture_load_u32(count_bytes);
    fixture_store_u32(id, count_bytes);
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x20184) + count * 4, 4,
                   count_bytes) != 0 ||
        ctx->write(ctx->opaque, "ram", UINT64_C(0x20200) + count * 4, 4,
                   ecx_bytes) != 0)
        return -1;
    fixture_store_u32(count + 1, count_bytes);
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x20180), 4,
                      count_bytes) != 0
               ? -1
               : fixture_return_cleanup(ctx, cleanup);
}

static int fixture_record_call(RviPcodeContext *ctx, uint32_t id) {
    return fixture_record_call_cleanup(ctx, id, 0);
}

int rvi_00631740(RviPcodeContext *ctx) {
    return fixture_record_call_cleanup(ctx, 1, 4);
}

int rvi_00507f80(RviPcodeContext *ctx) {
    return fixture_record_call(ctx, 2);
}

int rvi_00507340(RviPcodeContext *ctx) {
    return fixture_record_call_cleanup(ctx, 3, 4);
}

int rvi_0040e630(RviPcodeContext *ctx) {
    return fixture_record_call(ctx, 5);
}

int rvi_0040e390(RviPcodeContext *ctx) {
    return fixture_record_call(ctx, 6);
}

int rvi_004277a0(RviPcodeContext *ctx) {
    return fixture_record_call(ctx, 7);
}

int rvi_0040b870(RviPcodeContext *ctx) {
    uint8_t result[4];
    if (fixture_record_call(ctx, 4) != 0 ||
        ctx->read(ctx->opaque, "ram", UINT64_C(0x00bbf960), 4, result) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x00), 4, result) != 0)
        return -1;
    return 0;
}

int rvi_005088e0(RviPcodeContext *ctx) {
    const uint32_t called = 1;
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x20160), sizeof(called),
                   (const uint8_t *)&called) != 0)
        return -1;
    return fixture_return(ctx);
}

int rvi_00508970(RviPcodeContext *ctx) {
    uint8_t ecx_bytes[4];
    const uint32_t called = 1;
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x04), 4, ecx_bytes) != 0 ||
        ctx->write(ctx->opaque, "ram", UINT64_C(0x20164), sizeof(called),
                   (const uint8_t *)&called) != 0 ||
        ctx->write(ctx->opaque, "ram", UINT64_C(0x20168), sizeof(ecx_bytes),
                   ecx_bytes) != 0)
        return -1;
    return fixture_return(ctx);
}

int rvi_00509588(RviPcodeContext *ctx) {
    uint8_t ecx_bytes[4], esp_bytes[4];
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x04), 4, ecx_bytes) != 0 ||
        ctx->read(ctx->opaque, "register", UINT64_C(0x10), 4, esp_bytes) != 0 ||
        ctx->write(ctx->opaque, "ram", UINT64_C(0x20170), sizeof(ecx_bytes),
                   ecx_bytes) != 0 ||
        ctx->write(ctx->opaque, "ram", UINT64_C(0x20174), sizeof(esp_bytes),
                   esp_bytes) != 0)
        return -1;
    return 0;
}

int rvi_005089c0(RviPcodeContext *ctx) {
    uint8_t esp_bytes[4] = {0};
    uint8_t return_bytes[4] = {0};
    uint8_t next_esp_bytes[4] = {0};
    uint8_t next_eip_bytes[4] = {0};
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x10), 4,
                  esp_bytes) != 0) {
        return -1;
    }
    const uint32_t esp = (uint32_t)esp_bytes[0] |
                         ((uint32_t)esp_bytes[1] << 8) |
                         ((uint32_t)esp_bytes[2] << 16) |
                         ((uint32_t)esp_bytes[3] << 24);
    if (ctx->read(ctx->opaque, "ram", esp, 4, return_bytes) != 0) {
        return -1;
    }
    const uint32_t return_address = (uint32_t)return_bytes[0] |
                                    ((uint32_t)return_bytes[1] << 8) |
                                    ((uint32_t)return_bytes[2] << 16) |
                                    ((uint32_t)return_bytes[3] << 24);
    const uint32_t next_esp = esp + 4;
    for (unsigned i = 0; i < 4; ++i) {
        next_esp_bytes[i] = (uint8_t)(next_esp >> (i * 8));
        next_eip_bytes[i] = (uint8_t)(return_address >> (i * 8));
    }
    if (ctx->write(ctx->opaque, "register", UINT64_C(0x10), 4,
                   next_esp_bytes) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x284), 4,
                   next_eip_bytes) != 0) {
        return -1;
    }
    return 0;
}

int rvi_0050958c(RviPcodeContext *ctx) {
    uint8_t ecx[4] = {0};
    uint8_t esi[4] = {0};
    uint8_t esp[4] = {0};
    uint8_t record[12] = {0};
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x4), 4, ecx) != 0 ||
        ctx->read(ctx->opaque, "register", UINT64_C(0x18), 4, esi) != 0 ||
        ctx->read(ctx->opaque, "register", UINT64_C(0x10), 4, esp) != 0) {
        return -1;
    }
    for (unsigned i = 0; i < 4; ++i) {
        record[i] = ecx[i];
        record[4 + i] = esi[i];
        record[8 + i] = esp[i];
    }
    const uint8_t clobbered_edi[4] = {0xef, 0xbe, 0xad, 0xde};
    const uint8_t continuation_result[4] = {3, 0, 0, 0};
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x20150), sizeof(record),
                   record) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x1c),
                   sizeof(clobbered_edi), clobbered_edi) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x00),
                   sizeof(continuation_result), continuation_result) != 0) {
        return -1;
    }
    return 0;
}
