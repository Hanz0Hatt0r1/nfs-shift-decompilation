#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <float.h>
#include <math.h>

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

static uint64_t rvi_mask(unsigned size) {
    return size == 8 ? UINT64_MAX : (UINT64_C(1) << (size * 8)) - 1;
}
static uint64_t rvi_sign_extend(uint64_t value, unsigned size) {
    uint64_t mask = rvi_mask(size), sign = UINT64_C(1) << (size * 8 - 1);
    value &= mask;
    return (value & sign) ? (value | ~mask) : value;
}
static int rvi_signed_less(uint64_t left, uint64_t right, unsigned size) {
    uint64_t mask = rvi_mask(size), sign = UINT64_C(1) << (size * 8 - 1);
    left &= mask; right &= mask;
    if ((left & sign) != (right & sign)) return (left & sign) != 0;
    return left < right;
}
static int rvi_carry(uint64_t left, uint64_t right, unsigned size) {
    uint64_t mask = rvi_mask(size);
    left &= mask; right &= mask;
    return left > mask - right;
}
static int rvi_signed_carry(uint64_t left, uint64_t right, unsigned size) {
    uint64_t mask = rvi_mask(size), sign = UINT64_C(1) << (size * 8 - 1);
    uint64_t result = (left + right) & mask;
    return ((~(left ^ right) & (left ^ result) & sign) != 0);
}
static int rvi_signed_borrow(uint64_t left, uint64_t right, unsigned size) {
    uint64_t mask = rvi_mask(size), sign = UINT64_C(1) << (size * 8 - 1);
    uint64_t result = (left - right) & mask;
    return (((left ^ right) & (left ^ result) & sign) != 0);
}
static uint64_t rvi_left(uint64_t value, uint64_t shift, unsigned size) {
    unsigned bits = size * 8;
    return shift >= bits ? 0 : (value << shift) & rvi_mask(size);
}
static uint64_t rvi_right(uint64_t value, uint64_t shift, unsigned size) {
    unsigned bits = size * 8;
    return shift >= bits ? 0 : (value & rvi_mask(size)) >> shift;
}
static uint64_t rvi_signed_right(uint64_t value, uint64_t shift, unsigned size) {
    unsigned bits = size * 8;
    uint64_t mask = rvi_mask(size), sign = UINT64_C(1) << (bits - 1);
    value &= mask;
    if (shift >= bits) return (value & sign) ? mask : 0;
    if (shift == 0) return value;
    return (value >> shift) | ((value & sign) ? (mask ^ (mask >> shift)) : 0);
}
static uint64_t rvi_popcount(uint64_t value) {
    uint64_t count = 0;
    while (value) { count += value & 1; value >>= 1; }
    return count;
}
enum { RVI_FLOAT_ADD = 1, RVI_FLOAT_SUB = 2, RVI_FLOAT_MULT = 3, RVI_FLOAT_DIV = 4 };
enum {
    RVI_FLOAT80_ADD = 1, RVI_FLOAT80_SUB = 2, RVI_FLOAT80_MULT = 3, RVI_FLOAT80_DIV = 4,
    RVI_FLOAT80_EQUAL = 5, RVI_FLOAT80_NOTEQUAL = 6,
    RVI_FLOAT80_LESS = 7, RVI_FLOAT80_LESSEQUAL = 8,
    RVI_FLOAT80_SQRT = 9, RVI_FLOAT80_ROUND = 10, RVI_FLOAT80_TRUNC = 11
};
static float rvi_float32(uint64_t bits) {
    uint32_t word = (uint32_t)bits;
    float value;
    memcpy(&value, &word, sizeof(value));
    return value;
}
static double rvi_float64(uint64_t bits) {
    double value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}
static uint64_t rvi_float32_bits(float value) {
    uint32_t word;
    memcpy(&word, &value, sizeof(word));
    return word;
}
static uint64_t rvi_float64_bits(double value) {
    uint64_t bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}
