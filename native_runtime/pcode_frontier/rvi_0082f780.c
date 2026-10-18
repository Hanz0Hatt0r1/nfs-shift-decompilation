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
/* Generated from raw P-code for FUN_0082f780 (0x0082f780). */
int rvi_0082f780(RviPcodeContext *ctx) {
    uint8_t _unique[100] = {0};
    const size_t _unique_size = 100;
    if (!ctx) return -1;
rvi_label_000000000082f780: ;
    {
    uint64_t rvi_0_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_0_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_0_a0_value) & rvi_mask(4)) != 0) return -1;
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
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_2_value_value) != 0) return -1;
      uint64_t rvi_2_address = (rvi_2_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_2_address, 4, 0, rvi_2_value_value) != 0) return -1;
    }
rvi_label_000000000082f781: ;
    {
    uint64_t rvi_3_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_3_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, (rvi_3_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f783: ;
    {
    uint64_t rvi_4_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_4_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_4_a0_value & rvi_mask(4)) < (UINT64_C(0x8) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_5_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_5_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_5_a0_value, UINT64_C(0x8), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_6_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_6_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_6_a0_value - UINT64_C(0x8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_7_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_7_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_7_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_8_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_8_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_8_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_9_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_9_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_9_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_10_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_10_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_10_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_11_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_11_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_11_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_12_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_12_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_12_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f786: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_15_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_15_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_15_a0_value & UINT64_C(0xfffffff0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_16_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_16_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_16_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_17_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_17_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_17_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_18_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_18_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_18_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_19_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_19_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_19_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_20_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_20_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_20_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_21_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_21_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_21_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f789: ;
    {
    uint64_t rvi_22_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_22_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (rvi_carry(rvi_22_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_23_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_23_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_carry(rvi_23_a0_value, UINT64_C(0x4), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_24_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_24_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_24_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_25_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_25_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_25_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_26_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_26_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_26_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_27_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_27_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_27_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_28_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_28_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_28_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_29_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_29_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_29_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_30_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_30_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_30_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f78c: ;
    {
    uint64_t rvi_31_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_31_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_31_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_32_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_32_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_32_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_33_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_33_ptr_value) != 0) return -1;
    uint64_t rvi_33_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_33_value_value) != 0) return -1;
      uint64_t rvi_33_address = (rvi_33_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_33_address, 4, 0, rvi_33_value_value) != 0) return -1;
    }
rvi_label_000000000082f78d: ;
    {
    uint64_t rvi_34_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_34_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_34_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_35_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_35_ptr_value) != 0) return -1;
      uint64_t rvi_35_loaded;
      uint64_t rvi_35_address = (rvi_35_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_35_address, 4, 0, &rvi_35_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_35_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_36_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_36_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, (rvi_36_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f790: ;
    {
    uint64_t rvi_37_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_37_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, (((UINT64_C(0x4) + rvi_37_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_38_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_38_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_38_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_39_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 4, 0, &rvi_39_ptr_value) != 0) return -1;
    uint64_t rvi_39_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_39_value_value) != 0) return -1;
      uint64_t rvi_39_address = (rvi_39_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_39_address, 4, 0, rvi_39_value_value) != 0) return -1;
    }
rvi_label_000000000082f794: ;
    {
    uint64_t rvi_40_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_40_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, (rvi_40_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f796: ;
    {
    uint64_t rvi_41_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_41_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_41_a0_value & rvi_mask(4)) < (UINT64_C(0x28) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_42_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_42_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_42_a0_value, UINT64_C(0x28), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_43_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_43_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_43_a0_value - UINT64_C(0x28)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_44_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_44_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_44_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_45_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_45_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_45_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_46_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_46_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_46_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_47_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_47_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_47_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_48_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_48_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_48_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_49_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_49_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_49_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f799: ;
    {
    uint64_t rvi_50_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_50_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_50_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_51_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_51_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_51_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_52_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_52_ptr_value) != 0) return -1;
    uint64_t rvi_52_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_52_value_value) != 0) return -1;
      uint64_t rvi_52_address = (rvi_52_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_52_address, 4, 0, rvi_52_value_value) != 0) return -1;
    }
rvi_label_000000000082f79a: ;
    {
    uint64_t rvi_53_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_53_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_53_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f79c: ;
    {
    uint64_t rvi_54_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_54_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_54_a0_value + UINT64_C(0x478)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_55_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_55_ptr_value) != 0) return -1;
      uint64_t rvi_55_loaded;
      uint64_t rvi_55_address = (rvi_55_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_55_address, 4, 0, &rvi_55_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_55_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_56_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_56_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, (rvi_56_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_57_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_57_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_57_a0_value & rvi_mask(4)) < (UINT64_C(0x0) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_58_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_58_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_58_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_59_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2d), 4, 0, &rvi_59_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, (((rvi_59_a0_value - UINT64_C(0x0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_60_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_60_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_60_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_61_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_61_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_61_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_62_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x31), 4, 0, &rvi_62_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_62_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_63_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_63_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_63_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_64_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_64_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_64_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_65_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_65_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_65_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7a3: ;
    {
    uint64_t rvi_66_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_66_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_66_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_67_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_67_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_67_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_68_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_68_ptr_value) != 0) return -1;
    uint64_t rvi_68_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_68_value_value) != 0) return -1;
      uint64_t rvi_68_address = (rvi_68_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_68_address, 4, 0, rvi_68_value_value) != 0) return -1;
    }
rvi_label_000000000082f7a4: ;
    {
    uint64_t rvi_69_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_69_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_69_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_70_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_70_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_70_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_71_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_71_ptr_value) != 0) return -1;
    uint64_t rvi_71_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_71_value_value) != 0) return -1;
      uint64_t rvi_71_address = (rvi_71_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_71_address, 4, 0, rvi_71_value_value) != 0) return -1;
    }
rvi_label_000000000082f7a7: ;
    {
    uint64_t rvi_72_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_72_condition_value) != 0) return -1;
    if (rvi_72_condition_value != 0) { goto rvi_label_000000000082fa3c; }
    }
rvi_label_000000000082f7ad: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x3d), 4, 0, (UINT64_C(0xb18058)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_74_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_74_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_74_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_75_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_75_ptr_value) != 0) return -1;
    uint64_t rvi_75_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x3d), 4, 0, &rvi_75_value_value) != 0) return -1;
      uint64_t rvi_75_address = (rvi_75_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_75_address, 4, 0, rvi_75_value_value) != 0) return -1;
    }
rvi_label_000000000082f7b2: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x3d), 4, 0, (UINT64_C(0xffff0000)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_77_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_77_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_77_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_78_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_78_ptr_value) != 0) return -1;
    uint64_t rvi_78_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x3d), 4, 0, &rvi_78_value_value) != 0) return -1;
      uint64_t rvi_78_address = (rvi_78_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_78_address, 4, 0, rvi_78_value_value) != 0) return -1;
    }
rvi_label_000000000082f7b7: ;
    {
    uint64_t rvi_79_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_79_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_79_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_80_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_80_ptr_value) != 0) return -1;
      uint64_t rvi_80_address = (rvi_80_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_80_address, 4, 0, UINT64_C(0x82f7bc)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x923628)) != 0) return -1;
    }
