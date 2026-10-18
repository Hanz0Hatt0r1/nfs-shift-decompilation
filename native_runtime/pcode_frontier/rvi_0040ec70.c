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
        if (exponent == 0) exponent = 1;
        else if (!(significand >> 63)) return -1;
        binary_exponent = (int)exponent - 16383 - 63;
        *value = ldexpl((long double)significand, binary_exponent);
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
    if (isnan(a) || isnan(b)) return 0;
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
/* Generated from raw P-code for FUN_0040ec70 (0x0040ec70). */
int rvi_0040ec70(RviPcodeContext *ctx) {
    uint8_t _unique[60] = {0};
    const size_t _unique_size = 60;
    if (!ctx) return -1;
rvi_label_000000000040ec70: ;
    {
    uint64_t rvi_0_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_0_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 4, 0, (rvi_0_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_1_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_1_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_1_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_2_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_2_ptr_value) != 0) return -1;
    uint64_t rvi_2_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 4, 0, &rvi_2_value_value) != 0) return -1;
      uint64_t rvi_2_address = (rvi_2_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_2_address, 4, 0, rvi_2_value_value) != 0) return -1;
    }
rvi_label_000000000040ec71: ;
    {
    uint64_t rvi_3_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_3_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_3_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ec73: ;
    {
    uint64_t rvi_4_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_4_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, (rvi_4_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_5_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_5_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_5_a0_value & rvi_mask(4)) < (UINT64_C(0x1) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_6_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_6_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_6_a0_value, UINT64_C(0x1), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_7_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_7_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, (((rvi_7_a0_value - UINT64_C(0x1)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_8_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_8_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_8_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_9_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_9_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_9_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_10_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_10_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_10_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_11_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_11_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_11_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_12_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_12_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_12_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_13_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_13_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_13_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ec76: ;
    {
    uint64_t rvi_14_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_14_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, ((rvi_14_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_15_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_15_condition_value) != 0) return -1;
    if (rvi_15_condition_value != 0) { goto rvi_label_000000000040ecaa; }
    }
rvi_label_000000000040ec78: ;
    {
    uint64_t rvi_16_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xbc1854), 4, 0, &rvi_16_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, (rvi_16_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_17_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_17_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_17_a0_value & rvi_mask(4)) < (UINT64_C(0x0) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_18_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_18_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_18_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_19_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_19_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, (((rvi_19_a0_value - UINT64_C(0x0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_20_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_20_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_20_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_21_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_21_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_21_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_22_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_22_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_22_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_23_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_23_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_23_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_24_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_24_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_24_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_25_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_25_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_25_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ec7f: ;
    {
    uint64_t rvi_26_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_26_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, ((rvi_26_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_27_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x10), 1, 0, &rvi_27_condition_value) != 0) return -1;
    if (rvi_27_condition_value != 0) { goto rvi_label_000000000040ecaa; }
    }
rvi_label_000000000040ec81: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x34), 4, 0, (UINT64_C(0x14e0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_29_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_29_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_29_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_30_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_30_ptr_value) != 0) return -1;
    uint64_t rvi_30_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x34), 4, 0, &rvi_30_value_value) != 0) return -1;
      uint64_t rvi_30_address = (rvi_30_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_30_address, 4, 0, rvi_30_value_value) != 0) return -1;
    }
rvi_label_000000000040ec86: ;
    {
    uint64_t rvi_31_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_31_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_31_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_32_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_32_ptr_value) != 0) return -1;
      uint64_t rvi_32_address = (rvi_32_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_32_address, 4, 0, UINT64_C(0x40ec8b)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x8868c0)) != 0) return -1;
    }
rvi_label_000000000040ec8b: ;
    {
    uint64_t rvi_34_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_34_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (rvi_carry(rvi_34_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_35_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_35_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_carry(rvi_35_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_36_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_36_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_36_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_37_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_37_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_37_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_38_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_38_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_38_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_39_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_39_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_39_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_40_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_40_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_40_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_41_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_41_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_41_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_42_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_42_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_42_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ec8e: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_45_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_45_a0_value) != 0) return -1;
    uint64_t rvi_45_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_45_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x38), 4, 0, (((rvi_45_a0_value & rvi_45_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_46_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x38), 4, 0, &rvi_46_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_46_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_47_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x38), 4, 0, &rvi_47_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_47_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_48_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x38), 4, 0, &rvi_48_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_48_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_49_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_49_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_49_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_50_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_50_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_50_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_51_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_51_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_51_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ec90: ;
    {
    uint64_t rvi_52_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_52_condition_value) != 0) return -1;
    if (rvi_52_condition_value != 0) { goto rvi_label_000000000040eca0; }
    }