static uint64_t rvi_float_binary(uint64_t left, uint64_t right, unsigned size, unsigned op) {
    if (size == 4) {
        float a = rvi_float32(left), b = rvi_float32(right);
        volatile float result;
        switch (op) {
        case RVI_FLOAT_ADD: result = a + b; break;
        case RVI_FLOAT_SUB: result = a - b; break;
        case RVI_FLOAT_MULT: result = a * b; break;
        case RVI_FLOAT_DIV: result = a / b; break;
        default: return 0;
        }
        if (isfinite(a) && isfinite(b) && isinf(result) && !(op == RVI_FLOAT_DIV && b == 0.0f))
            result = NAN;
        return rvi_float32_bits(result);
    }
    if (size == 8) {
        double a = rvi_float64(left), b = rvi_float64(right);
        volatile double result;
        switch (op) {
        case RVI_FLOAT_ADD: result = a + b; break;
        case RVI_FLOAT_SUB: result = a - b; break;
        case RVI_FLOAT_MULT: result = a * b; break;
        case RVI_FLOAT_DIV: result = a / b; break;
        default: return 0;
        }
        if (isfinite(a) && isfinite(b) && isinf(result) && !(op == RVI_FLOAT_DIV && b == 0.0))
            result = NAN;
        return rvi_float64_bits(result);
    }
    return 0;
}
static uint64_t rvi_float_sqrt(uint64_t bits, unsigned size) {
    if (size == 4) return rvi_float32_bits(sqrtf(rvi_float32(bits)));
    if (size == 8) return rvi_float64_bits(sqrt(rvi_float64(bits)));
    return 0;
}
static uint64_t rvi_float_round(uint64_t bits, unsigned size) {
    if (size == 4) return rvi_float32_bits(roundf(rvi_float32(bits)));
    if (size == 8) return rvi_float64_bits(round(rvi_float64(bits)));
    return 0;
}
static uint64_t rvi_float_convert(uint64_t bits, unsigned input_size, unsigned output_size) {
    if (input_size == 4 && output_size == 8)
        return rvi_float64_bits((double)rvi_float32(bits));
    if (input_size == 8 && output_size == 4)
        return rvi_float32_bits((float)rvi_float64(bits));
    return 0;
}
static int64_t rvi_signed_integer(uint64_t value, unsigned size) {
    uint64_t extended = rvi_sign_extend(value, size);
    int64_t result;
    memcpy(&result, &extended, sizeof(result));
    return result;
}
static int rvi_float80_host_supported(void) {
    return LDBL_MANT_DIG >= 64 && LDBL_MAX_EXP >= 16384 &&
           LDBL_MIN_EXP <= -16381 && ldexpl(1.0L, -16445) != 0.0L;
}
static int rvi_x87_wait(void) {
#if (defined(__i386__) || defined(__x86_64__)) && (defined(__GNUC__) || defined(__clang__))
    __asm__ __volatile__("fwait" ::: "memory");
    return 0;
#elif defined(_MSC_VER) && defined(_M_IX86)
    __asm fwait
    return 0;
#else
    return -1;
#endif
}
static int rvi_float80_load(const uint8_t input[10], long double *value) {
    uint64_t significand = 0;
    unsigned sign_exponent, exponent;
    int binary_exponent;
    if (!input || !value || !rvi_float80_host_supported()) return -1;
    for (unsigned i = 0; i < 8; ++i) significand |= (uint64_t)input[i] << (i * 8);
    sign_exponent = (unsigned)input[8] | ((unsigned)input[9] << 8);
    exponent = sign_exponent & 0x7fff;
    if (exponent == 0x7fff) {
        if (significand == UINT64_C(0x8000000000000000)) *value = INFINITY;
        else *value = nanl("");
    } else {
        if (exponent != 0 && !(significand >> 63)) {
            *value = nanl("");
        } else {
            if (exponent == 0) exponent = 1;
            binary_exponent = (int)exponent - 16383 - 63;
            *value = ldexpl((long double)significand, binary_exponent);
        }
    }
    if (sign_exponent & 0x8000) *value = copysignl(*value, -1.0L);
    return 0;
}
static int rvi_float80_store(long double value, uint8_t output[10]) {
    uint64_t significand;
    unsigned exponent = 0;
    int sign = signbit(value) != 0;
    uint16_t sign_exponent;
    long double magnitude = fabsl(value);
    if (!output || !rvi_float80_host_supported()) return -1;
    if (isinf(value)) {
        exponent = 0x7fff;
        significand = UINT64_C(0x8000000000000000);
    } else if (isnan(value)) {
        exponent = 0x7fff;
        significand = UINT64_C(0xc000000000000000);
    } else if (magnitude >= ldexpl(1.0L, -16382)) {
        int binary_exponent;
        long double fraction = frexpl(magnitude, &binary_exponent);
        long double rounded = fabsl(rintl(sign ? -ldexpl(fraction, 64) : ldexpl(fraction, 64)));
        int biased_exponent = binary_exponent - 1 + 16383;
        if (rounded >= ldexpl(1.0L, 64)) {
            rounded = ldexpl(1.0L, 63);
            ++biased_exponent;
        }
        if (biased_exponent >= 0x7fff) {
            exponent = 0x7fff;
            significand = UINT64_C(0x8000000000000000);
        } else {
            exponent = (unsigned)biased_exponent;
            significand = (uint64_t)(rounded - ldexpl(1.0L, 63)) |
                          UINT64_C(0x8000000000000000);
        }
    } else {
        long double rounded = fabsl(rintl(sign ? -ldexpl(magnitude, 16445) : ldexpl(magnitude, 16445)));
        if (rounded >= ldexpl(1.0L, 63)) {
            exponent = 1;
            significand = UINT64_C(0x8000000000000000);
        } else {
            significand = (uint64_t)rounded;
        }
    }
    sign_exponent = (uint16_t)(exponent | (sign ? 0x8000 : 0));
    for (unsigned i = 0; i < 8; ++i) output[i] = (uint8_t)(significand >> (i * 8));
    output[8] = (uint8_t)sign_exponent;
    output[9] = (uint8_t)(sign_exponent >> 8);
    return 0;
}
static int rvi_float80_from_float(uint64_t bits, unsigned size, uint8_t output[10]) {
    long double value;
    if (!rvi_float80_host_supported()) return -1;
    if (size == 4) value = (long double)rvi_float32(bits);
    else if (size == 8) value = (long double)rvi_float64(bits);
    else return -1;
    return rvi_float80_store(value, output);
}
static int rvi_float80_to_float(const uint8_t input[10], unsigned size, uint64_t *bits) {
    long double value;
    if (!bits || rvi_float80_load(input, &value) != 0) return -1;
    if (size == 4) *bits = rvi_float32_bits((float)value);
    else if (size == 8) *bits = rvi_float64_bits((double)value);
    else return -1;
    return 0;
}
static int rvi_float80_from_integer(uint64_t value, unsigned size, uint8_t output[10]) {
    if (!rvi_float80_host_supported() || size == 0 || size > 8) return -1;
    return rvi_float80_store((long double)rvi_signed_integer(value, size), output);
}
static int rvi_float80_binary(const uint8_t left[10], const uint8_t right[10],
                              unsigned op, uint8_t output[10]) {
    long double a, b, result;
    volatile long double rounded;
    if (rvi_float80_load(left, &a) != 0 || rvi_float80_load(right, &b) != 0) return -1;
    switch (op) {
    case RVI_FLOAT80_ADD: rounded = a + b; break;
    case RVI_FLOAT80_SUB: rounded = a - b; break;
    case RVI_FLOAT80_MULT: rounded = a * b; break;
    case RVI_FLOAT80_DIV: rounded = a / b; break;
    default: return -1;
    }
    result = rounded;
    if (isfinite(a) && isfinite(b) && isinf(result) &&
        !(op == RVI_FLOAT80_DIV && b == 0.0L)) result = nanl("");
    return rvi_float80_store(result, output);
}
static int rvi_float80_compare(const uint8_t left[10], const uint8_t right[10],
                               unsigned op, int *result) {
    long double a, b;
    if (!result || rvi_float80_load(left, &a) != 0 || rvi_float80_load(right, &b) != 0) return -1;
    *result = 0;
    if (isnan(a) || isnan(b)) {
        *result = op == RVI_FLOAT80_NOTEQUAL;
        return 0;
    }
    switch (op) {
    case RVI_FLOAT80_EQUAL: *result = a == b; break;
    case RVI_FLOAT80_NOTEQUAL: *result = a != b; break;
    case RVI_FLOAT80_LESS: *result = a < b; break;
    case RVI_FLOAT80_LESSEQUAL: *result = a <= b; break;
    default: return -1;
    }
    return 0;
}
static void rvi_float80_sign(const uint8_t input[10], int clear_sign, uint8_t output[10]) {
    memcpy(output, input, 10);
    if (clear_sign) output[9] &= 0x7f;
    else output[9] ^= 0x80;
}
static int rvi_float80_unary(const uint8_t input[10], unsigned op, uint8_t output[10]) {
    long double value;
    if (rvi_float80_load(input, &value) != 0) return -1;
    if (op == RVI_FLOAT80_SQRT) value = sqrtl(value);
    else if (op == RVI_FLOAT80_ROUND) value = roundl(value);
    else if (op == RVI_FLOAT80_TRUNC) value = truncl(value);
    else return -1;
    return rvi_float80_store(value, output);
}
static int rvi_float80_isnan(const uint8_t input[10], int *result) {
    long double value;
    if (!result || rvi_float80_load(input, &value) != 0) return -1;
    *result = isnan(value);
    return 0;
}
static int rvi_float80_trunc(const uint8_t input[10], unsigned size, uint64_t *result) {
    long double value, truncated, limit;
    if (!result || size == 0 || size > 8 || rvi_float80_load(input, &value) != 0) return -1;
    truncated = truncl(value);
    limit = ldexpl(1.0L, size * 8 - 1);
    if (!isfinite(truncated) || truncated < -limit || truncated >= limit) return -1;
    *result = (uint64_t)(int64_t)truncated & rvi_mask(size);
    return 0;
}
static uint64_t rvi_int_to_float(uint64_t value, unsigned input_size, unsigned output_size) {
    int64_t signed_value = rvi_signed_integer(value, input_size);
    if (output_size == 4) return rvi_float32_bits((float)signed_value);
    if (output_size == 8) return rvi_float64_bits((double)signed_value);
    return 0;
}
static int rvi_integer_divmod(uint64_t left, uint64_t right, unsigned size,
                              int is_signed, int remainder, uint64_t *result) {
    uint64_t mask = rvi_mask(size);
    left &= mask;
    right &= mask;
    if (!result || right == 0) return -1;
    if (!is_signed) {
        *result = (remainder ? left % right : left / right) & mask;
        return 0;
    }
    int64_t a = rvi_signed_integer(left, size);
    int64_t b = rvi_signed_integer(right, size);
    int64_t minimum = size == 8 ? INT64_MIN : -(INT64_C(1) << (size * 8 - 1));
    if (a == minimum && b == -1) return -1;
    int64_t quotient = remainder ? a % b : a / b;
    *result = (uint64_t)quotient & mask;
    return 0;
}
static int rvi_float_trunc_to_int(uint64_t bits, unsigned input_size,
                                  unsigned output_size, uint64_t *result) {
    if (!result || (input_size != 4 && input_size != 8) || output_size == 0 || output_size > 8)
        return -1;
    double value = input_size == 4 ? (double)rvi_float32(bits) : rvi_float64(bits);
    double truncated = trunc(value);
    double limit = ldexp(1.0, output_size * 8 - 1);
    if (!isfinite(truncated) || truncated < -limit || truncated >= limit) return -1;
    int64_t signed_value = (int64_t)truncated;
    *result = (uint64_t)signed_value & rvi_mask(output_size);
    return 0;
}
static int rvi_read_bytes(RviPcodeContext *ctx, uint8_t *unique, uint64_t unique_base,
                          size_t unique_size, const char *space, uint64_t offset,
                          unsigned size, uint8_t *bytes) {
    if (size == 0 || size > 16) return -1;
    if (strcmp(space, "unique") == 0) {
        if (offset < unique_base || offset - unique_base > unique_size ||
            size > unique_size - (size_t)(offset - unique_base)) return -1;
        memcpy(bytes, unique + (size_t)(offset - unique_base), size);
        return 0;
    }
    return ctx && ctx->read ? ctx->read(ctx->opaque, space, offset, size, bytes) : -1;
}
static int rvi_write_bytes(RviPcodeContext *ctx, uint8_t *unique, uint64_t unique_base,
                           size_t unique_size, const char *space, uint64_t offset,
                           unsigned size, const uint8_t *bytes) {
    if (size == 0 || size > 16) return -1;
    if (strcmp(space, "unique") == 0) {
        if (offset < unique_base || offset - unique_base > unique_size ||
            size > unique_size - (size_t)(offset - unique_base)) return -1;
        memcpy(unique + (size_t)(offset - unique_base), bytes, size);
        return 0;
    }
    return ctx && ctx->write ? ctx->write(ctx->opaque, space, offset, size, bytes) : -1;
}
static void rvi_value_to_bytes(uint64_t value, unsigned value_size, unsigned output_size,
                              int big_endian, uint8_t *output) {
    memset(output, 0, output_size);
    for (unsigned i = 0; i < value_size; i++) {
        unsigned index = big_endian ? output_size - 1 - i : i;
        output[index] = (uint8_t)(value >> (i * 8));
    }
}
static void rvi_zero_extend_bytes(uint8_t *output, unsigned output_size,
                                  const uint8_t *input, unsigned input_size, int big_endian) {
    memset(output, 0, output_size);
    memcpy(output + (big_endian ? output_size - input_size : 0), input, input_size);
}
static uint64_t rvi_bytes_subpiece(const uint8_t *input, unsigned input_size,
                                  unsigned byte_offset, unsigned output_size, int big_endian) {
    uint64_t value = 0;
    for (unsigned i = 0; i < output_size; i++) {
        unsigned logical_index = byte_offset + i;
        if (logical_index >= input_size) continue;
        unsigned index = big_endian ? input_size - 1 - logical_index : logical_index;
        value |= (uint64_t)input[index] << (i * 8);
    }
    return value;
}
static void rvi_shift_right_bytes(const uint8_t *input, unsigned size, uint64_t shift,
                                 int big_endian, uint8_t *output) {
    memset(output, 0, size);
    if (shift >= (uint64_t)size * 8) return;
    unsigned whole = (unsigned)(shift / 8), bits = (unsigned)(shift % 8);
    for (unsigned i = 0; i < size; i++) {
        unsigned source = i + whole;
        if (source >= size) break;
        unsigned source_index = big_endian ? size - 1 - source : source;
        unsigned output_index = big_endian ? size - 1 - i : i;
        unsigned value = input[source_index] >> bits;
        if (bits && source + 1 < size) {
            unsigned next_index = big_endian ? size - 2 - source : source + 1;
            value |= (unsigned)input[next_index] << (8 - bits);
        }
        output[output_index] = (uint8_t)value;
    }
}
static int rvi_read_value(RviPcodeContext *ctx, uint8_t *unique, uint64_t unique_base,
                          size_t unique_size, const char *space, uint64_t offset,
                          unsigned size, int big_endian, uint64_t *value) {
    uint8_t bytes[8] = {0};
    if (size == 0 || size > 8) return -1;
    if (rvi_read_bytes(ctx, unique, unique_base, unique_size, space, offset,
                       size, bytes) != 0) return -1;
    *value = 0;
    for (unsigned i = 0; i < size; i++) {
        unsigned index = big_endian ? i : size - 1 - i;
        *value = (*value << 8) | bytes[index];
    }
    return 0;
}
static int rvi_write_value(RviPcodeContext *ctx, uint8_t *unique, uint64_t unique_base,
                           size_t unique_size, const char *space, uint64_t offset,
                           unsigned size, int big_endian, uint64_t value) {
    uint8_t bytes[8] = {0};
    if (size == 0 || size > 8) return -1;
    value &= rvi_mask(size);
    for (unsigned i = 0; i < size; i++) {
        unsigned shift = big_endian ? (size - 1 - i) * 8 : i * 8;
        bytes[i] = (uint8_t)(value >> shift);
    }
    return rvi_write_bytes(ctx, unique, unique_base, unique_size, space, offset, size, bytes);
}
static int rvi_read_space(RviPcodeContext *ctx, const char *space, uint64_t offset,
                          unsigned size, int big_endian, uint64_t *value) {
    uint8_t bytes[8] = {0};
    if (!ctx || !ctx->read || size == 0 || size > 8 ||
        ctx->read(ctx->opaque, space, offset, size, bytes) != 0) return -1;
    *value = 0;
    for (unsigned i = 0; i < size; i++) {
        unsigned index = big_endian ? i : size - 1 - i;
        *value = (*value << 8) | bytes[index];
    }
    return 0;
}
static int rvi_write_space(RviPcodeContext *ctx, const char *space, uint64_t offset,
                           unsigned size, int big_endian, uint64_t value) {
    uint8_t bytes[8] = {0};
    if (!ctx || !ctx->write || size == 0 || size > 8) return -1;
    value &= rvi_mask(size);
    for (unsigned i = 0; i < size; i++) {
        unsigned shift = big_endian ? (size - 1 - i) * 8 : i * 8;
        bytes[i] = (uint8_t)(value >> shift);
    }
    return ctx->write(ctx->opaque, space, offset, size, bytes);
}
static int rvi_call(RviPcodeContext *ctx, uint64_t target) {
    return ctx && ctx->call ? ctx->call(ctx->opaque, target) : -1;
}
static int rvi_call_x86_32(RviPcodeContext *ctx, uint64_t target,
                           uint32_t return_address, const char *stack_space) {
    uint64_t original_esp, stack_return_address = 0;
    if (!ctx || rvi_read_space(ctx, "register", UINT64_C(0x10), 4, 0,
                               &original_esp) != 0 || original_esp > UINT32_MAX)
        return -1;
    const uint32_t esp = (uint32_t)original_esp;
    int synthetic_return_slot = 1;
    uint32_t call_esp;
    if (rvi_read_space(ctx, stack_space, esp, 4, 0, &stack_return_address) == 0 &&
        (uint32_t)stack_return_address == return_address) {
        /* Ghidra's x86 CALL P-code has already pushed this fallthrough. */
        call_esp = esp;
        synthetic_return_slot = 0;
    } else {
        if (esp < 4) return -1;
        call_esp = esp - 4;
        if (rvi_write_space(ctx, stack_space, call_esp, 4, 0, return_address) != 0 ||
            rvi_write_space(ctx, "register", UINT64_C(0x10), 4, 0, call_esp) != 0)
            return -1;
    }
    if (rvi_call(ctx, target) != 0) return -1;
    uint64_t returned_esp;
    if (rvi_read_space(ctx, "register", UINT64_C(0x10), 4, 0,
                       &returned_esp) != 0 || returned_esp > UINT32_MAX)
        return -1;
    /* Imports have no guest RET instruction; consume the call's one return slot. */
    if (returned_esp == call_esp &&
        rvi_write_space(ctx, "register", UINT64_C(0x10), 4, 0,
                        synthetic_return_slot ? esp : call_esp + 4u) != 0)
        return -1;
    return 0;
}
/* Generated from raw P-code for ENTRY_00509551 (0x00509551). */
int rvi_00509551(RviPcodeContext *ctx) {
    uint8_t _unique[61] = {0};
    const size_t _unique_size = 61;
    if (!ctx) return -1;
rvi_label_0000000000509551: ;
    {
    uint64_t rvi_0_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_0_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_0_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_1_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_1_ptr_value) != 0) return -1;
      uint64_t rvi_1_address = (rvi_1_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_1_address, 4, 0, UINT64_C(0x509556)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x40b870), UINT32_C(0x509556), "ram") != 0) return -1;
    }