rvi_label_000000000082f7bc: ;
    {
    uint64_t rvi_82_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_82_ptr_value) != 0) return -1;
      uint64_t rvi_82_loaded;
      uint64_t rvi_82_address = (rvi_82_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_82_address, 4, 0, &rvi_82_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_82_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_83_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_83_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_83_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7be: ;
    {
    uint64_t rvi_84_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_84_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_84_a0_value + UINT64_C(0x294)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_85_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_85_ptr_value) != 0) return -1;
      uint64_t rvi_85_loaded;
      uint64_t rvi_85_address = (rvi_85_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_85_address, 4, 0, &rvi_85_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_85_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_86_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_86_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_86_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7c4: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_89_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_89_a0_value) != 0) return -1;
    uint64_t rvi_89_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_89_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (((rvi_89_a0_value ^ rvi_89_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_90_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_90_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_90_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_91_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_91_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_91_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_92_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_92_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_92_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_93_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_93_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_93_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_94_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_94_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_94_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_95_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_95_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_95_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7c6: ;
    {
    uint64_t rvi_96_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_96_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_96_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7c8: ;
    {
    uint64_t rvi_97_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_97_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_97_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_98_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_98_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_98_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_99_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_99_ptr_value) != 0) return -1;
      uint64_t rvi_99_address = (rvi_99_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_99_address, 4, 0, UINT64_C(0x82f7ca)) != 0) return -1;
    }
    {
    uint64_t rvi_100_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_100_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_100_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f7ca: ;
    {
    uint64_t rvi_101_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_101_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_101_a0_value + UINT64_C(0x1a98)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_102_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_102_ptr_value) != 0) return -1;
      uint64_t rvi_102_loaded;
      uint64_t rvi_102_address = (rvi_102_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_102_address, 4, 0, &rvi_102_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_102_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_103_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_103_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_103_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7d0: ;
    {
    uint64_t rvi_104_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_104_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_104_a0_value + UINT64_C(0x1)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_105_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_105_ptr_value) != 0) return -1;
      uint64_t rvi_105_loaded;
      uint64_t rvi_105_address = (rvi_105_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_105_address, 1, 0, &rvi_105_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 1, 0, (rvi_105_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_106_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 1, 0, &rvi_106_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, (rvi_106_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_107_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_107_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_107_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_108_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_108_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_108_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_109_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_109_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, (((rvi_109_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_110_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_110_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_110_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_111_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_111_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_111_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_112_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_112_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (((rvi_112_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_113_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_113_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_113_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_114_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_114_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_114_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_115_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_115_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_115_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7d4: ;
    {
    uint64_t rvi_116_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_116_condition_value) != 0) return -1;
    if (rvi_116_condition_value != 0) { goto rvi_label_000000000082f7dd; }
    }
rvi_label_000000000082f7d6: ;
    {
    uint64_t rvi_117_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_117_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_117_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7d8: ;
    {
    uint64_t rvi_118_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_118_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_118_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_119_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_119_ptr_value) != 0) return -1;
      uint64_t rvi_119_address = (rvi_119_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_119_address, 4, 0, UINT64_C(0x82f7dd)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x843aa0)) != 0) return -1;
    }
rvi_label_000000000082f7dd: ;
    {
    uint64_t rvi_121_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_121_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_121_a0_value + UINT64_C(0x1c)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_122_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_122_ptr_value) != 0) return -1;
      uint64_t rvi_122_loaded;
      uint64_t rvi_122_address = (rvi_122_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_122_address, 4, 0, &rvi_122_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_122_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_123_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_123_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_123_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7e0: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_126_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_126_a0_value) != 0) return -1;
    uint64_t rvi_126_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_126_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, (((rvi_126_a0_value & rvi_126_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_127_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_127_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_127_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_128_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_128_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_128_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_129_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_129_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_129_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_130_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_130_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_130_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_131_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_131_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_131_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_132_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_132_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_132_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7e2: ;
    {
    uint64_t rvi_133_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_133_condition_value) != 0) return -1;
    if (rvi_133_condition_value != 0) { goto rvi_label_000000000082f7f7; }
    }
rvi_label_000000000082f7e4: ;
    {
    uint64_t rvi_134_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_134_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_134_a0_value + UINT64_C(0x24)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_135_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_135_ptr_value) != 0) return -1;
      uint64_t rvi_135_loaded;
      uint64_t rvi_135_address = (rvi_135_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_135_address, 4, 0, &rvi_135_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_135_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_136_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_136_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_136_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7e7: ;
    {
    uint64_t rvi_137_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_137_a0_value) != 0) return -1;
    uint64_t rvi_137_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_137_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (rvi_carry(rvi_137_a0_value, rvi_137_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_138_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_138_a0_value) != 0) return -1;
    uint64_t rvi_138_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_138_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_carry(rvi_138_a0_value, rvi_138_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_139_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_139_a0_value) != 0) return -1;
    uint64_t rvi_139_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_139_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (((rvi_139_a0_value + rvi_139_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_140_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_140_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_140_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_141_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_141_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_141_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_142_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_142_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_142_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_143_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_143_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_143_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_144_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_144_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_144_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_145_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_145_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_145_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7e9: ;
    {
    uint64_t rvi_146_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_146_a0_value) != 0) return -1;
    uint64_t rvi_146_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_146_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (rvi_carry(rvi_146_a0_value, rvi_146_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_147_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_147_a0_value) != 0) return -1;
    uint64_t rvi_147_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_147_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_carry(rvi_147_a0_value, rvi_147_a1_value, 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_148_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_148_a0_value) != 0) return -1;
    uint64_t rvi_148_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_148_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (((rvi_148_a0_value + rvi_148_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_149_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_149_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_149_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_150_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_150_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_150_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_151_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_151_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_151_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_152_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_152_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_152_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_153_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_153_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_153_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_154_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_154_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_154_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7eb: ;
    {
    uint64_t rvi_155_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_155_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_155_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_156_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_156_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_156_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_157_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_157_ptr_value) != 0) return -1;
    uint64_t rvi_157_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_157_value_value) != 0) return -1;
      uint64_t rvi_157_address = (rvi_157_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_157_address, 4, 0, rvi_157_value_value) != 0) return -1;
    }
rvi_label_000000000082f7ec: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_159_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_159_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_159_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_160_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_160_ptr_value) != 0) return -1;
    uint64_t rvi_160_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_160_value_value) != 0) return -1;
      uint64_t rvi_160_address = (rvi_160_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_160_address, 4, 0, rvi_160_value_value) != 0) return -1;
    }
rvi_label_000000000082f7ee: ;
    {
    uint64_t rvi_161_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_161_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_161_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_162_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_162_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_162_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_163_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_163_ptr_value) != 0) return -1;
    uint64_t rvi_163_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_163_value_value) != 0) return -1;
      uint64_t rvi_163_address = (rvi_163_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_163_address, 4, 0, rvi_163_value_value) != 0) return -1;
    }
rvi_label_000000000082f7ef: ;
    {
    uint64_t rvi_164_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_164_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_164_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_165_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_165_ptr_value) != 0) return -1;
      uint64_t rvi_165_address = (rvi_165_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_165_address, 4, 0, UINT64_C(0x82f7f4)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x9015b0)) != 0) return -1;
    }
rvi_label_000000000082f7f4: ;
    {
    uint64_t rvi_167_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_167_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (rvi_carry(rvi_167_a0_value, UINT64_C(0xc), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_168_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_168_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_carry(rvi_168_a0_value, UINT64_C(0xc), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_169_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_169_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_169_a0_value + UINT64_C(0xc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_170_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_170_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_170_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_171_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_171_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_171_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_172_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_172_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_172_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_173_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_173_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_173_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_174_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_174_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_174_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_175_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_175_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_175_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f7f7: ;
    {
    uint64_t rvi_176_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_176_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_176_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_177_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_177_ptr_value) != 0) return -1;
      uint64_t rvi_177_loaded;
      uint64_t rvi_177_address = (rvi_177_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_177_address, 4, 0, &rvi_177_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_177_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_178_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_178_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_178_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f7fa: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_180_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_180_ptr_value) != 0) return -1;
    uint64_t rvi_180_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, &rvi_180_value_value) != 0) return -1;
      uint64_t rvi_180_address = (rvi_180_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_180_address, 1, 0, rvi_180_value_value) != 0) return -1;
    }
rvi_label_000000000082f7fd: ;
    {
    uint64_t rvi_181_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_181_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_181_a0_value + UINT64_C(0x698)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_182_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_182_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_182_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_183_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_183_ptr_value) != 0) return -1;
    uint64_t rvi_183_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_183_value_value) != 0) return -1;
      uint64_t rvi_183_address = (rvi_183_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_183_address, 4, 0, rvi_183_value_value) != 0) return -1;
    }
rvi_label_000000000082f803: ;
    {
    uint64_t rvi_184_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_184_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_184_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_185_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_185_ptr_value) != 0) return -1;
      uint64_t rvi_185_address = (rvi_185_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_185_address, 4, 0, UINT64_C(0x82f808)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x853620)) != 0) return -1;
    }
rvi_label_000000000082f808: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_189_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_189_a0_value) != 0) return -1;
    uint64_t rvi_189_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_189_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, (((rvi_189_a0_value & rvi_189_a1_value) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_190_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_190_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_190_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_191_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_191_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_191_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_192_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_192_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (((rvi_192_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_193_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_193_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_193_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_194_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_194_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_194_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_195_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_195_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_195_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f80a: ;
    {
    uint64_t rvi_196_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_196_condition_value) != 0) return -1;
    if (rvi_196_condition_value != 0) { goto rvi_label_000000000082fa37; }
    }
rvi_label_000000000082f810: ;
    {
    uint64_t rvi_197_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_197_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_197_a0_value + UINT64_C(0x8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_198_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_198_ptr_value) != 0) return -1;
      uint64_t rvi_198_loaded;
      uint64_t rvi_198_address = (rvi_198_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_198_address, 1, 0, &rvi_198_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 1, 0, (rvi_198_loaded) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_199_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 1, 0, &rvi_199_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, (rvi_199_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_200_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_200_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_200_a0_value & rvi_mask(1)) < (UINT64_C(0x0) & rvi_mask(1)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_201_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_201_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_201_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_202_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2b), 1, 0, &rvi_202_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, (((rvi_202_a0_value - UINT64_C(0x0)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_203_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_203_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_203_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_204_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_204_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_204_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_205_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x2c), 1, 0, &rvi_205_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (((rvi_205_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_206_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_206_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_206_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_207_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_207_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_207_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_208_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_208_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_208_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f814: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f814)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_210_result[10];
    if (rvi_float80_from_integer(UINT64_C(0x0), 4, rvi_210_result) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x50), 10, rvi_210_result) != 0) return -1;
    }
    {
    uint8_t rvi_211_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_211_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_211_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_212_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_212_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_212_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_213_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_213_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_213_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_214_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_214_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_214_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_215_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_215_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_215_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_216_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_216_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_216_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_217_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_217_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_217_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_218_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x50), 10, rvi_218_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_218_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f816: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f816)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_220_result[10];
    if (rvi_float80_from_integer(UINT64_C(0x1), 4, rvi_220_result) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x46), 10, rvi_220_result) != 0) return -1;
    }
    {
    uint8_t rvi_221_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_221_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_221_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_222_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_222_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_222_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_223_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_223_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_223_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_224_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_224_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_224_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_225_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_225_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_225_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_226_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_226_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_226_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_227_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_227_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_227_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_228_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x46), 10, rvi_228_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_228_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f818: ;
    {
    uint64_t rvi_229_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_229_condition_value) != 0) return -1;
    if (rvi_229_condition_value != 0) { goto rvi_label_000000000082f859; }
    }
rvi_label_000000000082f81a: ;
    {
    uint64_t rvi_230_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_230_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_230_a0_value + UINT64_C(0xc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_231_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_231_ptr_value) != 0) return -1;
      uint64_t rvi_231_loaded;
      uint64_t rvi_231_address = (rvi_231_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_231_address, 4, 0, &rvi_231_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_231_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_232_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_232_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_232_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f81d: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_235_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_235_a0_value) != 0) return -1;
    uint64_t rvi_235_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_235_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, (((rvi_235_a0_value & rvi_235_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_236_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_236_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_236_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_237_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_237_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_237_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_238_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_238_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_238_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_239_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_239_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_239_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_240_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_240_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_240_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_241_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_241_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_241_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f81f: ;
    {
    uint64_t rvi_242_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_242_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_242_a0_value + UINT64_C(0x698)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_243_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_243_ptr_value) != 0) return -1;
      uint64_t rvi_243_loaded;
      uint64_t rvi_243_address = (rvi_243_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_243_address, 4, 0, &rvi_243_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_243_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_244_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_244_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_244_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f825: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (UINT64_C(0x7)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_246_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_246_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_246_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_247_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_247_ptr_value) != 0) return -1;
    uint64_t rvi_247_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_247_value_value) != 0) return -1;
      uint64_t rvi_247_address = (rvi_247_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_247_address, 4, 0, rvi_247_value_value) != 0) return -1;
    }