rvi_label_000000000040ec92: ;
    {
    uint64_t rvi_53_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_53_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_53_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ec94: ;
    {
    uint64_t rvi_54_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_54_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_54_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_55_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_55_ptr_value) != 0) return -1;
      uint64_t rvi_55_address = (rvi_55_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_55_address, 4, 0, UINT64_C(0x40ec99)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x5499d0)) != 0) return -1;
    }
rvi_label_000000000040ec99: ;
    {
    uint64_t rvi_57_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_57_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xbc1854), 4, 0, (rvi_57_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ec9e: ;
    {
    goto rvi_label_000000000040ecaa;
    }
rvi_label_000000000040eca0: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xbc1854), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecaa: ;
    {
    uint64_t rvi_60_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xb811d4), 4, 0, &rvi_60_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 4, 0, (rvi_60_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_61_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_61_a0_value) != 0) return -1;
    uint64_t rvi_61_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 4, 0, &rvi_61_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_61_a0_value & rvi_mask(4)) < (rvi_61_a1_value & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_62_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_62_a0_value) != 0) return -1;
    uint64_t rvi_62_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 4, 0, &rvi_62_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_62_a0_value, rvi_62_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_63_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_63_a0_value) != 0) return -1;
    uint64_t rvi_63_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x28), 4, 0, &rvi_63_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 4, 0, (((rvi_63_a0_value - rvi_63_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_64_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 4, 0, &rvi_64_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_64_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_65_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 4, 0, &rvi_65_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_65_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_66_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 4, 0, &rvi_66_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_66_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_67_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_67_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_67_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_68_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_68_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_68_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_69_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_69_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_69_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ecb0: ;
    {
    uint64_t rvi_70_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_70_condition_value) != 0) return -1;
    if (rvi_70_condition_value != 0) { goto rvi_label_000000000040ecfe; }
    }
rvi_label_000000000040ecb2: ;
    {
    uint64_t rvi_71_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xc26058), 4, 0, &rvi_71_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_71_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecb8: ;
    {
    uint64_t rvi_72_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_72_ptr_value) != 0) return -1;
      uint64_t rvi_72_loaded;
      uint64_t rvi_72_address = (rvi_72_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_72_address, 4, 0, &rvi_72_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_72_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_73_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_73_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_73_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecba: ;
    {
    uint64_t rvi_74_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_74_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_74_a0_value + UINT64_C(0x10)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_75_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_75_ptr_value) != 0) return -1;
      uint64_t rvi_75_loaded;
      uint64_t rvi_75_address = (rvi_75_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_75_address, 4, 0, &rvi_75_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_75_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_76_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_76_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_76_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecbd: ;
    {
    uint64_t rvi_77_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_77_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, (rvi_77_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_78_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_78_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_78_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_79_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_79_ptr_value) != 0) return -1;
      uint64_t rvi_79_address = (rvi_79_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_79_address, 4, 0, UINT64_C(0x40ecbf)) != 0) return -1;
    }
    {
    uint64_t rvi_80_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, &rvi_80_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_80_call_target_value) != 0) return -1;
    }