rvi_label_0000000000509556: ;
    {
    uint64_t rvi_3_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_3_ptr_value) != 0) return -1;
      uint64_t rvi_3_loaded;
      uint64_t rvi_3_address = (rvi_3_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_3_address, 4, 0, &rvi_3_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_3_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_4_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_4_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_4_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_0000000000509558: ;
    {
    uint64_t rvi_5_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_5_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_5_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050955a: ;
    {
    uint64_t rvi_6_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_6_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_6_a0_value + UINT64_C(0x48)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_7_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_7_ptr_value) != 0) return -1;
      uint64_t rvi_7_loaded;
      uint64_t rvi_7_address = (rvi_7_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_7_address, 4, 0, &rvi_7_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_7_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_8_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_8_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_8_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050955d: ;
    {
    uint64_t rvi_9_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_9_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, (rvi_9_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_10_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_10_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_10_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_11_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_11_ptr_value) != 0) return -1;
      uint64_t rvi_11_address = (rvi_11_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_11_address, 4, 0, UINT64_C(0x50955f)) != 0) return -1;
    }
    {
    uint64_t rvi_12_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, &rvi_12_call_target_value) != 0) return -1;
    if (rvi_call_x86_32(ctx, rvi_12_call_target_value, UINT32_C(0x50955f), "ram") != 0) return -1;
    }
