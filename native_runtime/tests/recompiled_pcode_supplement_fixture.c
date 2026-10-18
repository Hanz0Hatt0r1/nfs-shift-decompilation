#include "shift_recompiled_pcode_abi.h"

static int fixture_call_import(RviPcodeContext *ctx, uint32_t target,
                               const uint32_t *arguments, size_t count,
                               uint32_t *result) {
    uint32_t stack = 0;
    const uint32_t return_address = UINT32_C(0x00401020);
    if (ctx->read(ctx->opaque, "register", UINT64_C(0x10), sizeof(stack),
                  (uint8_t *)&stack) != 0 || stack < 0x100) {
        return -1;
    }
    stack -= 0x100;
    if (ctx->write(ctx->opaque, "ram", stack, sizeof(return_address),
                   (const uint8_t *)&return_address) != 0) {
        return -1;
    }
    for (size_t index = 0; index < count; ++index) {
        if (ctx->write(ctx->opaque, "ram", stack + 4 + index * 4,
                       sizeof(arguments[index]),
                       (const uint8_t *)&arguments[index]) != 0) {
            return -1;
        }
    }
    if (ctx->write(ctx->opaque, "register", UINT64_C(0x10), sizeof(stack),
                   (const uint8_t *)&stack) != 0) {
        return -1;
    }
    const int call_result = ctx->call(ctx->opaque, target);
    if (call_result != 0) return call_result;
    return ctx->read(ctx->opaque, "register", 0, sizeof(*result),
                     (uint8_t *)result);
}