rvi_label_000000000040ecbf: ;
    {
    uint64_t rvi_81_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xb811d4), 4, 0, &rvi_81_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_81_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecc4: ;
    {
    uint64_t rvi_82_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_82_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, (rvi_82_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_83_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_83_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_83_a0_value & rvi_mask(4)) < (UINT64_C(0x4) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_84_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_84_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_84_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_85_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_85_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, (((rvi_85_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_86_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_86_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_86_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_87_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_87_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_87_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_88_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_88_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_88_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_89_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_89_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_89_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_90_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_90_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_90_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_91_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_91_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_91_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ecc7: ;
    {
    uint64_t rvi_92_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, &rvi_92_a0_value) != 0) return -1;
    uint64_t rvi_92_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, &rvi_92_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, ((rvi_92_a0_value == rvi_92_a1_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_93_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, &rvi_93_condition_value) != 0) return -1;
    if (rvi_93_condition_value != 0) { goto rvi_label_000000000040ecd7; }
    }
rvi_label_000000000040ecc9: ;
    {
    uint64_t rvi_94_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_94_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_94_a0_value * UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_95_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_95_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, (((UINT64_C(0xbc1850) + rvi_95_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_96_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, &rvi_96_ptr_value) != 0) return -1;
      uint64_t rvi_96_loaded;
      uint64_t rvi_96_address = (rvi_96_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_96_address, 4, 0, &rvi_96_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_96_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_97_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_97_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_97_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecd0: ;
    {
    uint64_t rvi_98_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_98_ptr_value) != 0) return -1;
      uint64_t rvi_98_loaded;
      uint64_t rvi_98_address = (rvi_98_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_98_address, 4, 0, &rvi_98_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_98_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_99_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_99_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_99_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecd2: ;
    {
    uint64_t rvi_100_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_100_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_100_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_101_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_101_ptr_value) != 0) return -1;
      uint64_t rvi_101_loaded;
      uint64_t rvi_101_address = (rvi_101_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_101_address, 4, 0, &rvi_101_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_101_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_102_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_102_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_102_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecd5: ;
    {
    uint64_t rvi_103_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_103_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, (rvi_103_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_104_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_104_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_104_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_105_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_105_ptr_value) != 0) return -1;
      uint64_t rvi_105_address = (rvi_105_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_105_address, 4, 0, UINT64_C(0x40ecd7)) != 0) return -1;
    }
    {
    uint64_t rvi_106_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, &rvi_106_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_106_call_target_value) != 0) return -1;
    }
rvi_label_000000000040ecd7: ;
    {
    uint64_t rvi_107_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_107_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, (rvi_107_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_108_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_108_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_108_a0_value & rvi_mask(4)) < (UINT64_C(0x4) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_109_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_109_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_109_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_110_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x20), 4, 0, &rvi_110_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, (((rvi_110_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_111_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_111_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_111_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_112_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_112_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_112_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_113_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x24), 4, 0, &rvi_113_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, (((rvi_113_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_114_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x16), 4, 0, &rvi_114_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, (rvi_popcount(rvi_114_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_115_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1a), 1, 0, &rvi_115_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, (((rvi_115_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_116_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 1, 0, &rvi_116_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_116_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000040ecda: ;
    {
    uint64_t rvi_117_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_117_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xb811d4), 4, 0, (rvi_117_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ece0: ;
    {
    uint64_t rvi_118_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, &rvi_118_a0_value) != 0) return -1;
    uint64_t rvi_118_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, &rvi_118_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, ((rvi_118_a0_value == rvi_118_a1_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_119_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, &rvi_119_condition_value) != 0) return -1;
    if (rvi_119_condition_value != 0) { goto rvi_label_000000000040ecf0; }
    }
rvi_label_000000000040ece2: ;
    {
    uint64_t rvi_120_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_120_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_120_a0_value * UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_121_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_121_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, (((UINT64_C(0xbc1850) + rvi_121_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_122_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, &rvi_122_ptr_value) != 0) return -1;
      uint64_t rvi_122_loaded;
      uint64_t rvi_122_address = (rvi_122_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_122_address, 4, 0, &rvi_122_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_122_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_123_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_123_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_123_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ece9: ;
    {
    uint64_t rvi_124_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_124_ptr_value) != 0) return -1;
      uint64_t rvi_124_loaded;
      uint64_t rvi_124_address = (rvi_124_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_124_address, 4, 0, &rvi_124_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_124_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_125_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_125_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_125_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040eceb: ;
    {
    uint64_t rvi_126_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_126_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_126_a0_value + UINT64_C(0x10)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_127_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_127_ptr_value) != 0) return -1;
      uint64_t rvi_127_loaded;
      uint64_t rvi_127_address = (rvi_127_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_127_address, 4, 0, &rvi_127_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_127_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_128_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_128_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_128_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecee: ;
    {
    uint64_t rvi_129_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_129_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, (rvi_129_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_130_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_130_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_130_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_131_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_131_ptr_value) != 0) return -1;
      uint64_t rvi_131_address = (rvi_131_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_131_address, 4, 0, UINT64_C(0x40ecf0)) != 0) return -1;
    }
    {
    uint64_t rvi_132_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 4, 0, &rvi_132_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_132_call_target_value) != 0) return -1;
    }
rvi_label_000000000040ecf0: ;
    {
    uint64_t rvi_133_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "ram", UINT64_C(0xc26058), 4, 0, &rvi_133_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_133_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecf6: ;
    {
    uint64_t rvi_134_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_134_ptr_value) != 0) return -1;
      uint64_t rvi_134_loaded;
      uint64_t rvi_134_address = (rvi_134_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_134_address, 4, 0, &rvi_134_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_134_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_135_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_135_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_135_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecf8: ;
    {
    uint64_t rvi_136_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_136_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_136_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_137_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_137_ptr_value) != 0) return -1;
      uint64_t rvi_137_loaded;
      uint64_t rvi_137_address = (rvi_137_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_137_address, 4, 0, &rvi_137_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, (rvi_137_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_138_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 4, 0, &rvi_138_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_138_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecfb: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_140_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_140_ptr_value) != 0) return -1;
      uint64_t rvi_140_loaded;
      uint64_t rvi_140_address = (rvi_140_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_140_address, 4, 0, &rvi_140_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, (rvi_140_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_141_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_141_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_141_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_142_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, &rvi_142_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_142_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecfc: ;
    {
    uint64_t rvi_143_branch_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_143_branch_target_value) != 0) return -1;
    switch (rvi_143_branch_target_value) {
    case UINT64_C(0x40ec70): goto rvi_label_000000000040ec70;
    case UINT64_C(0x40ec71): goto rvi_label_000000000040ec71;
    case UINT64_C(0x40ec73): goto rvi_label_000000000040ec73;
    case UINT64_C(0x40ec76): goto rvi_label_000000000040ec76;
    case UINT64_C(0x40ec78): goto rvi_label_000000000040ec78;
    case UINT64_C(0x40ec7f): goto rvi_label_000000000040ec7f;
    case UINT64_C(0x40ec81): goto rvi_label_000000000040ec81;
    case UINT64_C(0x40ec86): goto rvi_label_000000000040ec86;
    case UINT64_C(0x40ec8b): goto rvi_label_000000000040ec8b;
    case UINT64_C(0x40ec8e): goto rvi_label_000000000040ec8e;
    case UINT64_C(0x40ec90): goto rvi_label_000000000040ec90;
    case UINT64_C(0x40ec92): goto rvi_label_000000000040ec92;
    case UINT64_C(0x40ec94): goto rvi_label_000000000040ec94;
    case UINT64_C(0x40ec99): goto rvi_label_000000000040ec99;
    case UINT64_C(0x40ec9e): goto rvi_label_000000000040ec9e;
    case UINT64_C(0x40eca0): goto rvi_label_000000000040eca0;
    case UINT64_C(0x40ecaa): goto rvi_label_000000000040ecaa;
    case UINT64_C(0x40ecb0): goto rvi_label_000000000040ecb0;
    case UINT64_C(0x40ecb2): goto rvi_label_000000000040ecb2;
    case UINT64_C(0x40ecb8): goto rvi_label_000000000040ecb8;
    case UINT64_C(0x40ecba): goto rvi_label_000000000040ecba;
    case UINT64_C(0x40ecbd): goto rvi_label_000000000040ecbd;
    case UINT64_C(0x40ecbf): goto rvi_label_000000000040ecbf;
    case UINT64_C(0x40ecc4): goto rvi_label_000000000040ecc4;
    case UINT64_C(0x40ecc7): goto rvi_label_000000000040ecc7;
    case UINT64_C(0x40ecc9): goto rvi_label_000000000040ecc9;
    case UINT64_C(0x40ecd0): goto rvi_label_000000000040ecd0;
    case UINT64_C(0x40ecd2): goto rvi_label_000000000040ecd2;
    case UINT64_C(0x40ecd5): goto rvi_label_000000000040ecd5;
    case UINT64_C(0x40ecd7): goto rvi_label_000000000040ecd7;
    case UINT64_C(0x40ecda): goto rvi_label_000000000040ecda;
    case UINT64_C(0x40ece0): goto rvi_label_000000000040ece0;
    case UINT64_C(0x40ece2): goto rvi_label_000000000040ece2;
    case UINT64_C(0x40ece9): goto rvi_label_000000000040ece9;
    case UINT64_C(0x40eceb): goto rvi_label_000000000040eceb;
    case UINT64_C(0x40ecee): goto rvi_label_000000000040ecee;
    case UINT64_C(0x40ecf0): goto rvi_label_000000000040ecf0;
    case UINT64_C(0x40ecf6): goto rvi_label_000000000040ecf6;
    case UINT64_C(0x40ecf8): goto rvi_label_000000000040ecf8;
    case UINT64_C(0x40ecfb): goto rvi_label_000000000040ecfb;
    case UINT64_C(0x40ecfc): goto rvi_label_000000000040ecfc;
    case UINT64_C(0x40ecfe): goto rvi_label_000000000040ecfe;
    case UINT64_C(0x40ecff): goto rvi_label_000000000040ecff;
    default:
        if (rvi_call(ctx, rvi_143_branch_target_value) != 0) return -1;
        return 0;
    }
    }
rvi_label_000000000040ecfe: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_145_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_145_ptr_value) != 0) return -1;
      uint64_t rvi_145_loaded;
      uint64_t rvi_145_address = (rvi_145_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_145_address, 4, 0, &rvi_145_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, (rvi_145_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_146_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_146_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_146_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_147_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x30), 4, 0, &rvi_147_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_147_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000040ecff: ;
    {
    uint64_t rvi_148_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_148_ptr_value) != 0) return -1;
      uint64_t rvi_148_loaded;
      uint64_t rvi_148_address = (rvi_148_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_148_address, 4, 0, &rvi_148_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x284), 4, 0, (rvi_148_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_149_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_149_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_149_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    return 0;
    }
    return 0;
}