rvi_label_000000000050955f: ;
    {
    uint64_t rvi_13_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_13_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, (rvi_13_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_14_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_14_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_14_a0_value & rvi_mask(4)) < (UINT64_C(0x1) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_15_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_15_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_15_a0_value, UINT64_C(0x1), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_16_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_16_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, (((rvi_16_a0_value - UINT64_C(0x1)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_17_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_17_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_17_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_18_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_18_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_18_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_19_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_19_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_19_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_20_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_20_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_20_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_21_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_21_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_21_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_22_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_22_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_22_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509562: ;
    {
    uint64_t rvi_23_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_23_condition_value) != 0) return -1;
    if (rvi_23_condition_value != 0) { if (rvi_call(ctx, UINT64_C(0x5096aa)) != 0) return -1; return 0; }
    }
rvi_label_0000000000509568: ;
    {
    uint64_t rvi_24_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_24_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_24_a0_value + UINT64_C(0xc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_25_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_25_ptr_value) != 0) return -1;
      uint64_t rvi_25_loaded;
      uint64_t rvi_25_address = (rvi_25_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_25_address, 4, 0, &rvi_25_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_25_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_26_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_26_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_26_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050956b: ;
    {
    uint64_t rvi_27_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_27_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_27_a0_value + UINT64_C(0xe4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_28_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_28_ptr_value) != 0) return -1;
      uint64_t rvi_28_loaded;
      uint64_t rvi_28_address = (rvi_28_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_28_address, 4, 0, &rvi_28_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_28_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_29_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_29_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_29_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_0000000000509571: ;
    {
    uint64_t rvi_30_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_30_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, (rvi_30_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_31_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_31_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_31_a0_value & rvi_mask(4)) < (UINT64_C(0x7) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_32_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_32_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_32_a0_value, UINT64_C(0x7), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_33_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_33_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, (((rvi_33_a0_value - UINT64_C(0x7)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_34_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_34_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_34_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_35_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_35_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_35_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_36_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_36_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_36_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_37_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_37_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_37_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_38_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_38_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_38_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_39_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_39_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_39_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509574: ;
    {
    uint64_t rvi_40_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, &rvi_40_a0_value) != 0) return -1;
    uint64_t rvi_40_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_40_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_40_a0_value != 0) || (rvi_40_a1_value != 0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_41_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_41_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 1, 0, ((rvi_41_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_42_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 1, 0, &rvi_42_condition_value) != 0) return -1;
    if (rvi_42_condition_value != 0) { goto rvi_label_0000000000509588; }
    }
rvi_label_0000000000509576: ;
    {
    uint64_t rvi_43_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_43_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, (((rvi_43_a0_value * UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_44_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, &rvi_44_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (((UINT64_C(0x5096d8) + rvi_44_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_45_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_45_ptr_value) != 0) return -1;
      uint64_t rvi_45_loaded;
      uint64_t rvi_45_address = (rvi_45_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_45_address, 4, 0, &rvi_45_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_45_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_46_branch_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_46_branch_target_value) != 0) return -1;
    switch (rvi_46_branch_target_value) {
    case UINT64_C(0x509551): goto rvi_label_0000000000509551;
    case UINT64_C(0x509556): goto rvi_label_0000000000509556;
    case UINT64_C(0x509558): goto rvi_label_0000000000509558;
    case UINT64_C(0x50955a): goto rvi_label_000000000050955a;
    case UINT64_C(0x50955d): goto rvi_label_000000000050955d;
    case UINT64_C(0x50955f): goto rvi_label_000000000050955f;
    case UINT64_C(0x509562): goto rvi_label_0000000000509562;
    case UINT64_C(0x509568): goto rvi_label_0000000000509568;
    case UINT64_C(0x50956b): goto rvi_label_000000000050956b;
    case UINT64_C(0x509571): goto rvi_label_0000000000509571;
    case UINT64_C(0x509574): goto rvi_label_0000000000509574;
    case UINT64_C(0x509576): goto rvi_label_0000000000509576;
    case UINT64_C(0x50957d): goto rvi_label_000000000050957d;
    case UINT64_C(0x50957f): goto rvi_label_000000000050957f;
    case UINT64_C(0x509584): goto rvi_label_0000000000509584;
    case UINT64_C(0x509588): goto rvi_label_0000000000509588;
    case UINT64_C(0x50958c): goto rvi_label_000000000050958c;
    case UINT64_C(0x50958f): goto rvi_label_000000000050958f;
    case UINT64_C(0x509591): goto rvi_label_0000000000509591;
    case UINT64_C(0x509593): goto rvi_label_0000000000509593;
    case UINT64_C(0x509595): goto rvi_label_0000000000509595;
    case UINT64_C(0x509598): goto rvi_label_0000000000509598;
    case UINT64_C(0x50959b): goto rvi_label_000000000050959b;
    case UINT64_C(0x5095a0): goto rvi_label_00000000005095a0;
    case UINT64_C(0x5095a2): goto rvi_label_00000000005095a2;
    case UINT64_C(0x5095a4): goto rvi_label_00000000005095a4;
    case UINT64_C(0x5095a8): goto rvi_label_00000000005095a8;
    case UINT64_C(0x5095ae): goto rvi_label_00000000005095ae;
    case UINT64_C(0x5095b1): goto rvi_label_00000000005095b1;
    case UINT64_C(0x5095b3): goto rvi_label_00000000005095b3;
    case UINT64_C(0x5095b9): goto rvi_label_00000000005095b9;
    case UINT64_C(0x5095bd): goto rvi_label_00000000005095bd;
    case UINT64_C(0x5095c3): goto rvi_label_00000000005095c3;
    case UINT64_C(0x5095c7): goto rvi_label_00000000005095c7;
    case UINT64_C(0x5095cd): goto rvi_label_00000000005095cd;
    case UINT64_C(0x5095f0): goto rvi_label_00000000005095f0;
    case UINT64_C(0x5095f7): goto rvi_label_00000000005095f7;
    case UINT64_C(0x5095f9): goto rvi_label_00000000005095f9;
    case UINT64_C(0x5095fb): goto rvi_label_00000000005095fb;
    case UINT64_C(0x509600): goto rvi_label_0000000000509600;
    case UINT64_C(0x509607): goto rvi_label_0000000000509607;
    case UINT64_C(0x509609): goto rvi_label_0000000000509609;
    case UINT64_C(0x50960b): goto rvi_label_000000000050960b;
    case UINT64_C(0x509610): goto rvi_label_0000000000509610;
    case UINT64_C(0x509615): goto rvi_label_0000000000509615;
    case UINT64_C(0x50961c): goto rvi_label_000000000050961c;
    case UINT64_C(0x509622): goto rvi_label_0000000000509622;
    case UINT64_C(0x509626): goto rvi_label_0000000000509626;
    case UINT64_C(0x50962b): goto rvi_label_000000000050962b;
    case UINT64_C(0x509632): goto rvi_label_0000000000509632;
    case UINT64_C(0x509634): goto rvi_label_0000000000509634;
    case UINT64_C(0x509636): goto rvi_label_0000000000509636;
    case UINT64_C(0x50963b): goto rvi_label_000000000050963b;
    case UINT64_C(0x509642): goto rvi_label_0000000000509642;
    case UINT64_C(0x509648): goto rvi_label_0000000000509648;
    case UINT64_C(0x50964c): goto rvi_label_000000000050964c;
    case UINT64_C(0x509651): goto rvi_label_0000000000509651;
    case UINT64_C(0x509656): goto rvi_label_0000000000509656;
    case UINT64_C(0x50965b): goto rvi_label_000000000050965b;
    case UINT64_C(0x50965d): goto rvi_label_000000000050965d;
    case UINT64_C(0x509662): goto rvi_label_0000000000509662;
    case UINT64_C(0x509666): goto rvi_label_0000000000509666;
    case UINT64_C(0x50966b): if (rvi_call(ctx, UINT64_C(0x50966b)) != 0) return -1; return 0;
    case UINT64_C(0x50967d): if (rvi_call(ctx, UINT64_C(0x50967d)) != 0) return -1; return 0;
    default:
        if (rvi_call(ctx, rvi_46_branch_target_value) != 0) return -1;
        return 0;
    }
    }
rvi_label_000000000050957d: ;
    {
    uint64_t rvi_47_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_47_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_47_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050957f: ;
    {
    uint64_t rvi_48_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_48_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_48_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_49_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_49_ptr_value) != 0) return -1;
      uint64_t rvi_49_address = (rvi_49_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_49_address, 4, 0, UINT64_C(0x509584)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x5088c0), UINT32_C(0x509584), "ram") != 0) return -1;
    }
rvi_label_0000000000509584: ;
    {
    uint64_t rvi_51_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_51_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_51_a0_value + UINT64_C(0xfffffffd)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_53_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_53_ptr_value) != 0) return -1;
    uint64_t rvi_53_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_53_value_value) != 0) return -1;
      uint64_t rvi_53_address = (rvi_53_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_53_address, 1, 0, rvi_53_value_value) != 0) return -1;
    }
rvi_label_0000000000509588: ;
    {
    uint64_t rvi_54_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_54_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_54_a0_value + UINT64_C(0xffffffff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_56_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_56_ptr_value) != 0) return -1;
    uint64_t rvi_56_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_56_value_value) != 0) return -1;
      uint64_t rvi_56_address = (rvi_56_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_56_address, 1, 0, rvi_56_value_value) != 0) return -1;
    }
