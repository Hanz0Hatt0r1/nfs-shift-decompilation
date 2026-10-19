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
    const uint32_t stack = UINT32_C(0x00033000);
    const uint32_t return_address = UINT32_C(0x00405005);
    const uint32_t milliseconds = 1;
    uint8_t iat[4] = {0};
    if (ctx->write(ctx->opaque, "ram", stack, sizeof(return_address),
                   (const uint8_t *)&return_address) != 0 ||
        ctx->write(ctx->opaque, "ram", stack + 4, sizeof(milliseconds),
                   (const uint8_t *)&milliseconds) != 0 ||
        ctx->write(ctx->opaque, "register", UINT64_C(0x10), sizeof(stack),
                   (const uint8_t *)&stack) != 0 ||
        ctx->read(ctx->opaque, "ram", UINT64_C(0x00402c00), sizeof(iat),
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
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x00402c08), sizeof(iat),
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
        ctx->read(ctx->opaque, "ram", UINT64_C(0x00402c08), sizeof(iat),
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

int rvi_0050c7f0(RviPcodeContext *ctx) {
    const uint8_t enabled = 1;
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x00be250c), 1,
                   &enabled) != 0) {
        return -1;
    }
    return 0;
}

int rvi_0050c7e0(RviPcodeContext *ctx) {
    const uint8_t neighbor = 0;
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x00be250d), 1,
                      &neighbor);
}

int rvi_0050ceb0(RviPcodeContext *ctx) {
    return ctx->call(ctx->opaque, UINT64_C(0x0050c880));
}

int rvi_0050c880(RviPcodeContext *ctx) {
    (void)ctx;
    return 0;
}

int rvi_00403000(RviPcodeContext *ctx) {
    uint64_t output = 0;
    return ctx->userop(ctx->opaque, 7, NULL, NULL, 0, &output, 4);
}

static int cpuid_and_check(RviPcodeContext *ctx, uint32_t leaf,
                           uint32_t userop_index) {
    const uint64_t arguments[1] = {leaf};
    const unsigned argument_sizes[1] = {4};
    uint64_t result_address = 0;
    uint8_t registers[16] = {0};
    if (ctx->userop(ctx->opaque, userop_index, arguments, argument_sizes, 1,
                    &result_address, 4) != 0 ||
        result_address > UINT32_MAX ||
        ctx->read(ctx->opaque, "ram", result_address, sizeof(registers),
                  registers) != 0) {
        return -1;
    }
    return 0;
}

int rvi_00408000(RviPcodeContext *ctx) {
    if (cpuid_and_check(ctx, 0, 45) != 0) return -1;
    return cpuid_and_check(ctx, 1, 46);
}

int rvi_00409000(RviPcodeContext *ctx) {
    if (ctx->userop(ctx->opaque, 17, NULL, NULL, 0, NULL, 0) != 0) return -1;
    return ctx->userop(ctx->opaque, 18, NULL, NULL, 0, NULL, 0);
}

int rvi_0040a000(RviPcodeContext *ctx) {
    uint64_t ticks = 0;
    if (ctx->userop(ctx->opaque, 72, NULL, NULL, 0, &ticks, 8) != 0)
        return -1;
    return ticks == 0 ? -2 : 0;
}

int rvi_0040b000(RviPcodeContext *ctx) {
    const uint64_t arguments[2] = {
        UINT64_C(0x8000000000000000), UINT64_C(0x3fff)};
    const unsigned argument_sizes[1] = {10};
    uint64_t result[2] = {0};
    if (ctx->userop(ctx->opaque, 100, arguments, argument_sizes, 1, result,
                    10) != 0) {
        return -1;
    }
    uint8_t bytes[10];
    for (size_t index = 0; index < sizeof(bytes); ++index) {
        bytes[index] = (uint8_t)(result[index / sizeof(uint64_t)] >>
                                 ((index % sizeof(uint64_t)) * 8));
    }
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x11010), sizeof(bytes),
                      bytes);
}