rvi_label_000000000082f827: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_249_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_249_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_249_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_250_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_250_ptr_value) != 0) return -1;
    uint64_t rvi_250_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_250_value_value) != 0) return -1;
      uint64_t rvi_250_address = (rvi_250_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_250_address, 4, 0, rvi_250_value_value) != 0) return -1;
    }
rvi_label_000000000082f829: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_252_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_252_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_252_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_253_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_253_ptr_value) != 0) return -1;
    uint64_t rvi_253_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x39), 4, 0, &rvi_253_value_value) != 0) return -1;
      uint64_t rvi_253_address = (rvi_253_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_253_address, 4, 0, rvi_253_value_value) != 0) return -1;
    }
rvi_label_000000000082f82b: ;
    {
    uint64_t rvi_254_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_254_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_254_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_255_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_255_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_255_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_256_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_256_ptr_value) != 0) return -1;
    uint64_t rvi_256_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_256_value_value) != 0) return -1;
      uint64_t rvi_256_address = (rvi_256_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_256_address, 4, 0, rvi_256_value_value) != 0) return -1;
    }
rvi_label_000000000082f82c: ;
    {
    uint64_t rvi_257_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_257_condition_value) != 0) return -1;
    if (rvi_257_condition_value != 0) { goto rvi_label_000000000082f83c; }
    }
rvi_label_000000000082f82e: ;
    {
    uint64_t rvi_258_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_258_ptr_value) != 0) return -1;
      uint64_t rvi_258_loaded;
      uint64_t rvi_258_address = (rvi_258_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_258_address, 4, 0, &rvi_258_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_258_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_259_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_259_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_259_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f830: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f830)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_261_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_261_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_261_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_262_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_262_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_262_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_263_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_263_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_263_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_264_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_264_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_264_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_265_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_265_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_265_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_266_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_266_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_266_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_267_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_267_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_267_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_268_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_268_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_268_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f832: ;
    {
    uint64_t rvi_269_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_269_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_269_a0_value + UINT64_C(0x60)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_270_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_270_ptr_value) != 0) return -1;
      uint64_t rvi_270_loaded;
      uint64_t rvi_270_address = (rvi_270_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_270_address, 4, 0, &rvi_270_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_270_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_271_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_271_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_271_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f835: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f835)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_273_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_273_a0_bytes) != 0) return -1;
    uint64_t rvi_273_converted;
    if (rvi_float80_to_float(rvi_273_a0_bytes, 4, &rvi_273_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_273_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_274_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_274_ptr_value) != 0) return -1;
    uint64_t rvi_274_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_274_value_value) != 0) return -1;
      uint64_t rvi_274_address = (rvi_274_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_274_address, 4, 0, rvi_274_value_value) != 0) return -1;
    }
    {
    uint8_t rvi_275_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_275_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_275_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_276_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_276_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_276_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_277_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_277_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_277_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_278_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_278_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_278_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_279_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_279_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_279_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_280_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_280_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_280_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_281_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_281_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_281_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f838: ;
    {
    uint64_t rvi_282_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_282_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_282_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_283_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_283_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_283_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_284_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_284_ptr_value) != 0) return -1;
      uint64_t rvi_284_address = (rvi_284_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_284_address, 4, 0, UINT64_C(0x82f83a)) != 0) return -1;
    }
    {
    uint64_t rvi_285_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_285_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_285_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f83a: ;
    {
    goto rvi_label_000000000082f85d;
    }
rvi_label_000000000082f83c: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f83c)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_288_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_288_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_288_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_289_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_289_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_289_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_290_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_290_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_290_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f83e: ;
    {
    uint64_t rvi_291_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_291_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_291_a0_value + UINT64_C(0xffffffe0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_292_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_292_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_292_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f841: ;
    {
    uint64_t rvi_293_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_293_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_293_a0_value + UINT64_C(0xffffffe0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f841)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_295_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_295_a0_bytes) != 0) return -1;
    uint64_t rvi_295_converted;
    if (rvi_float80_to_float(rvi_295_a0_bytes, 4, &rvi_295_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_295_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_296_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_296_ptr_value) != 0) return -1;
    uint64_t rvi_296_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_296_value_value) != 0) return -1;
      uint64_t rvi_296_address = (rvi_296_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_296_address, 4, 0, rvi_296_value_value) != 0) return -1;
    }
rvi_label_000000000082f844: ;
    {
    uint64_t rvi_297_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_297_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_297_a0_value + UINT64_C(0xffffffe4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f844)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_299_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_299_a0_bytes) != 0) return -1;
    uint64_t rvi_299_converted;
    if (rvi_float80_to_float(rvi_299_a0_bytes, 4, &rvi_299_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_299_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_300_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_300_ptr_value) != 0) return -1;
    uint64_t rvi_300_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_300_value_value) != 0) return -1;
      uint64_t rvi_300_address = (rvi_300_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_300_address, 4, 0, rvi_300_value_value) != 0) return -1;
    }
rvi_label_000000000082f847: ;
    {
    uint64_t rvi_301_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_301_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_301_a0_value + UINT64_C(0xffffffe8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f847)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_303_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_303_a0_bytes) != 0) return -1;
    uint64_t rvi_303_converted;
    if (rvi_float80_to_float(rvi_303_a0_bytes, 4, &rvi_303_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_303_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_304_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_304_ptr_value) != 0) return -1;
    uint64_t rvi_304_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_304_value_value) != 0) return -1;
      uint64_t rvi_304_address = (rvi_304_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_304_address, 4, 0, rvi_304_value_value) != 0) return -1;
    }
rvi_label_000000000082f84a: ;
    {
    uint64_t rvi_305_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_305_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_305_a0_value + UINT64_C(0xffffffec)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f84a)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_307_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_307_a0_bytes) != 0) return -1;
    uint64_t rvi_307_converted;
    if (rvi_float80_to_float(rvi_307_a0_bytes, 4, &rvi_307_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_307_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_308_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_308_ptr_value) != 0) return -1;
    uint64_t rvi_308_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_308_value_value) != 0) return -1;
      uint64_t rvi_308_address = (rvi_308_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_308_address, 4, 0, rvi_308_value_value) != 0) return -1;
    }
    {
    uint8_t rvi_309_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_309_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_309_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_310_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_310_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_310_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_311_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_311_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_311_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_312_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_312_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_312_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_313_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_313_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_313_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_314_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_314_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_314_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_315_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_315_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_315_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f84d: ;
    {
    uint64_t rvi_316_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_316_ptr_value) != 0) return -1;
      uint64_t rvi_316_loaded;
      uint64_t rvi_316_address = (rvi_316_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_316_address, 4, 0, &rvi_316_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_316_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_317_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_317_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_317_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f84f: ;
    {
    uint64_t rvi_318_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_318_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_318_a0_value + UINT64_C(0x60)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_319_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_319_ptr_value) != 0) return -1;
      uint64_t rvi_319_loaded;
      uint64_t rvi_319_address = (rvi_319_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_319_address, 4, 0, &rvi_319_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_319_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_320_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_320_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_320_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f852: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f852)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_322_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_322_a0_bytes) != 0) return -1;
    uint64_t rvi_322_converted;
    if (rvi_float80_to_float(rvi_322_a0_bytes, 4, &rvi_322_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_322_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_323_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_323_ptr_value) != 0) return -1;
    uint64_t rvi_323_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_323_value_value) != 0) return -1;
      uint64_t rvi_323_address = (rvi_323_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_323_address, 4, 0, rvi_323_value_value) != 0) return -1;
    }
    {
    uint8_t rvi_324_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_324_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_324_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_325_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_325_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_325_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_326_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_326_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_326_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_327_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_327_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_327_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_328_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_328_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_328_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_329_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_329_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_329_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_330_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_330_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_330_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f855: ;
    {
    uint64_t rvi_331_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_331_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_331_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_332_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_332_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_332_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_333_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_333_ptr_value) != 0) return -1;
      uint64_t rvi_333_address = (rvi_333_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_333_address, 4, 0, UINT64_C(0x82f857)) != 0) return -1;
    }
    {
    uint64_t rvi_334_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_334_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_334_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f857: ;
    {
    goto rvi_label_000000000082f85d;
    }
rvi_label_000000000082f859: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f859)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_337_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_337_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_337_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_338_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_338_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_338_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_339_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_339_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_339_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_340_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_340_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_340_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_341_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_341_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_341_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_342_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_342_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_342_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_343_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_343_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_343_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_344_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_344_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_344_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f85b: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f85b)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_346_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_346_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_346_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_347_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_347_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_347_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_348_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_348_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_348_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_349_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_349_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_349_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_350_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_350_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_350_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_351_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_351_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_351_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_352_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_352_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_352_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_353_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_353_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_353_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f85d: ;
    {
    uint64_t rvi_354_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_354_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_354_a0_value + UINT64_C(0x5f4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_355_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_355_ptr_value) != 0) return -1;
      uint64_t rvi_355_loaded;
      uint64_t rvi_355_address = (rvi_355_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_355_address, 4, 0, &rvi_355_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_355_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_356_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_356_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_356_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f863: ;
    {
    uint64_t rvi_357_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_357_ptr_value) != 0) return -1;
      uint64_t rvi_357_loaded;
      uint64_t rvi_357_address = (rvi_357_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_357_address, 4, 0, &rvi_357_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_357_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_358_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_358_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_358_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f865: ;
    {
    uint64_t rvi_359_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_359_ptr_value) != 0) return -1;
      uint64_t rvi_359_loaded;
      uint64_t rvi_359_address = (rvi_359_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_359_address, 4, 0, &rvi_359_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_359_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_360_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_360_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_360_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f867: ;
    {
    uint64_t rvi_361_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_361_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_361_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_362_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_362_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_362_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_363_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_363_ptr_value) != 0) return -1;
      uint64_t rvi_363_address = (rvi_363_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_363_address, 4, 0, UINT64_C(0x82f869)) != 0) return -1;
    }
    {
    uint64_t rvi_364_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_364_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_364_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f869: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_367_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_367_a0_value) != 0) return -1;
    uint64_t rvi_367_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_367_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, (((rvi_367_a0_value & rvi_367_a1_value) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_368_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_368_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_368_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_369_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_369_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_369_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_370_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x41), 1, 0, &rvi_370_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (((rvi_370_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_371_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_371_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_371_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_372_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_372_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_372_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_373_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_373_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_373_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f86b: ;
    {
    uint64_t rvi_374_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_374_condition_value) != 0) return -1;
    if (rvi_374_condition_value != 0) { goto rvi_label_000000000082f878; }
    }
rvi_label_000000000082f86d: ;
    {
    uint64_t rvi_375_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_375_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_375_a0_value + UINT64_C(0x5f4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_376_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_376_ptr_value) != 0) return -1;
      uint64_t rvi_376_loaded;
      uint64_t rvi_376_address = (rvi_376_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_376_address, 4, 0, &rvi_376_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_376_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_377_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_377_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_377_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f873: ;
    {
    uint64_t rvi_378_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_378_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_378_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_379_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_379_ptr_value) != 0) return -1;
      uint64_t rvi_379_address = (rvi_379_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_379_address, 4, 0, UINT64_C(0x82f878)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x8506a0)) != 0) return -1;
    }