rvi_label_000000000050958c: ;
    {
    uint64_t rvi_57_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_57_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_57_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_58_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_58_ptr_value) != 0) return -1;
      uint64_t rvi_58_loaded;
      uint64_t rvi_58_address = (rvi_58_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_58_address, 4, 0, &rvi_58_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_58_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_59_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_59_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_59_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050958f: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_62_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_62_a0_value) != 0) return -1;
    uint64_t rvi_62_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_62_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (((rvi_62_a0_value & rvi_62_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_63_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_63_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_63_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_64_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_64_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_64_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_65_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_65_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_65_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_66_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_66_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_66_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_67_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_67_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_67_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_68_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_68_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_68_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509591: ;
    {
    uint64_t rvi_69_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_69_condition_value) != 0) return -1;
    if (rvi_69_condition_value != 0) { goto rvi_label_0000000000509595; }
    }
rvi_label_0000000000509593: ;
    {
    uint64_t rvi_70_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_70_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_70_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_0000000000509595: ;
    {
    uint64_t rvi_71_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_71_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_71_a0_value + UINT64_C(0xfffffff4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_72_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_72_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_72_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_0000000000509598: ;
    {
    uint64_t rvi_73_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_73_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_73_a0_value + UINT64_C(0x8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_74_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_74_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_74_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050959b: ;
    {
    uint64_t rvi_75_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_75_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_75_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_76_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_76_ptr_value) != 0) return -1;
      uint64_t rvi_76_address = (rvi_76_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_76_address, 4, 0, UINT64_C(0x5095a0)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x4f5eb0), UINT32_C(0x5095a0), "ram") != 0) return -1;
    }
rvi_label_00000000005095a0: ;
    {
    uint64_t rvi_78_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_78_ptr_value) != 0) return -1;
      uint64_t rvi_78_loaded;
      uint64_t rvi_78_address = (rvi_78_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_78_address, 4, 0, &rvi_78_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 4, 0, (rvi_78_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_79_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 4, 0, &rvi_79_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, (rvi_79_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_80_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_80_a0_value) != 0) return -1;
    uint64_t rvi_80_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_80_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_80_a0_value & rvi_mask(4)) < (rvi_80_a1_value & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_81_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_81_a0_value) != 0) return -1;
    uint64_t rvi_81_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_81_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_81_a0_value, rvi_81_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_82_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_82_a0_value) != 0) return -1;
    uint64_t rvi_82_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_82_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (((rvi_82_a0_value - rvi_82_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_83_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_83_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_83_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_84_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_84_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_84_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_85_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_85_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_85_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_86_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_86_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_86_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_87_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_87_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_87_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_88_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_88_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_88_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095a2: ;
    {
    uint64_t rvi_89_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_89_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_89_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_90_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_90_condition_value) != 0) return -1;
    if (rvi_90_condition_value != 0) { goto rvi_label_0000000000509551; }
    }
rvi_label_00000000005095a4: ;
    {
    uint64_t rvi_91_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_91_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_91_a0_value + UINT64_C(0xfffffffd)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_92_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_92_ptr_value) != 0) return -1;
      uint64_t rvi_92_loaded;
      uint64_t rvi_92_address = (rvi_92_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_92_address, 1, 0, &rvi_92_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_92_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_93_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_93_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_93_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_94_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_94_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_94_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_95_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_95_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_95_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_96_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_96_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_96_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_97_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_97_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_97_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_98_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_98_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_98_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_99_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_99_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_99_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_100_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_100_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_100_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_101_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_101_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_101_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_102_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_102_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_102_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095a8: ;
    {
    uint64_t rvi_103_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_103_condition_value) != 0) return -1;
    if (rvi_103_condition_value != 0) { if (rvi_call(ctx, UINT64_C(0x50968e)) != 0) return -1; return 0; }
    }