static int fixture_resolve_kernel32(RviPcodeContext *ctx, const char *name,
                                    uint32_t *address) {
    static const uint32_t name_address = UINT32_C(0x36a00);
    size_t length = 0;
    while (name[length] != '\0') ++length;
    for (size_t offset = 0; offset < length + 1; offset += 16) {
        size_t chunk = length + 1 - offset;
        if (chunk > 16) chunk = 16;
        if (ctx->write(ctx->opaque, "ram", name_address + offset, chunk,
                       (const uint8_t *)name + offset) != 0) {
            return -1;
        }
    }
    const uint32_t arguments[] = {UINT32_C(0xe0000000), name_address};
    const int result = fixture_call_import(
        ctx, UINT32_C(0xf00000e0), arguments,
        sizeof(arguments) / sizeof(arguments[0]), address);
    return result;
}

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
    uint32_t create_thread = 0;
    uint32_t switch_to_thread = 0;
    uint32_t set_last_error = 0;
    uint32_t get_last_error = 0;
    uint32_t get_exit_code = 0;
    uint32_t exit_thread = 0;
    uint32_t suspend_thread = 0;
    uint32_t resume_thread = 0;
    if (fixture_resolve_kernel32(ctx, "CreateThread", &create_thread) != 0 ||
        fixture_resolve_kernel32(ctx, "SwitchToThread", &switch_to_thread) !=
            0 ||
        fixture_resolve_kernel32(ctx, "SetLastError", &set_last_error) != 0 ||
        fixture_resolve_kernel32(ctx, "GetLastError", &get_last_error) != 0 ||
        fixture_resolve_kernel32(ctx, "GetExitCodeThread", &get_exit_code) !=
            0 ||
        fixture_resolve_kernel32(ctx, "ExitThread", &exit_thread) != 0 ||
        fixture_resolve_kernel32(ctx, "SuspendThread", &suspend_thread) != 0 ||
        fixture_resolve_kernel32(ctx, "ResumeThread", &resume_thread) != 0 ||
        create_thread == 0 || switch_to_thread == 0 || set_last_error == 0 ||
        get_last_error == 0 || get_exit_code == 0 || exit_thread == 0 ||
        suspend_thread == 0 || resume_thread == 0) {
        return -3;
    }
    const uint32_t last_error_argument[] = {0x77};
    uint32_t ignored_result = 0;
    if (fixture_call_import(ctx, set_last_error, last_error_argument, 1,
                            &ignored_result) != 0) {
        return -4;
    }
    const uint32_t create_arguments[] = {
        0, 0, UINT32_C(0x00401040), UINT32_C(0x1234), 0,
        UINT32_C(0x32c14)};
    uint32_t thread_handle = 0;
    if (fixture_call_import(ctx, create_thread, create_arguments,
                            sizeof(create_arguments) /
                                sizeof(create_arguments[0]),
                            &thread_handle) != 0 ||
        thread_handle == 0) {
        return -5;
    }
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x32c18),
                   sizeof(thread_handle),
                   (const uint8_t *)&thread_handle) != 0) {
        return -6;
    }
    const uint32_t thread_handle_argument[] = {thread_handle};
    uint32_t thread_status = UINT32_MAX;
    if (fixture_call_import(ctx, suspend_thread, thread_handle_argument, 1,
                            &thread_status) != 0 ||
        thread_status != 0) {
        return -7;
    }
    uint32_t switched = 0;
    if (fixture_call_import(ctx, switch_to_thread, NULL, 0, &switched) != 0 ||
        switched != 1) {
        return -8;
    }
    if (fixture_call_import(ctx, resume_thread, thread_handle_argument, 1,
                            &thread_status) != 0 ||
        thread_status != 1) {
        return -9;
    }
    if (fixture_call_import(ctx, switch_to_thread, NULL, 0, &switched) != 0 ||
        switched != 1) {
        return -10;
    }
    uint8_t worker_marker[4] = {0};
    const uint8_t expected_worker_marker[4] = {0x34, 0x12, 0, 0};
    if (ctx->read(ctx->opaque, "ram", UINT64_C(0x32c10),
                  sizeof(worker_marker), worker_marker) != 0 ||
        worker_marker[0] != expected_worker_marker[0] ||
        worker_marker[1] != expected_worker_marker[1] ||
        worker_marker[2] != expected_worker_marker[2] ||
        worker_marker[3] != expected_worker_marker[3]) {
        return -11;
    }
    uint32_t restored_last_error = 0;
    if (fixture_call_import(ctx, get_last_error, NULL, 0,
                            &restored_last_error) != 0 ||
        restored_last_error != 0x77) {
        return -12;
    }
    const uint32_t exit_code_arguments[] = {thread_handle, UINT32_C(0x32c1c)};
    uint32_t got_exit_code = 0;
    if (fixture_call_import(ctx, get_exit_code, exit_code_arguments, 2,
                            &got_exit_code) != 0 ||
        got_exit_code != 1 ||
        ctx->read(ctx->opaque, "ram", UINT64_C(0x32c1c),
                  sizeof(got_exit_code), (uint8_t *)&got_exit_code) != 0 ||
        got_exit_code != UINT32_C(0xbeef)) {
        return -13;
    }
    if (fixture_call_import(ctx, switch_to_thread, NULL, 0, &switched) != 0 ||
        switched != 0) {
        return -14;
    }
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x32c00), sizeof(marker),
                      marker);
}

int rvi_00401040(RviPcodeContext *ctx) {
    const uint8_t marker[4] = {0x34, 0x12, 0, 0};
    uint32_t set_last_error = 0;
    uint32_t exit_thread = 0;
    if (fixture_resolve_kernel32(ctx, "SetLastError", &set_last_error) != 0 ||
        fixture_resolve_kernel32(ctx, "ExitThread", &exit_thread) != 0 ||
        set_last_error == 0 || exit_thread == 0) {
        return -1;
    }
    const uint32_t argument[] = {0x88};
    uint32_t ignored_result = 0;
    if (fixture_call_import(ctx, set_last_error, argument, 1,
                            &ignored_result) != 0) {
        return -2;
    }
    if (ctx->write(ctx->opaque, "ram", UINT64_C(0x32c10), sizeof(marker),
                   marker) != 0) {
        return -3;
    }
    const uint32_t exit_arguments[] = {UINT32_C(0xbeef)};
    if (fixture_call_import(ctx, exit_thread, exit_arguments, 1,
                            &ignored_result) != 1) {
        return -4;
    }
    return 1;
}

int rvi_00685700(RviPcodeContext *ctx) {
    const uint8_t duplicate[4] = {'D', 'U', 'P', 'L'};
    return ctx->write(ctx->opaque, "ram", UINT64_C(0x20000),
                      sizeof(duplicate), duplicate);
}