rvi_label_000000000082f878: ;
    {
    uint64_t rvi_381_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_381_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_381_a0_value + UINT64_C(0x478)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_382_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_382_ptr_value) != 0) return -1;
      uint64_t rvi_382_loaded;
      uint64_t rvi_382_address = (rvi_382_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_382_address, 4, 0, &rvi_382_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_382_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_383_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_383_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_383_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f87e: ;
    {
    uint64_t rvi_384_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_384_ptr_value) != 0) return -1;
      uint64_t rvi_384_loaded;
      uint64_t rvi_384_address = (rvi_384_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_384_address, 4, 0, &rvi_384_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_384_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_385_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_385_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_385_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f880: ;
    {
    uint64_t rvi_386_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_386_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_386_a0_value + UINT64_C(0xa4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_387_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_387_ptr_value) != 0) return -1;
      uint64_t rvi_387_loaded;
      uint64_t rvi_387_address = (rvi_387_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_387_address, 4, 0, &rvi_387_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_387_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_388_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_388_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_388_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f886: ;
    {
    uint64_t rvi_389_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_389_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_389_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_390_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_390_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_390_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_391_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_391_ptr_value) != 0) return -1;
    uint64_t rvi_391_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_391_value_value) != 0) return -1;
      uint64_t rvi_391_address = (rvi_391_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_391_address, 4, 0, rvi_391_value_value) != 0) return -1;
    }
rvi_label_000000000082f887: ;
    {
    uint64_t rvi_392_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_392_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_392_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_393_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_393_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_393_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_394_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_394_ptr_value) != 0) return -1;
      uint64_t rvi_394_address = (rvi_394_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_394_address, 4, 0, UINT64_C(0x82f889)) != 0) return -1;
    }
    {
    uint64_t rvi_395_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_395_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_395_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f889: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_398_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_398_a0_value) != 0) return -1;
    uint64_t rvi_398_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_398_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, (((rvi_398_a0_value & rvi_398_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_399_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_399_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_399_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_400_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_400_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_400_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_401_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_401_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_401_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_402_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_402_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_402_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_403_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_403_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_403_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_404_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_404_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_404_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f88b: ;
    {
    uint64_t rvi_405_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_405_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 1, 0, ((rvi_405_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_406_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1c), 1, 0, &rvi_406_condition_value) != 0) return -1;
    if (rvi_406_condition_value != 0) { goto rvi_label_000000000082fa37; }
    }
rvi_label_000000000082f891: ;
    {
    uint64_t rvi_407_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_407_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_407_a0_value + UINT64_C(0x10)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_408_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_408_ptr_value) != 0) return -1;
      uint64_t rvi_408_loaded;
      uint64_t rvi_408_address = (rvi_408_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_408_address, 4, 0, &rvi_408_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_408_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_409_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_409_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_409_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f894: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_412_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_412_a0_value) != 0) return -1;
    uint64_t rvi_412_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_412_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, (((rvi_412_a0_value & rvi_412_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_413_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_413_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_413_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_414_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_414_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_414_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_415_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_415_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_415_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_416_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_416_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_416_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_417_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_417_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_417_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_418_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_418_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_418_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f896: ;
    {
    uint64_t rvi_419_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_419_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_419_a0_value + UINT64_C(0x18)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_420_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_420_ptr_value) != 0) return -1;
      uint64_t rvi_420_loaded;
      uint64_t rvi_420_address = (rvi_420_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_420_address, 4, 0, &rvi_420_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_420_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_421_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_421_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_421_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f899: ;
    {
    uint64_t rvi_422_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_422_condition_value) != 0) return -1;
    if (rvi_422_condition_value != 0) { goto rvi_label_000000000082f8ae; }
    }
rvi_label_000000000082f89b: ;
    {
    uint64_t rvi_423_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_423_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_423_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_424_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_424_ptr_value) != 0) return -1;
      uint64_t rvi_424_loaded;
      uint64_t rvi_424_address = (rvi_424_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_424_address, 4, 0, &rvi_424_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_424_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_425_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_425_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_425_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f89e: ;
    {
    uint64_t rvi_426_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_426_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_426_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_427_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_427_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_427_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_428_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_428_ptr_value) != 0) return -1;
    uint64_t rvi_428_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_428_value_value) != 0) return -1;
      uint64_t rvi_428_address = (rvi_428_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_428_address, 4, 0, rvi_428_value_value) != 0) return -1;
    }
rvi_label_000000000082f89f: ;
    {
    uint64_t rvi_429_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_429_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_429_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_430_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_430_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_430_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_431_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_431_ptr_value) != 0) return -1;
    uint64_t rvi_431_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_431_value_value) != 0) return -1;
      uint64_t rvi_431_address = (rvi_431_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_431_address, 4, 0, rvi_431_value_value) != 0) return -1;
    }
rvi_label_000000000082f8a0: ;
    {
    uint64_t rvi_432_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_432_ptr_value) != 0) return -1;
      uint64_t rvi_432_loaded;
      uint64_t rvi_432_address = (rvi_432_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_432_address, 4, 0, &rvi_432_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_432_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_433_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_433_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_433_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8a2: ;
    {
    uint64_t rvi_434_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_434_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_434_a0_value + UINT64_C(0x140)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_435_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_435_ptr_value) != 0) return -1;
      uint64_t rvi_435_loaded;
      uint64_t rvi_435_address = (rvi_435_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_435_address, 4, 0, &rvi_435_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_435_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_436_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_436_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_436_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8a8: ;
    {
    uint64_t rvi_437_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_437_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_437_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8aa: ;
    {
    uint64_t rvi_438_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_438_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_438_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_439_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_439_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_439_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_440_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_440_ptr_value) != 0) return -1;
      uint64_t rvi_440_address = (rvi_440_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_440_address, 4, 0, UINT64_C(0x82f8ac)) != 0) return -1;
    }
    {
    uint64_t rvi_441_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_441_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_441_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f8ac: ;
    {
    goto rvi_label_000000000082f8b8;
    }
rvi_label_000000000082f8ae: ;
    {
    uint64_t rvi_443_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_443_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_443_a0_value + UINT64_C(0x69c)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_445_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_445_ptr_value) != 0) return -1;
    uint64_t rvi_445_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_445_value_value) != 0) return -1;
      uint64_t rvi_445_address = (rvi_445_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_445_address, 4, 0, rvi_445_value_value) != 0) return -1;
    }
rvi_label_000000000082f8b8: ;
    {
    uint64_t rvi_446_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_446_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_446_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_447_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_447_ptr_value) != 0) return -1;
      uint64_t rvi_447_loaded;
      uint64_t rvi_447_address = (rvi_447_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_447_address, 4, 0, &rvi_447_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_447_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_448_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_448_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_448_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8bb: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_451_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_451_a0_value) != 0) return -1;
    uint64_t rvi_451_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_451_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, (((rvi_451_a0_value & rvi_451_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_452_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_452_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_452_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_453_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_453_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_453_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_454_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x42), 4, 0, &rvi_454_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_454_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_455_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_455_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_455_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_456_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_456_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_456_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_457_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_457_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_457_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f8bd: ;
    {
    uint64_t rvi_458_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_458_condition_value) != 0) return -1;
    if (rvi_458_condition_value != 0) { goto rvi_label_000000000082f8e2; }
    }
rvi_label_000000000082f8bf: ;
    {
    uint64_t rvi_459_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_459_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_459_a0_value + UINT64_C(0xfffffffc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_460_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_460_ptr_value) != 0) return -1;
      uint64_t rvi_460_loaded;
      uint64_t rvi_460_address = (rvi_460_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_460_address, 4, 0, &rvi_460_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_460_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_461_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_461_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_461_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8c2: ;
    {
    uint64_t rvi_462_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_462_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_462_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_463_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_463_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_463_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_464_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_464_ptr_value) != 0) return -1;
    uint64_t rvi_464_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_464_value_value) != 0) return -1;
      uint64_t rvi_464_address = (rvi_464_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_464_address, 4, 0, rvi_464_value_value) != 0) return -1;
    }
rvi_label_000000000082f8c3: ;
    {
    uint64_t rvi_465_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_465_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, (rvi_465_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_466_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_466_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_466_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_467_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_467_ptr_value) != 0) return -1;
    uint64_t rvi_467_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1d), 4, 0, &rvi_467_value_value) != 0) return -1;
      uint64_t rvi_467_address = (rvi_467_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_467_address, 4, 0, rvi_467_value_value) != 0) return -1;
    }