rvi_label_00000000005095ae: ;
    {
    uint64_t rvi_104_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_104_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_104_a0_value + UINT64_C(0xfffffff8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_105_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_105_ptr_value) != 0) return -1;
      uint64_t rvi_105_loaded;
      uint64_t rvi_105_address = (rvi_105_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_105_address, 4, 0, &rvi_105_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_105_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_106_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_106_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_106_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_00000000005095b1: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_109_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_109_a0_value) != 0) return -1;
    uint64_t rvi_109_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_109_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (((rvi_109_a0_value & rvi_109_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_110_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_110_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_110_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_111_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_111_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_111_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_112_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_112_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_112_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_113_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_113_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_113_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_114_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_114_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_114_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_115_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_115_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_115_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095b3: ;
    {
    uint64_t rvi_116_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_116_condition_value) != 0) return -1;
    if (rvi_116_condition_value != 0) { if (rvi_call(ctx, UINT64_C(0x50968e)) != 0) return -1; return 0; }
    }
rvi_label_00000000005095b9: ;
    {
    uint64_t rvi_117_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_117_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_117_a0_value + UINT64_C(0xfffffffe)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_118_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_118_ptr_value) != 0) return -1;
      uint64_t rvi_118_loaded;
      uint64_t rvi_118_address = (rvi_118_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_118_address, 1, 0, &rvi_118_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_118_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_119_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_119_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_119_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_120_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_120_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_120_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_121_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_121_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_121_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_122_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_122_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_122_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_123_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_123_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_123_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_124_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_124_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_124_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_125_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_125_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_125_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_126_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_126_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_126_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_127_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_127_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_127_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_128_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_128_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_128_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095bd: ;
    {
    uint64_t rvi_129_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_129_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_129_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_130_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_130_condition_value) != 0) return -1;
    if (rvi_130_condition_value != 0) { if (rvi_call(ctx, UINT64_C(0x50968e)) != 0) return -1; return 0; }
    }
