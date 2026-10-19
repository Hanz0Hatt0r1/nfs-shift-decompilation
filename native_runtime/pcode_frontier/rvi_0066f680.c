#include "shift_recompiled_pcode_abi.h"
#include "shift_lzx.h"

#include <stdlib.h>

enum {
    MAX_COMPRESSED_INPUT = 16 * 1024 * 1024,
    MAX_DECODED_OUTPUT = 64 * 1024 * 1024,
    GUEST_IO_CHUNK = 16,
};

static int read_bytes(RviPcodeContext *ctx, uint64_t address, size_t size,
                      uint8_t *output) {
    for (size_t offset = 0; offset < size; offset += GUEST_IO_CHUNK) {
        const size_t chunk = size - offset < GUEST_IO_CHUNK
                                 ? size - offset
                                 : GUEST_IO_CHUNK;
        if (ctx->read(ctx->opaque, "ram", address + offset, chunk,
                      output + offset) != 0)
            return -1;
    }
    return 0;
}

static int write_bytes(RviPcodeContext *ctx, uint64_t address, size_t size,
                       const uint8_t *input) {
    for (size_t offset = 0; offset < size; offset += GUEST_IO_CHUNK) {
        const size_t chunk = size - offset < GUEST_IO_CHUNK
                                 ? size - offset
                                 : GUEST_IO_CHUNK;
        if (ctx->write(ctx->opaque, "ram", address + offset, chunk,
                       input + offset) != 0)
            return -1;
    }
    return 0;
}

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

int rvi_0066f680(RviPcodeContext *ctx) {
    uint32_t esp, return_address, receiver, context, output, output_size_ptr;
    uint32_t input, input_size;
    if (!ctx || !ctx->read || !ctx->write ||
        read_u32(ctx, "register", 0x10, &esp) != 0 ||
        esp > UINT32_MAX - 24 ||
        read_u32(ctx, "ram", esp, &return_address) != 0 ||
        read_u32(ctx, "register", 0x04, &receiver) != 0 ||
        read_u32(ctx, "ram", (uint64_t)esp + 4, &context) != 0 ||
        read_u32(ctx, "ram", (uint64_t)esp + 8, &output) != 0 ||
        read_u32(ctx, "ram", (uint64_t)esp + 12, &output_size_ptr) != 0 ||
        read_u32(ctx, "ram", (uint64_t)esp + 16, &input) != 0 ||
        read_u32(ctx, "ram", (uint64_t)esp + 20, &input_size) != 0 ||
        context != receiver || output == 0 || output_size_ptr == 0 || input == 0 ||
        input_size == 0 || input_size > MAX_COMPRESSED_INPUT ||
        (uint64_t)input + input_size > (uint64_t)UINT32_MAX + 1)
        return -1;

    uint8_t *packed = (uint8_t *)malloc(input_size);
    if (!packed) return -1;
    if (read_bytes(ctx, input, input_size, packed) != 0) {
        free(packed);
        return -1;
    }

    size_t decoded_size = 0;
    if (shift_xmem_decompressed_size(packed, input_size, &decoded_size) != 0 ||
        decoded_size > MAX_DECODED_OUTPUT ||
        (uint64_t)output + decoded_size > (uint64_t)UINT32_MAX + 1) {
        free(packed);
        return -1;
    }
    uint8_t *decoded = (uint8_t *)malloc(decoded_size);
    if (!decoded) {
        free(packed);
        return -1;
    }
    size_t actual_size = 0;
    const int decode_status = shift_xmem_decompress_auto(
        packed, input_size, decoded, decoded_size, &actual_size);
    free(packed);
    if (decode_status != 0 || actual_size != decoded_size ||
        write_bytes(ctx, output, decoded_size, decoded) != 0) {
        free(decoded);
        return -1;
    }
    free(decoded);

    if (write_u32(ctx, "ram", output_size_ptr, (uint32_t)actual_size) != 0 ||
        write_u32(ctx, "register", 0x00, 0) != 0 ||
        write_u32(ctx, "register", 0x10, esp + 4) != 0 ||
        write_u32(ctx, "register", 0x284, return_address) != 0)
        return -1;
    return 0;
}