rvi_label_000000000082f8c4: ;
    {
    uint64_t rvi_468_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_468_ptr_value) != 0) return -1;
      uint64_t rvi_468_loaded;
      uint64_t rvi_468_address = (rvi_468_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_468_address, 4, 0, &rvi_468_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_468_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_469_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_469_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_469_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8c6: ;
    {
    uint64_t rvi_470_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_470_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_470_a0_value + UINT64_C(0x148)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_471_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_471_ptr_value) != 0) return -1;
      uint64_t rvi_471_loaded;
      uint64_t rvi_471_address = (rvi_471_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_471_address, 4, 0, &rvi_471_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, (rvi_471_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_472_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x18), 4, 0, &rvi_472_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_472_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8cc: ;
    {
    uint64_t rvi_473_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_473_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_473_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8ce: ;
    {
    uint64_t rvi_474_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_474_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, (rvi_474_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_475_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_475_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_475_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_476_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_476_ptr_value) != 0) return -1;
      uint64_t rvi_476_address = (rvi_476_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_476_address, 4, 0, UINT64_C(0x82f8d0)) != 0) return -1;
    }
    {
    uint64_t rvi_477_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 4, 0, &rvi_477_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_477_call_target_value) != 0) return -1;
    }
rvi_label_000000000082f8d0: ;
    {
    uint64_t rvi_478_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_478_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_478_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_479_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_479_ptr_value) != 0) return -1;
      uint64_t rvi_479_address = (rvi_479_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_479_address, 4, 0, UINT64_C(0x82f8d5)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x923622)) != 0) return -1;
    }
rvi_label_000000000082f8d5: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f8d7: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_483_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_483_ptr_value) != 0) return -1;
      uint64_t rvi_483_loaded;
      uint64_t rvi_483_address = (rvi_483_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_483_address, 4, 0, &rvi_483_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_483_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_484_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_484_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_484_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_485_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_485_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_485_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8d8: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_487_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_487_ptr_value) != 0) return -1;
      uint64_t rvi_487_loaded;
      uint64_t rvi_487_address = (rvi_487_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_487_address, 4, 0, &rvi_487_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_487_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_488_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_488_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_488_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_489_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_489_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_489_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8d9: ;
    {
    uint64_t rvi_490_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_490_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_490_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8db: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_492_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_492_ptr_value) != 0) return -1;
      uint64_t rvi_492_loaded;
      uint64_t rvi_492_address = (rvi_492_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_492_address, 4, 0, &rvi_492_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_492_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_493_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_493_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_493_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_494_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_494_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, (rvi_494_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8dc: ;
    {
    uint64_t rvi_495_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_495_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_495_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8de: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_497_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_497_ptr_value) != 0) return -1;
      uint64_t rvi_497_loaded;
      uint64_t rvi_497_address = (rvi_497_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_497_address, 4, 0, &rvi_497_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_497_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_498_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_498_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_498_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_499_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_499_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, (rvi_499_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082f8df: ;
    {
    uint64_t rvi_500_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_500_ptr_value) != 0) return -1;
      uint64_t rvi_500_loaded;
      uint64_t rvi_500_address = (rvi_500_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_500_address, 4, 0, &rvi_500_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x284), 4, 0, (rvi_500_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_501_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_501_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_501_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_502_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_502_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_502_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    return 0;
    }
rvi_label_000000000082f8e2: ;
    {
    uint64_t rvi_504_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_504_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_504_a0_value + UINT64_C(0x6a0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_506_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_506_ptr_value) != 0) return -1;
    uint64_t rvi_506_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_506_value_value) != 0) return -1;
      uint64_t rvi_506_address = (rvi_506_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_506_address, 4, 0, rvi_506_value_value) != 0) return -1;
    }
rvi_label_000000000082f8ec: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f8ec)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_508_result[10];
    if (rvi_float80_from_integer(UINT64_C(0x0), 4, rvi_508_result) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x50), 10, rvi_508_result) != 0) return -1;
    }
    {
    uint8_t rvi_509_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_509_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_509_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_510_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_510_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_510_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_511_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_511_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_511_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_512_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_512_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_512_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_513_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_513_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_513_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_514_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_514_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_514_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_515_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_515_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_515_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_516_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x50), 10, rvi_516_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_516_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f8ee: ;
    {
    uint64_t rvi_517_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_517_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_517_a0_value + UINT64_C(0x13a8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f8ee)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_519_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_519_a0_bytes) != 0) return -1;
    uint64_t rvi_519_converted;
    if (rvi_float80_to_float(rvi_519_a0_bytes, 4, &rvi_519_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_519_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_520_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_520_ptr_value) != 0) return -1;
    uint64_t rvi_520_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_520_value_value) != 0) return -1;
      uint64_t rvi_520_address = (rvi_520_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_520_address, 4, 0, rvi_520_value_value) != 0) return -1;
    }
rvi_label_000000000082f8f4: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f8f6: ;
    {
    uint64_t rvi_522_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_522_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_522_a0_value + UINT64_C(0x13a4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f8f6)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_524_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_524_a0_bytes) != 0) return -1;
    uint64_t rvi_524_converted;
    if (rvi_float80_to_float(rvi_524_a0_bytes, 4, &rvi_524_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_524_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_525_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_525_ptr_value) != 0) return -1;
    uint64_t rvi_525_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_525_value_value) != 0) return -1;
      uint64_t rvi_525_address = (rvi_525_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_525_address, 4, 0, rvi_525_value_value) != 0) return -1;
    }
rvi_label_000000000082f8fc: ;
    {
    uint64_t rvi_526_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_526_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_526_a0_value + UINT64_C(0x13a0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f8fc)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_528_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_528_a0_bytes) != 0) return -1;
    uint64_t rvi_528_converted;
    if (rvi_float80_to_float(rvi_528_a0_bytes, 4, &rvi_528_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_528_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_529_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_529_ptr_value) != 0) return -1;
    uint64_t rvi_529_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_529_value_value) != 0) return -1;
      uint64_t rvi_529_address = (rvi_529_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_529_address, 4, 0, rvi_529_value_value) != 0) return -1;
    }
rvi_label_000000000082f902: ;
    {
    uint64_t rvi_530_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_530_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_530_a0_value + UINT64_C(0x139c)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f902)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_532_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_532_a0_bytes) != 0) return -1;
    uint64_t rvi_532_converted;
    if (rvi_float80_to_float(rvi_532_a0_bytes, 4, &rvi_532_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_532_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_533_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_533_ptr_value) != 0) return -1;
    uint64_t rvi_533_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_533_value_value) != 0) return -1;
      uint64_t rvi_533_address = (rvi_533_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_533_address, 4, 0, rvi_533_value_value) != 0) return -1;
    }
rvi_label_000000000082f908: ;
    {
    uint64_t rvi_534_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_534_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_534_a0_value + UINT64_C(0x1394)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f908)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_536_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_536_a0_bytes) != 0) return -1;
    uint64_t rvi_536_converted;
    if (rvi_float80_to_float(rvi_536_a0_bytes, 4, &rvi_536_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_536_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_537_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_537_ptr_value) != 0) return -1;
    uint64_t rvi_537_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_537_value_value) != 0) return -1;
      uint64_t rvi_537_address = (rvi_537_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_537_address, 4, 0, rvi_537_value_value) != 0) return -1;
    }
rvi_label_000000000082f90e: ;
    {
    uint64_t rvi_538_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_538_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_538_a0_value + UINT64_C(0x1390)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f90e)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_540_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_540_a0_bytes) != 0) return -1;
    uint64_t rvi_540_converted;
    if (rvi_float80_to_float(rvi_540_a0_bytes, 4, &rvi_540_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_540_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_541_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_541_ptr_value) != 0) return -1;
    uint64_t rvi_541_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_541_value_value) != 0) return -1;
      uint64_t rvi_541_address = (rvi_541_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_541_address, 4, 0, rvi_541_value_value) != 0) return -1;
    }
rvi_label_000000000082f914: ;
    {
    uint64_t rvi_542_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_542_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_542_a0_value + UINT64_C(0x138c)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f914)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_544_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_544_a0_bytes) != 0) return -1;
    uint64_t rvi_544_converted;
    if (rvi_float80_to_float(rvi_544_a0_bytes, 4, &rvi_544_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_544_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_545_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_545_ptr_value) != 0) return -1;
    uint64_t rvi_545_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_545_value_value) != 0) return -1;
      uint64_t rvi_545_address = (rvi_545_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_545_address, 4, 0, rvi_545_value_value) != 0) return -1;
    }
rvi_label_000000000082f91a: ;
    {
    uint64_t rvi_546_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_546_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_546_a0_value + UINT64_C(0x1388)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f91a)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_548_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_548_a0_bytes) != 0) return -1;
    uint64_t rvi_548_converted;
    if (rvi_float80_to_float(rvi_548_a0_bytes, 4, &rvi_548_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_548_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_549_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_549_ptr_value) != 0) return -1;
    uint64_t rvi_549_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_549_value_value) != 0) return -1;
      uint64_t rvi_549_address = (rvi_549_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_549_address, 4, 0, rvi_549_value_value) != 0) return -1;
    }
rvi_label_000000000082f920: ;
    {
    uint64_t rvi_550_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_550_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_550_a0_value + UINT64_C(0x1380)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f920)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_552_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_552_a0_bytes) != 0) return -1;
    uint64_t rvi_552_converted;
    if (rvi_float80_to_float(rvi_552_a0_bytes, 4, &rvi_552_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_552_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_553_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_553_ptr_value) != 0) return -1;
    uint64_t rvi_553_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_553_value_value) != 0) return -1;
      uint64_t rvi_553_address = (rvi_553_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_553_address, 4, 0, rvi_553_value_value) != 0) return -1;
    }
rvi_label_000000000082f926: ;
    {
    uint64_t rvi_554_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_554_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_554_a0_value + UINT64_C(0x137c)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f926)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_556_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_556_a0_bytes) != 0) return -1;
    uint64_t rvi_556_converted;
    if (rvi_float80_to_float(rvi_556_a0_bytes, 4, &rvi_556_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_556_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_557_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_557_ptr_value) != 0) return -1;
    uint64_t rvi_557_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_557_value_value) != 0) return -1;
      uint64_t rvi_557_address = (rvi_557_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_557_address, 4, 0, rvi_557_value_value) != 0) return -1;
    }
