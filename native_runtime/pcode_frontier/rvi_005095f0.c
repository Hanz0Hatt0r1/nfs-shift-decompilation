/* Ghidra-lowered retail block 0x005095f0 (12 instructions). */
#include <stdint.h>
#include <stddef.h>

typedef int (*RviReadBytes)(void *, const char *, uint64_t, size_t, uint8_t *);
typedef int (*RviWriteBytes)(void *, const char *, uint64_t, size_t,
                             const uint8_t *);
typedef int (*RviCallFunction)(void *, uint64_t);
typedef struct {
    void *opaque;
    RviReadBytes read;
    RviWriteBytes write;
    RviCallFunction call;
} RviPcodeContext;

static uint32_t rvi_load_u32(const uint8_t bytes[4]) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void rvi_store_u32(uint32_t value, uint8_t bytes[4]) {
    for (unsigned i = 0; i < 4; ++i) bytes[i] = (uint8_t)(value >> (i * 8));
}

static int rvi_read_u32(RviPcodeContext *ctx, const char *space,
                        uint64_t address, uint32_t *value) {
    uint8_t bytes[4];
    if (!ctx || !ctx->read || ctx->read(ctx->opaque, space, address, 4, bytes))
        return -1;
    *value = rvi_load_u32(bytes);
    return 0;
}

static int rvi_write_u32(RviPcodeContext *ctx, const char *space,
                         uint64_t address, uint32_t value) {
    uint8_t bytes[4];
    rvi_store_u32(value, bytes);
    return !ctx || !ctx->write ||
                   ctx->write(ctx->opaque, space, address, 4, bytes)
               ? -1
               : 0;
}

static int rvi_call_at(RviPcodeContext *ctx, uint32_t target,
                       uint32_t return_address) {
    uint32_t esp;
    if (rvi_read_u32(ctx, "register", 0x10, &esp) || esp < 4 ||
        rvi_write_u32(ctx, "ram", esp - 4, return_address) ||
        rvi_write_u32(ctx, "register", 0x10, esp - 4) || !ctx->call ||
        ctx->call(ctx->opaque, target))
        return -1;
    return 0;
}

int rvi_005095f0(RviPcodeContext *ctx) {
    uint32_t ebx, esi;
    uint8_t owner_flag;
    if (rvi_read_u32(ctx, "register", 0x0c, &ebx) ||
        rvi_read_u32(ctx, "register", 0x18, &esi) || !ctx->read ||
        ctx->read(ctx->opaque, "ram", (uint32_t)(ebx + 0xad), 1,
                  &owner_flag) != 0 ||
        rvi_write_u32(ctx, "register", 0x04, esi) != 0)
        return -1;

    if (owner_flag != 0) {
        if (rvi_call_at(ctx, 0x00508970, 0x00509610) != 0) return -1;
    } else {
        if (rvi_call_at(ctx, 0x005088e0, 0x00509600) != 0 ||
            rvi_read_u32(ctx, "register", 0x18, &esi) != 0)
            return -1;
        uint32_t state;
        if (rvi_read_u32(ctx, "ram", (uint32_t)(esi + 0xe4), &state) != 0)
            return -1;
        if (state == 1) {
            if (rvi_write_u32(ctx, "register", 0x04, esi) != 0 ||
                rvi_call_at(ctx, 0x00508970, 0x00509610) != 0)
                return -1;
        } else {
            uint8_t active;
            uint32_t ebp;
            if (!ctx->read(ctx->opaque, "ram", (uint32_t)(esi + 0xed), 1,
                           &active)) {
                if (active != 0 &&
                    (rvi_read_u32(ctx, "register", 0x14, &ebp) != 0 ||
                     ebp < 2 ||
                     ctx->write(ctx->opaque, "ram", ebp - 2, 1,
                                (const uint8_t[]){1}) != 0))
                    return -1;
            } else {
                return -1;
            }
        }
    }

    return ctx->call && ctx->call(ctx->opaque, 0x00509588) == 0 ? 0 : -1;
}