rvi_label_00000000005095c3: ;
    {
    uint64_t rvi_131_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_131_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_131_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_132_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_132_ptr_value) != 0) return -1;
      uint64_t rvi_132_loaded;
      uint64_t rvi_132_address = (rvi_132_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_132_address, 1, 0, &rvi_132_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_132_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_133_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_133_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_133_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_134_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_134_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_134_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_135_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_135_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_135_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_136_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_136_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_136_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_137_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_137_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_137_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_138_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_138_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_138_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_139_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_139_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_139_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_140_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_140_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_140_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_141_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_141_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_141_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_142_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_142_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_142_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095c7: ;
    {
    uint64_t rvi_143_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_143_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_143_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_144_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_144_condition_value) != 0) return -1;
    if (rvi_144_condition_value != 0) { if (rvi_call(ctx, UINT64_C(0x50968e)) != 0) return -1; return 0; }
    }
rvi_label_00000000005095cd: ;
    if (rvi_call(ctx, UINT64_C(0x42c9cc)) != 0) return -1;
    return 0;
rvi_label_00000000005095f0: ;
    {
    uint64_t rvi_146_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_146_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_146_a0_value + UINT64_C(0xad)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_147_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_147_ptr_value) != 0) return -1;
      uint64_t rvi_147_loaded;
      uint64_t rvi_147_address = (rvi_147_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_147_address, 1, 0, &rvi_147_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_147_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_148_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_148_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_148_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_149_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_149_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_149_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_150_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_150_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_150_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_151_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_151_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_151_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_152_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_152_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_152_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_153_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_153_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_153_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_154_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_154_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_154_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_155_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_155_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_155_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_156_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_156_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_156_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_157_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_157_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_157_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_00000000005095f7: ;
    {
    uint64_t rvi_158_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_158_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_158_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_00000000005095f9: ;
    {
    uint64_t rvi_159_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_159_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_159_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_160_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_160_condition_value) != 0) return -1;
    if (rvi_160_condition_value != 0) { goto rvi_label_000000000050960b; }
    }
rvi_label_00000000005095fb: ;
    {
    uint64_t rvi_161_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_161_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_161_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_162_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_162_ptr_value) != 0) return -1;
      uint64_t rvi_162_address = (rvi_162_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_162_address, 4, 0, UINT64_C(0x509600)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x5088e0), UINT32_C(0x509600), "ram") != 0) return -1;
    }