rvi_label_000000000082f92c: ;
    {
    uint64_t rvi_558_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_558_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_558_a0_value + UINT64_C(0x1378)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f92c)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_560_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_560_a0_bytes) != 0) return -1;
    uint64_t rvi_560_converted;
    if (rvi_float80_to_float(rvi_560_a0_bytes, 4, &rvi_560_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_560_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_561_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_561_ptr_value) != 0) return -1;
    uint64_t rvi_561_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_561_value_value) != 0) return -1;
      uint64_t rvi_561_address = (rvi_561_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_561_address, 4, 0, rvi_561_value_value) != 0) return -1;
    }
rvi_label_000000000082f932: ;
    {
    uint64_t rvi_562_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_562_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_562_a0_value + UINT64_C(0x1374)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f932)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_564_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_564_a0_bytes) != 0) return -1;
    uint64_t rvi_564_converted;
    if (rvi_float80_to_float(rvi_564_a0_bytes, 4, &rvi_564_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_564_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_565_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_565_ptr_value) != 0) return -1;
    uint64_t rvi_565_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_565_value_value) != 0) return -1;
      uint64_t rvi_565_address = (rvi_565_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_565_address, 4, 0, rvi_565_value_value) != 0) return -1;
    }
rvi_label_000000000082f938: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f938)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_567_result[10];
    if (rvi_float80_from_integer(UINT64_C(0x1), 4, rvi_567_result) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x46), 10, rvi_567_result) != 0) return -1;
    }
    {
    uint8_t rvi_568_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_568_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_568_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_569_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_569_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_569_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_570_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_570_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_570_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_571_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_571_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_571_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_572_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_572_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_572_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_573_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_573_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_573_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_574_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_574_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_574_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_575_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x46), 10, rvi_575_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_575_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f93a: ;
    {
    uint64_t rvi_576_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_576_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_576_a0_value + UINT64_C(0x13ac)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f93a)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_578_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_578_a0_bytes) != 0) return -1;
    uint64_t rvi_578_converted;
    if (rvi_float80_to_float(rvi_578_a0_bytes, 4, &rvi_578_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_578_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_579_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_579_ptr_value) != 0) return -1;
    uint64_t rvi_579_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_579_value_value) != 0) return -1;
      uint64_t rvi_579_address = (rvi_579_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_579_address, 4, 0, rvi_579_value_value) != 0) return -1;
    }
rvi_label_000000000082f940: ;
    {
    uint64_t rvi_580_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_580_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_580_a0_value + UINT64_C(0x1398)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f940)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_582_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_582_a0_bytes) != 0) return -1;
    uint64_t rvi_582_converted;
    if (rvi_float80_to_float(rvi_582_a0_bytes, 4, &rvi_582_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_582_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_583_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_583_ptr_value) != 0) return -1;
    uint64_t rvi_583_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_583_value_value) != 0) return -1;
      uint64_t rvi_583_address = (rvi_583_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_583_address, 4, 0, rvi_583_value_value) != 0) return -1;
    }
rvi_label_000000000082f946: ;
    {
    uint64_t rvi_584_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_584_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_584_a0_value + UINT64_C(0x1384)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f946)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_586_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_586_a0_bytes) != 0) return -1;
    uint64_t rvi_586_converted;
    if (rvi_float80_to_float(rvi_586_a0_bytes, 4, &rvi_586_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_586_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_587_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_587_ptr_value) != 0) return -1;
    uint64_t rvi_587_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_587_value_value) != 0) return -1;
      uint64_t rvi_587_address = (rvi_587_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_587_address, 4, 0, rvi_587_value_value) != 0) return -1;
    }
rvi_label_000000000082f94c: ;
    {
    uint64_t rvi_588_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_588_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_588_a0_value + UINT64_C(0x1370)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f94c)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_590_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_590_a0_bytes) != 0) return -1;
    uint64_t rvi_590_converted;
    if (rvi_float80_to_float(rvi_590_a0_bytes, 4, &rvi_590_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_590_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_591_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_591_ptr_value) != 0) return -1;
    uint64_t rvi_591_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_591_value_value) != 0) return -1;
      uint64_t rvi_591_address = (rvi_591_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_591_address, 4, 0, rvi_591_value_value) != 0) return -1;
    }
rvi_label_000000000082f952: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f952)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_593_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_593_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_593_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_594_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_594_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_594_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_595_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_595_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_595_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f954: ;
    {
    uint64_t rvi_596_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_596_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_596_a0_value + UINT64_C(0x1a70)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_597_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_597_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, (rvi_597_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_598_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_598_ptr_value) != 0) return -1;
    uint64_t rvi_598_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, &rvi_598_value_value) != 0) return -1;
      uint64_t rvi_598_address = (rvi_598_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_598_address, 1, 0, rvi_598_value_value) != 0) return -1;
    }
rvi_label_000000000082f95a: ;
    {
    uint64_t rvi_599_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_599_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_599_a0_value + UINT64_C(0x13e8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f95a)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_601_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_601_a0_bytes) != 0) return -1;
    uint64_t rvi_601_converted;
    if (rvi_float80_to_float(rvi_601_a0_bytes, 4, &rvi_601_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_601_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_602_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_602_ptr_value) != 0) return -1;
    uint64_t rvi_602_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_602_value_value) != 0) return -1;
      uint64_t rvi_602_address = (rvi_602_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_602_address, 4, 0, rvi_602_value_value) != 0) return -1;
    }
rvi_label_000000000082f960: ;
    {
    uint64_t rvi_603_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_603_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_603_a0_value + UINT64_C(0x13e4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f960)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_605_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_605_a0_bytes) != 0) return -1;
    uint64_t rvi_605_converted;
    if (rvi_float80_to_float(rvi_605_a0_bytes, 4, &rvi_605_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_605_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_606_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_606_ptr_value) != 0) return -1;
    uint64_t rvi_606_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_606_value_value) != 0) return -1;
      uint64_t rvi_606_address = (rvi_606_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_606_address, 4, 0, rvi_606_value_value) != 0) return -1;
    }
rvi_label_000000000082f966: ;
    {
    uint64_t rvi_607_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_607_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_607_a0_value + UINT64_C(0x13e0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f966)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_609_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_609_a0_bytes) != 0) return -1;
    uint64_t rvi_609_converted;
    if (rvi_float80_to_float(rvi_609_a0_bytes, 4, &rvi_609_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_609_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_610_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_610_ptr_value) != 0) return -1;
    uint64_t rvi_610_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_610_value_value) != 0) return -1;
      uint64_t rvi_610_address = (rvi_610_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_610_address, 4, 0, rvi_610_value_value) != 0) return -1;
    }
rvi_label_000000000082f96c: ;
    {
    uint64_t rvi_611_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_611_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_611_a0_value + UINT64_C(0x13dc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f96c)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_613_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_613_a0_bytes) != 0) return -1;
    uint64_t rvi_613_converted;
    if (rvi_float80_to_float(rvi_613_a0_bytes, 4, &rvi_613_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_613_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_614_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_614_ptr_value) != 0) return -1;
    uint64_t rvi_614_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_614_value_value) != 0) return -1;
      uint64_t rvi_614_address = (rvi_614_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_614_address, 4, 0, rvi_614_value_value) != 0) return -1;
    }
rvi_label_000000000082f972: ;
    {
    uint64_t rvi_615_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_615_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_615_a0_value + UINT64_C(0x13d4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f972)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_617_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_617_a0_bytes) != 0) return -1;
    uint64_t rvi_617_converted;
    if (rvi_float80_to_float(rvi_617_a0_bytes, 4, &rvi_617_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_617_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_618_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_618_ptr_value) != 0) return -1;
    uint64_t rvi_618_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_618_value_value) != 0) return -1;
      uint64_t rvi_618_address = (rvi_618_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_618_address, 4, 0, rvi_618_value_value) != 0) return -1;
    }
rvi_label_000000000082f978: ;
    {
    uint64_t rvi_619_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_619_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_619_a0_value + UINT64_C(0x13d0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f978)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_621_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_621_a0_bytes) != 0) return -1;
    uint64_t rvi_621_converted;
    if (rvi_float80_to_float(rvi_621_a0_bytes, 4, &rvi_621_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_621_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_622_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_622_ptr_value) != 0) return -1;
    uint64_t rvi_622_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_622_value_value) != 0) return -1;
      uint64_t rvi_622_address = (rvi_622_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_622_address, 4, 0, rvi_622_value_value) != 0) return -1;
    }
rvi_label_000000000082f97e: ;
    {
    uint64_t rvi_623_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_623_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_623_a0_value + UINT64_C(0x13cc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f97e)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_625_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_625_a0_bytes) != 0) return -1;
    uint64_t rvi_625_converted;
    if (rvi_float80_to_float(rvi_625_a0_bytes, 4, &rvi_625_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_625_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_626_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_626_ptr_value) != 0) return -1;
    uint64_t rvi_626_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_626_value_value) != 0) return -1;
      uint64_t rvi_626_address = (rvi_626_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_626_address, 4, 0, rvi_626_value_value) != 0) return -1;
    }
rvi_label_000000000082f984: ;
    {
    uint64_t rvi_627_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_627_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_627_a0_value + UINT64_C(0x13c8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f984)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_629_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_629_a0_bytes) != 0) return -1;
    uint64_t rvi_629_converted;
    if (rvi_float80_to_float(rvi_629_a0_bytes, 4, &rvi_629_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_629_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_630_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_630_ptr_value) != 0) return -1;
    uint64_t rvi_630_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_630_value_value) != 0) return -1;
      uint64_t rvi_630_address = (rvi_630_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_630_address, 4, 0, rvi_630_value_value) != 0) return -1;
    }