int rvi_0040c000(RviPcodeContext *ctx) {
    uint32_t esp = 0;
    uint32_t teb = 0;
    uint32_t teb_self = 0;
    uint32_t parameter = 0;
    uint8_t value[4] = {0};
    const uint8_t result[4] = {0xef, 0xbe, 0, 0};
    if (ctx->read(ctx->opaque, "register", 0x10, 4,
                  (uint8_t *)&esp) != 0 ||
        ctx->read(ctx->opaque, "register", 0x110, 4,
                  (uint8_t *)&teb) != 0 ||
        ctx->read(ctx->opaque, "ram", esp + 4, 4, value) != 0 ||
        ctx->read(ctx->opaque, "ram", teb + 0x18, 4,
                  (uint8_t *)&teb_self) != 0) {
        return -1;
    }
    parameter = (uint32_t)value[0] | ((uint32_t)value[1] << 8) |
                ((uint32_t)value[2] << 16) | ((uint32_t)value[3] << 24);
    if (parameter != UINT32_C(0x12345678) || teb == 0 || teb_self != teb)
        return -2;
    return ctx->write(ctx->opaque, "register", 0, sizeof(result), result);
}

int rvi_0040c100(RviPcodeContext *ctx) {
    uint32_t esp = 0;
    uint32_t exit_thread_api = 0;
    const uint8_t exit_code[4] = {0xef, 0xbe, 0, 0};
    const uint8_t continued_marker[4] = {1, 0, 0, 0};
    if (ctx->read(ctx->opaque, "register", 0x10, 4,
                  (uint8_t *)&esp) != 0 ||
        ctx->read(ctx->opaque, "ram", 0x00034208, 4,
                  (uint8_t *)&exit_thread_api) != 0 ||
        ctx->write(ctx->opaque, "ram", esp + 4, sizeof(exit_code),
                   exit_code) != 0) {
        return -1;
    }
    if (ctx->call(ctx->opaque, exit_thread_api) != 0) return -1;
    return ctx->write(ctx->opaque, "ram", 0x0003420c,
                      sizeof(continued_marker), continued_marker);
}

int rvi_0040d000(RviPcodeContext *ctx) {
    const uint32_t value = 1;
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x00000008),
                      sizeof(value), (const uint8_t *)&value);
}

int rvi_00d8a600(RviPcodeContext *ctx) {
    uint32_t ecx = 0;
    uint32_t list_head = 0;
    if (ctx->read(ctx->opaque, "register", 4, sizeof(ecx),
                  (uint8_t *)&ecx) != 0 ||
        ctx->read(ctx->opaque, "ram", ecx, sizeof(list_head),
                  (uint8_t *)&list_head) != 0) {
        return -1;
    }
    return list_head == 0 ? -2 : 0;
}

int rvi_00506ab0(RviPcodeContext *ctx) {
    uint32_t ecx = 0;
    uint32_t edx = 0;
    uint32_t esp = 0;
    uint32_t element_count = 0;
    uint32_t element_type = 0;
    uint32_t frame[4] = {0};
    if (ctx->read(ctx->opaque, "register", 4, sizeof(ecx),
                  (uint8_t *)&ecx) != 0 ||
        ctx->read(ctx->opaque, "register", 8, sizeof(edx),
                  (uint8_t *)&edx) != 0 ||
        ctx->read(ctx->opaque, "register", 0x10, sizeof(esp),
                  (uint8_t *)&esp) != 0 ||
        ctx->read(ctx->opaque, "ram", ecx + 8, sizeof(element_count),
                  (uint8_t *)&element_count) != 0 ||
        ctx->read(ctx->opaque, "ram", ecx + 0x1c, sizeof(element_type),
                  (uint8_t *)&element_type) != 0 ||
        ctx->read(ctx->opaque, "ram", esp, sizeof(frame),
                  (uint8_t *)frame) != 0) {
        return -1;
    }
    if (edx != 0x10 || frame[0] != UINT32_C(0x00d8a681) ||
        frame[1] != element_count || frame[2] != 0x1f ||
        frame[3] != element_type) {
        return -2;
    }
    const uint32_t list_head = ecx + 0x40;
    return ctx->write(ctx->opaque, "ram", ecx, sizeof(list_head),
                      (const uint8_t *)&list_head);
}