rvi_label_0000000000509600: ;
    {
    uint64_t rvi_164_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_164_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_164_a0_value + UINT64_C(0xe4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_165_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_165_ptr_value) != 0) return -1;
      uint64_t rvi_165_loaded;
      uint64_t rvi_165_address = (rvi_165_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_165_address, 4, 0, &rvi_165_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (rvi_165_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_166_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_166_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, (rvi_166_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_167_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_167_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_167_a0_value & rvi_mask(4)) < (UINT64_C(0x1) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_168_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_168_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_168_a0_value, UINT64_C(0x1), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_169_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x29), 4, 0, &rvi_169_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, (((rvi_169_a0_value - UINT64_C(0x1)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_170_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_170_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_170_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_171_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_171_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_171_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_172_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_172_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (((rvi_172_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_173_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_173_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_173_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_174_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_174_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_174_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_175_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_175_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_175_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509607: ;
    {
    uint64_t rvi_176_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_176_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_176_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_177_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_177_condition_value) != 0) return -1;
    if (rvi_177_condition_value != 0) { goto rvi_label_0000000000509615; }
    }
rvi_label_0000000000509609: ;
    {
    uint64_t rvi_178_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_178_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_178_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050960b: ;
    {
    uint64_t rvi_179_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_179_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_179_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_180_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_180_ptr_value) != 0) return -1;
      uint64_t rvi_180_address = (rvi_180_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_180_address, 4, 0, UINT64_C(0x509610)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x508970), UINT32_C(0x509610), "ram") != 0) return -1;
    }
rvi_label_0000000000509610: ;
    {
    goto rvi_label_0000000000509588;
    }
rvi_label_0000000000509615: ;
    {
    uint64_t rvi_183_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_183_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_183_a0_value + UINT64_C(0xed)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_184_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_184_ptr_value) != 0) return -1;
      uint64_t rvi_184_loaded;
      uint64_t rvi_184_address = (rvi_184_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_184_address, 1, 0, &rvi_184_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_184_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_185_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_185_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_185_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_186_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_186_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_186_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_187_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_187_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_187_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_188_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_188_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_188_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_189_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_189_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_189_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_190_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_190_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_190_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_191_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_191_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_191_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_192_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_192_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_192_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_193_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_193_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_193_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_194_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_194_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_194_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000050961c: ;
    {
    uint64_t rvi_195_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_195_condition_value) != 0) return -1;
    if (rvi_195_condition_value != 0) { goto rvi_label_0000000000509588; }
    }
rvi_label_0000000000509622: ;
    {
    uint64_t rvi_196_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_196_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_196_a0_value + UINT64_C(0xfffffffe)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_198_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_198_ptr_value) != 0) return -1;
    uint64_t rvi_198_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_198_value_value) != 0) return -1;
      uint64_t rvi_198_address = (rvi_198_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_198_address, 1, 0, rvi_198_value_value) != 0) return -1;
    }
rvi_label_0000000000509626: ;
    {
    goto rvi_label_0000000000509588;
    }
rvi_label_000000000050962b: ;
    {
    uint64_t rvi_200_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_200_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_200_a0_value + UINT64_C(0xad)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_201_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_201_ptr_value) != 0) return -1;
      uint64_t rvi_201_loaded;
      uint64_t rvi_201_address = (rvi_201_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_201_address, 1, 0, &rvi_201_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_201_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_202_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_202_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_202_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_203_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_203_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_203_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_204_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_204_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_204_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_205_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_205_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_205_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_206_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_206_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_206_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_207_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_207_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_207_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_208_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_208_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_208_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_209_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_209_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_209_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_210_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_210_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_210_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_211_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_211_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_211_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509632: ;
    {
    uint64_t rvi_212_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_212_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_212_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_0000000000509634: ;
    {
    uint64_t rvi_213_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_213_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, ((rvi_213_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_214_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_214_condition_value) != 0) return -1;
    if (rvi_214_condition_value != 0) { goto rvi_label_0000000000509651; }
    }
rvi_label_0000000000509636: ;
    {
    uint64_t rvi_215_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_215_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_215_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_216_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_216_ptr_value) != 0) return -1;
      uint64_t rvi_216_address = (rvi_216_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_216_address, 4, 0, UINT64_C(0x50963b)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x508900), UINT32_C(0x50963b), "ram") != 0) return -1;
    }
rvi_label_000000000050963b: ;
    {
    uint64_t rvi_218_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_218_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_218_a0_value + UINT64_C(0xed)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_219_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_219_ptr_value) != 0) return -1;
      uint64_t rvi_219_loaded;
      uint64_t rvi_219_address = (rvi_219_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_219_address, 1, 0, &rvi_219_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, (rvi_219_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_220_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x15), 1, 0, &rvi_220_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (rvi_220_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_221_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_221_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_221_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_222_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_222_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_222_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_223_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_223_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, (((rvi_223_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_224_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_224_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_224_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_225_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_225_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_225_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_226_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 1, 0, &rvi_226_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, (((rvi_226_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_227_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 1, 0, &rvi_227_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (rvi_popcount(rvi_227_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_228_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_228_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, (((rvi_228_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_229_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x22), 1, 0, &rvi_229_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_229_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_0000000000509642: ;
    {
    uint64_t rvi_230_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_230_condition_value) != 0) return -1;
    if (rvi_230_condition_value != 0) { goto rvi_label_000000000050958c; }
    }
rvi_label_0000000000509648: ;
    {
    uint64_t rvi_231_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_231_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_231_a0_value + UINT64_C(0xfffffffe)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_233_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_233_ptr_value) != 0) return -1;
    uint64_t rvi_233_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_233_value_value) != 0) return -1;
      uint64_t rvi_233_address = (rvi_233_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_233_address, 1, 0, rvi_233_value_value) != 0) return -1;
    }
rvi_label_000000000050964c: ;
    {
    goto rvi_label_000000000050958c;
    }
rvi_label_0000000000509651: ;
    {
    uint64_t rvi_235_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_235_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_235_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_236_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_236_ptr_value) != 0) return -1;
      uint64_t rvi_236_address = (rvi_236_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_236_address, 4, 0, UINT64_C(0x509656)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x508970), UINT32_C(0x509656), "ram") != 0) return -1;
    }
rvi_label_0000000000509656: ;
    {
    goto rvi_label_000000000050958c;
    }
rvi_label_000000000050965b: ;
    {
    uint64_t rvi_239_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_239_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_239_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000050965d: ;
    {
    uint64_t rvi_240_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_240_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_240_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_241_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_241_ptr_value) != 0) return -1;
      uint64_t rvi_241_address = (rvi_241_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_241_address, 4, 0, UINT64_C(0x509662)) != 0) return -1;
    }
    {
    if (rvi_call_x86_32(ctx, UINT64_C(0x508970), UINT32_C(0x509662), "ram") != 0) return -1;
    }
rvi_label_0000000000509662: ;
    {
    uint64_t rvi_243_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_243_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_243_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_245_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_245_ptr_value) != 0) return -1;
    uint64_t rvi_245_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_245_value_value) != 0) return -1;
      uint64_t rvi_245_address = (rvi_245_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_245_address, 1, 0, rvi_245_value_value) != 0) return -1;
    }
rvi_label_0000000000509666: ;
    {
    goto rvi_label_000000000050958c;
    }
    return 0;
}