rvi_label_000000000082f98a: ;
    {
    uint64_t rvi_631_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_631_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_631_a0_value + UINT64_C(0x13c0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f98a)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_633_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_633_a0_bytes) != 0) return -1;
    uint64_t rvi_633_converted;
    if (rvi_float80_to_float(rvi_633_a0_bytes, 4, &rvi_633_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_633_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_634_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_634_ptr_value) != 0) return -1;
    uint64_t rvi_634_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_634_value_value) != 0) return -1;
      uint64_t rvi_634_address = (rvi_634_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_634_address, 4, 0, rvi_634_value_value) != 0) return -1;
    }
rvi_label_000000000082f990: ;
    {
    uint64_t rvi_635_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_635_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_635_a0_value + UINT64_C(0x13bc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f990)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_637_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_637_a0_bytes) != 0) return -1;
    uint64_t rvi_637_converted;
    if (rvi_float80_to_float(rvi_637_a0_bytes, 4, &rvi_637_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_637_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_638_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_638_ptr_value) != 0) return -1;
    uint64_t rvi_638_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_638_value_value) != 0) return -1;
      uint64_t rvi_638_address = (rvi_638_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_638_address, 4, 0, rvi_638_value_value) != 0) return -1;
    }
rvi_label_000000000082f996: ;
    {
    uint64_t rvi_639_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_639_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_639_a0_value + UINT64_C(0x13b8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f996)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_641_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_641_a0_bytes) != 0) return -1;
    uint64_t rvi_641_converted;
    if (rvi_float80_to_float(rvi_641_a0_bytes, 4, &rvi_641_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_641_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_642_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_642_ptr_value) != 0) return -1;
    uint64_t rvi_642_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_642_value_value) != 0) return -1;
      uint64_t rvi_642_address = (rvi_642_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_642_address, 4, 0, rvi_642_value_value) != 0) return -1;
    }
rvi_label_000000000082f99c: ;
    {
    uint64_t rvi_643_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_643_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_643_a0_value + UINT64_C(0x13b4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f99c)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_645_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_645_a0_bytes) != 0) return -1;
    uint64_t rvi_645_converted;
    if (rvi_float80_to_float(rvi_645_a0_bytes, 4, &rvi_645_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_645_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_646_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_646_ptr_value) != 0) return -1;
    uint64_t rvi_646_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_646_value_value) != 0) return -1;
      uint64_t rvi_646_address = (rvi_646_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_646_address, 4, 0, rvi_646_value_value) != 0) return -1;
    }
rvi_label_000000000082f9a2: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9a2)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_648_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_648_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_648_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_649_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_649_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_649_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_650_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_650_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_650_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f9a4: ;
    {
    uint64_t rvi_651_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_651_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_651_a0_value + UINT64_C(0x13ec)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9a4)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_653_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_653_a0_bytes) != 0) return -1;
    uint64_t rvi_653_converted;
    if (rvi_float80_to_float(rvi_653_a0_bytes, 4, &rvi_653_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_653_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_654_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_654_ptr_value) != 0) return -1;
    uint64_t rvi_654_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_654_value_value) != 0) return -1;
      uint64_t rvi_654_address = (rvi_654_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_654_address, 4, 0, rvi_654_value_value) != 0) return -1;
    }
rvi_label_000000000082f9aa: ;
    {
    uint64_t rvi_655_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_655_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_655_a0_value + UINT64_C(0x13d8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9aa)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_657_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_657_a0_bytes) != 0) return -1;
    uint64_t rvi_657_converted;
    if (rvi_float80_to_float(rvi_657_a0_bytes, 4, &rvi_657_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_657_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_658_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_658_ptr_value) != 0) return -1;
    uint64_t rvi_658_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_658_value_value) != 0) return -1;
      uint64_t rvi_658_address = (rvi_658_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_658_address, 4, 0, rvi_658_value_value) != 0) return -1;
    }
rvi_label_000000000082f9b0: ;
    {
    uint64_t rvi_659_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_659_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_659_a0_value + UINT64_C(0x13c4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9b0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_661_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_661_a0_bytes) != 0) return -1;
    uint64_t rvi_661_converted;
    if (rvi_float80_to_float(rvi_661_a0_bytes, 4, &rvi_661_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_661_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_662_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_662_ptr_value) != 0) return -1;
    uint64_t rvi_662_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_662_value_value) != 0) return -1;
      uint64_t rvi_662_address = (rvi_662_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_662_address, 4, 0, rvi_662_value_value) != 0) return -1;
    }
rvi_label_000000000082f9b6: ;
    {
    uint64_t rvi_663_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_663_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_663_a0_value + UINT64_C(0x13b0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9b6)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_665_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_665_a0_bytes) != 0) return -1;
    uint64_t rvi_665_converted;
    if (rvi_float80_to_float(rvi_665_a0_bytes, 4, &rvi_665_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_665_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_666_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_666_ptr_value) != 0) return -1;
    uint64_t rvi_666_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_666_value_value) != 0) return -1;
      uint64_t rvi_666_address = (rvi_666_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_666_address, 4, 0, rvi_666_value_value) != 0) return -1;
    }
rvi_label_000000000082f9bc: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9bc)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_668_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_668_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_668_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_669_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_669_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_669_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_670_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_670_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_670_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082f9be: ;
    {
    uint64_t rvi_671_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_671_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_671_a0_value + UINT64_C(0x1a71)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_672_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_672_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, (rvi_672_a0_value) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_673_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_673_ptr_value) != 0) return -1;
    uint64_t rvi_673_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xc), 1, 0, &rvi_673_value_value) != 0) return -1;
      uint64_t rvi_673_address = (rvi_673_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_673_address, 1, 0, rvi_673_value_value) != 0) return -1;
    }
rvi_label_000000000082f9c4: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_676_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_676_a0_value) != 0) return -1;
    uint64_t rvi_676_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_676_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (((rvi_676_a0_value ^ rvi_676_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_677_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_677_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_677_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_678_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_678_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_678_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_679_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_679_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, (((rvi_679_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_680_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 4, 0, &rvi_680_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_680_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_681_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_681_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_681_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_682_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_682_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_682_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082f9c6: ;
    {
    uint64_t rvi_683_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_683_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_683_a0_value + UINT64_C(0x1a72)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_684_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_684_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_684_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_685_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_685_ptr_value) != 0) return -1;
    uint64_t rvi_685_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_685_value_value) != 0) return -1;
      uint64_t rvi_685_address = (rvi_685_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_685_address, 4, 0, rvi_685_value_value) != 0) return -1;
    }
rvi_label_000000000082f9cc: ;
    {
    uint64_t rvi_686_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_686_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_686_a0_value + UINT64_C(0x1a76)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_687_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_687_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_687_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_688_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_688_ptr_value) != 0) return -1;
    uint64_t rvi_688_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_688_value_value) != 0) return -1;
      uint64_t rvi_688_address = (rvi_688_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_688_address, 4, 0, rvi_688_value_value) != 0) return -1;
    }
rvi_label_000000000082f9d2: ;
    {
    uint64_t rvi_689_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_689_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_689_a0_value + UINT64_C(0x1a7a)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_690_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_690_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_690_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_691_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_691_ptr_value) != 0) return -1;
    uint64_t rvi_691_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_691_value_value) != 0) return -1;
      uint64_t rvi_691_address = (rvi_691_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_691_address, 4, 0, rvi_691_value_value) != 0) return -1;
    }
rvi_label_000000000082f9d8: ;
    {
    uint64_t rvi_692_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_692_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_692_a0_value + UINT64_C(0x1a7e)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_693_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_693_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_693_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_694_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_694_ptr_value) != 0) return -1;
    uint64_t rvi_694_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_694_value_value) != 0) return -1;
      uint64_t rvi_694_address = (rvi_694_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_694_address, 4, 0, rvi_694_value_value) != 0) return -1;
    }
rvi_label_000000000082f9de: ;
    {
    uint64_t rvi_695_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_695_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_695_a0_value + UINT64_C(0x1a82)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_696_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_696_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_696_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_697_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_697_ptr_value) != 0) return -1;
    uint64_t rvi_697_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_697_value_value) != 0) return -1;
      uint64_t rvi_697_address = (rvi_697_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_697_address, 4, 0, rvi_697_value_value) != 0) return -1;
    }
rvi_label_000000000082f9e4: ;
    {
    uint64_t rvi_698_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_698_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_698_a0_value + UINT64_C(0x1a86)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_699_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_699_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, (rvi_699_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_700_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_700_ptr_value) != 0) return -1;
    uint64_t rvi_700_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xf), 4, 0, &rvi_700_value_value) != 0) return -1;
      uint64_t rvi_700_address = (rvi_700_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_700_address, 4, 0, rvi_700_value_value) != 0) return -1;
    }
rvi_label_000000000082f9ea: ;
    {
    uint64_t rvi_701_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_701_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_701_a0_value + UINT64_C(0x1a8a)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_702_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 2, 0, &rvi_702_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 2, 0, (rvi_702_a0_value) & rvi_mask(2)) != 0) return -1;
    }
    {
    uint64_t rvi_703_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_703_ptr_value) != 0) return -1;
    uint64_t rvi_703_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 2, 0, &rvi_703_value_value) != 0) return -1;
      uint64_t rvi_703_address = (rvi_703_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_703_address, 2, 0, rvi_703_value_value) != 0) return -1;
    }
rvi_label_000000000082f9f1: ;
    {
    uint64_t rvi_704_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_704_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_704_a0_value + UINT64_C(0x6b0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9f1)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_706_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_706_a0_bytes) != 0) return -1;
    uint64_t rvi_706_converted;
    if (rvi_float80_to_float(rvi_706_a0_bytes, 4, &rvi_706_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_706_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_707_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_707_ptr_value) != 0) return -1;
    uint64_t rvi_707_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_707_value_value) != 0) return -1;
      uint64_t rvi_707_address = (rvi_707_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_707_address, 4, 0, rvi_707_value_value) != 0) return -1;
    }
