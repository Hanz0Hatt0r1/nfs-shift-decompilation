#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef int (*RviReadBytes)(void *, const char *, uint64_t, size_t, uint8_t *);
typedef int (*RviWriteBytes)(void *, const char *, uint64_t, size_t, const uint8_t *);
typedef int (*RviCallFunction)(void *, uint64_t);
typedef int (*RviUseropFunction)(void *, uint32_t, const uint64_t *, const unsigned *,
                                 size_t, uint64_t *, unsigned);
typedef struct {
    void *opaque;
    RviReadBytes read;
    RviWriteBytes write;
    RviCallFunction call;
    RviUseropFunction userop;
} RviPcodeContext;

enum { RAM_BASE = 0x8000, RAM_SIZE = 0x40000, REGISTER_SIZE = 0x1000 };
typedef struct {
    uint8_t ram[RAM_SIZE];
    uint8_t registers[REGISTER_SIZE];
    uint64_t last_call;
    unsigned call_count;
} SmokeState;

static int bank(void *opaque, const char *space, uint64_t offset, size_t size,
                uint8_t **bytes) {
    SmokeState *state = opaque;
    if (strcmp(space, "register") == 0) {
        if (offset > REGISTER_SIZE || size > REGISTER_SIZE - (size_t)offset) return -1;
        *bytes = state->registers + offset;
        return 0;
    }
    if (strcmp(space, "ram") == 0) {
        if (offset < RAM_BASE || offset - RAM_BASE > RAM_SIZE ||
            size > RAM_SIZE - (size_t)(offset - RAM_BASE)) return -1;
        *bytes = state->ram + (size_t)(offset - RAM_BASE);
        return 0;
    }
    return -1;
}

static int read_bytes(void *opaque, const char *space, uint64_t offset, size_t size,
                      uint8_t *out) {
    uint8_t *in;
    if (bank(opaque, space, offset, size, &in) != 0) return -1;
    memcpy(out, in, size);
    return 0;
}

static int write_bytes(void *opaque, const char *space, uint64_t offset, size_t size,
                       const uint8_t *in) {
    uint8_t *out;
    if (bank(opaque, space, offset, size, &out) != 0) return -1;
    memcpy(out, in, size);
    return 0;
}

static int call_function(void *opaque, uint64_t target) {
    SmokeState *state = opaque;
    state->last_call = target;
    ++state->call_count;
    return 0;
}

static void put_u32(uint8_t *bytes, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) bytes[i] = (uint8_t)(value >> (i * 8));
}

static uint32_t get_u32(const uint8_t *bytes) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <libnfs_shift_pcode_partial.so>\n", argv[0]);
        return 2;
    }
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    typedef int (*Function)(RviPcodeContext *);
    Function function = (Function)dlsym(library, "rvi_00401000");
    if (!function) {
        fprintf(stderr, "generated function rvi_00401000 is missing: %s\n", dlerror());
        dlclose(library);
        return 1;
    }

    SmokeState state = {0};
    const uint32_t esp = 0x10000, esi = 0x20000, return_address = 0xcafebabe;
    put_u32(state.registers + 0x4, esi); /* ECX becomes ESI in the function. */
    put_u32(state.registers + 0x10, esp);
    put_u32(state.ram + (esp - RAM_BASE), return_address);
    RviPcodeContext context = {&state, read_bytes, write_bytes, call_function, NULL};

    int result = function(&context);
    uint32_t eax = get_u32(state.registers);
    uint32_t stored = get_u32(state.ram + (esi - RAM_BASE));
    int ok = result == 0 && state.call_count == 1 && state.last_call == 0x00685700 &&
             eax == esi && stored == 0x00aa99d0;
    if (!ok) {
        fprintf(stderr,
                "smoke failed: result=%d calls=%u target=0x%llx eax=0x%x [esi]=0x%x\n",
                result, state.call_count, (unsigned long long)state.last_call, eax, stored);
        dlclose(library);
        return 1;
    }
    printf("PASS: rvi_00401000 returned %d, called 0x%llx once, EAX=0x%x, [ESI]=0x%x\n",
           result, (unsigned long long)state.last_call, eax, stored);
    dlclose(library);
    return 0;
}