rvi_label_000000000082f9f7: ;
    {
    uint64_t rvi_708_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_708_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_708_a0_value + UINT64_C(0x6b4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9f7)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_710_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_710_a0_bytes) != 0) return -1;
    uint64_t rvi_710_converted;
    if (rvi_float80_to_float(rvi_710_a0_bytes, 4, &rvi_710_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_710_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_711_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_711_ptr_value) != 0) return -1;
    uint64_t rvi_711_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_711_value_value) != 0) return -1;
      uint64_t rvi_711_address = (rvi_711_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_711_address, 4, 0, rvi_711_value_value) != 0) return -1;
    }
rvi_label_000000000082f9fd: ;
    {
    uint64_t rvi_712_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_712_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_712_a0_value + UINT64_C(0x6b8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82f9fd)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_714_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_714_a0_bytes) != 0) return -1;
    uint64_t rvi_714_converted;
    if (rvi_float80_to_float(rvi_714_a0_bytes, 4, &rvi_714_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_714_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_715_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_715_ptr_value) != 0) return -1;
    uint64_t rvi_715_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_715_value_value) != 0) return -1;
      uint64_t rvi_715_address = (rvi_715_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_715_address, 4, 0, rvi_715_value_value) != 0) return -1;
    }
rvi_label_000000000082fa03: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa03)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_717_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_717_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_717_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_718_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_718_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_718_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_719_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_719_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_719_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082fa05: ;
    {
    uint64_t rvi_720_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_720_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_720_a0_value + UINT64_C(0x6bc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa05)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_722_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_722_a0_bytes) != 0) return -1;
    uint64_t rvi_722_converted;
    if (rvi_float80_to_float(rvi_722_a0_bytes, 4, &rvi_722_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_722_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_723_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_723_ptr_value) != 0) return -1;
    uint64_t rvi_723_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_723_value_value) != 0) return -1;
      uint64_t rvi_723_address = (rvi_723_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_723_address, 4, 0, rvi_723_value_value) != 0) return -1;
    }
rvi_label_000000000082fa0b: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa0b)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_725_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_725_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_725_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_726_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_726_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_726_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_727_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x5a), 10, rvi_727_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_727_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082fa0d: ;
    {
    uint64_t rvi_728_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_728_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_728_a0_value + UINT64_C(0x6c0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa0d)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_730_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_730_a0_bytes) != 0) return -1;
    uint64_t rvi_730_converted;
    if (rvi_float80_to_float(rvi_730_a0_bytes, 4, &rvi_730_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_730_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_731_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_731_ptr_value) != 0) return -1;
    uint64_t rvi_731_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_731_value_value) != 0) return -1;
      uint64_t rvi_731_address = (rvi_731_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_731_address, 4, 0, rvi_731_value_value) != 0) return -1;
    }
rvi_label_000000000082fa13: ;
    {
    uint64_t rvi_732_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_732_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_732_a0_value + UINT64_C(0x6c8)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa13)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_734_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_734_a0_bytes) != 0) return -1;
    uint64_t rvi_734_converted;
    if (rvi_float80_to_float(rvi_734_a0_bytes, 4, &rvi_734_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_734_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_735_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_735_ptr_value) != 0) return -1;
    uint64_t rvi_735_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_735_value_value) != 0) return -1;
      uint64_t rvi_735_address = (rvi_735_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_735_address, 4, 0, rvi_735_value_value) != 0) return -1;
    }
rvi_label_000000000082fa19: ;
    {
    uint64_t rvi_736_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_736_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_736_a0_value + UINT64_C(0x6cc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa19)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_738_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_738_a0_bytes) != 0) return -1;
    uint64_t rvi_738_converted;
    if (rvi_float80_to_float(rvi_738_a0_bytes, 4, &rvi_738_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_738_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_739_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_739_ptr_value) != 0) return -1;
    uint64_t rvi_739_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_739_value_value) != 0) return -1;
      uint64_t rvi_739_address = (rvi_739_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_739_address, 4, 0, rvi_739_value_value) != 0) return -1;
    }
    {
    uint8_t rvi_740_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_740_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_740_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_741_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_741_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_741_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_742_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_742_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_742_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_743_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_743_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_743_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_744_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_744_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_744_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_745_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_745_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_745_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_746_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_746_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_746_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082fa1f: ;
    {
    uint64_t rvi_747_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_747_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (((rvi_747_a0_value + UINT64_C(0x6c4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10ac), 4, 0, (UINT64_C(0x82fa1f)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint8_t rvi_749_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_749_a0_bytes) != 0) return -1;
    uint64_t rvi_749_converted;
    if (rvi_float80_to_float(rvi_749_a0_bytes, 4, &rvi_749_converted) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_749_converted) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_750_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_750_ptr_value) != 0) return -1;
    uint64_t rvi_750_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_750_value_value) != 0) return -1;
      uint64_t rvi_750_address = (rvi_750_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_750_address, 4, 0, rvi_750_value_value) != 0) return -1;
    }
    {
    uint8_t rvi_751_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_751_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1100), 10, rvi_751_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_752_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_752_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1110), 10, rvi_752_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_753_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_753_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1120), 10, rvi_753_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_754_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_754_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1130), 10, rvi_754_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_755_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_755_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1140), 10, rvi_755_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_756_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_756_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1150), 10, rvi_756_a0_bytes) != 0) return -1;
    }
    {
    uint8_t rvi_757_a0_bytes[10];
    if (rvi_read_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1170), 10, rvi_757_a0_bytes) != 0) return -1;
    if (rvi_write_bytes(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1160), 10, rvi_757_a0_bytes) != 0) return -1;
    }
rvi_label_000000000082fa25: ;
    {
    uint64_t rvi_758_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_758_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_758_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_759_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_759_ptr_value) != 0) return -1;
      uint64_t rvi_759_address = (rvi_759_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_759_address, 4, 0, UINT64_C(0x82fa2a)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x923622)) != 0) return -1;
    }
rvi_label_000000000082fa2a: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, (UINT64_C(0x1)) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082fa2c: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_763_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_763_ptr_value) != 0) return -1;
      uint64_t rvi_763_loaded;
      uint64_t rvi_763_address = (rvi_763_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_763_address, 4, 0, &rvi_763_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_763_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_764_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_764_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_764_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_765_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_765_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_765_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa2d: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_767_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_767_ptr_value) != 0) return -1;
      uint64_t rvi_767_loaded;
      uint64_t rvi_767_address = (rvi_767_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_767_address, 4, 0, &rvi_767_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_767_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_768_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_768_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_768_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_769_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_769_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_769_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa2e: ;
    {
    uint64_t rvi_770_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_770_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_770_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa30: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_772_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_772_ptr_value) != 0) return -1;
      uint64_t rvi_772_loaded;
      uint64_t rvi_772_address = (rvi_772_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_772_address, 4, 0, &rvi_772_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_772_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_773_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_773_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_773_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_774_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_774_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, (rvi_774_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa31: ;
    {
    uint64_t rvi_775_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_775_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_775_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa33: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_777_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_777_ptr_value) != 0) return -1;
      uint64_t rvi_777_loaded;
      uint64_t rvi_777_address = (rvi_777_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_777_address, 4, 0, &rvi_777_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_777_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_778_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_778_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_778_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_779_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_779_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, (rvi_779_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa34: ;
    {
    uint64_t rvi_780_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_780_ptr_value) != 0) return -1;
      uint64_t rvi_780_loaded;
      uint64_t rvi_780_address = (rvi_780_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_780_address, 4, 0, &rvi_780_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x284), 4, 0, (rvi_780_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_781_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_781_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_781_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_782_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_782_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_782_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    return 0;
    }
rvi_label_000000000082fa37: ;
    {
    uint64_t rvi_784_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_784_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_784_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_785_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_785_ptr_value) != 0) return -1;
      uint64_t rvi_785_address = (rvi_785_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_785_address, 4, 0, UINT64_C(0x82fa3c)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x923622)) != 0) return -1;
    }
rvi_label_000000000082fa3c: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_788_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_788_ptr_value) != 0) return -1;
      uint64_t rvi_788_loaded;
      uint64_t rvi_788_address = (rvi_788_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_788_address, 4, 0, &rvi_788_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_788_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_789_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_789_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_789_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_790_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_790_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_790_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa3d: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_793_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_793_a0_value) != 0) return -1;
    uint64_t rvi_793_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_793_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, (((rvi_793_a0_value ^ rvi_793_a1_value) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_794_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_794_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_794_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_795_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_795_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_795_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_796_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_796_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, (((rvi_796_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_797_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x21), 1, 0, &rvi_797_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, (rvi_popcount(rvi_797_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_798_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x25), 1, 0, &rvi_798_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, (((rvi_798_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_799_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x26), 1, 0, &rvi_799_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_799_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000082fa3f: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_801_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_801_ptr_value) != 0) return -1;
      uint64_t rvi_801_loaded;
      uint64_t rvi_801_address = (rvi_801_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_801_address, 4, 0, &rvi_801_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_801_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_802_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_802_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_802_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_803_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_803_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_803_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa40: ;
    {
    uint64_t rvi_804_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, &rvi_804_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_804_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa42: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_806_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_806_ptr_value) != 0) return -1;
      uint64_t rvi_806_loaded;
      uint64_t rvi_806_address = (rvi_806_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_806_address, 4, 0, &rvi_806_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_806_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_807_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_807_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_807_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_808_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_808_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x14), 4, 0, (rvi_808_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa43: ;
    {
    uint64_t rvi_809_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, &rvi_809_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (rvi_809_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa45: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_811_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_811_ptr_value) != 0) return -1;
      uint64_t rvi_811_loaded;
      uint64_t rvi_811_address = (rvi_811_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_811_address, 4, 0, &rvi_811_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, (rvi_811_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_812_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_812_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_812_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_813_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x35), 4, 0, &rvi_813_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0xc), 4, 0, (rvi_813_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000082fa46: ;
    {
    uint64_t rvi_814_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_814_ptr_value) != 0) return -1;
      uint64_t rvi_814_loaded;
      uint64_t rvi_814_address = (rvi_814_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_814_address, 4, 0, &rvi_814_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x284), 4, 0, (rvi_814_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_815_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_815_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_815_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_816_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_816_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_816_a0_value + UINT64_C(0x14)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    return 0;
    }
    return 0;
}
