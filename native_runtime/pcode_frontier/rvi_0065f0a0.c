/* Generated from raw P-code for FUN_0065f0a0 (0x0065f0a0). */
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
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
    return LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384 && sizeof(long double) >= 10;
#else
    return 0;
#endif
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
    uint8_t bytes[sizeof(long double)] = {0};
    if (!input || !value || !rvi_float80_host_supported()) return -1;
    memcpy(bytes, input, 10);
    memcpy(value, bytes, sizeof(*value));
    return 0;
}
static int rvi_float80_store(long double value, uint8_t output[10]) {
    uint8_t bytes[sizeof(long double)] = {0};
    if (!output || !rvi_float80_host_supported()) return -1;
    memcpy(bytes, &value, sizeof(value));
    memcpy(output, bytes, 10);
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
int rvi_0065f0a0(RviPcodeContext *ctx) {
    uint8_t _unique[40] = {0};
    const size_t _unique_size = 40;
    if (!ctx) return -1;
rvi_label_000000000065f0a0: ;
    {
    uint64_t rvi_0_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_0_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x9), 4, 0, (rvi_0_a0_value) & rvi_mask(4)) != 0) return -1;
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
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x9), 4, 0, &rvi_2_value_value) != 0) return -1;
      uint64_t rvi_2_address = (rvi_2_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_2_address, 4, 0, rvi_2_value_value) != 0) return -1;
    }
rvi_label_000000000065f0a1: ;
    {
    uint64_t rvi_3_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_3_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_3_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0a3: ;
    {
    uint64_t rvi_4_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_4_ptr_value) != 0) return -1;
      uint64_t rvi_4_loaded;
      uint64_t rvi_4_address = (rvi_4_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_4_address, 4, 0, &rvi_4_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_4_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_5_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_5_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_5_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0a5: ;
    {
    uint64_t rvi_6_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_6_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_6_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_7_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_7_ptr_value) != 0) return -1;
      uint64_t rvi_7_loaded;
      uint64_t rvi_7_address = (rvi_7_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_7_address, 4, 0, &rvi_7_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_7_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_8_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_8_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 4, 0, (rvi_8_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_9_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 4, 0, &rvi_9_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (((rvi_9_a0_value & rvi_mask(4)) < (UINT64_C(0x0) & rvi_mask(4)))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_10_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 4, 0, &rvi_10_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (rvi_signed_borrow(rvi_10_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_11_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x17), 4, 0, &rvi_11_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 4, 0, (((rvi_11_a0_value - UINT64_C(0x0)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_12_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 4, 0, &rvi_12_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_12_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_13_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 4, 0, &rvi_13_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_13_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_14_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1b), 4, 0, &rvi_14_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 4, 0, (((rvi_14_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_15_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 4, 0, &rvi_15_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, (rvi_popcount(rvi_15_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_16_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, &rvi_16_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, (((rvi_16_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_17_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, &rvi_17_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_17_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000065f0a9: ;
    {
    uint64_t rvi_18_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_18_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x9), 4, 0, (rvi_18_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_19_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_19_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_19_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_20_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_20_ptr_value) != 0) return -1;
    uint64_t rvi_20_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x9), 4, 0, &rvi_20_value_value) != 0) return -1;
      uint64_t rvi_20_address = (rvi_20_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_20_address, 4, 0, rvi_20_value_value) != 0) return -1;
    }
rvi_label_000000000065f0aa: ;
    {
    uint64_t rvi_21_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_21_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_21_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0ac: ;
    {
    uint64_t rvi_22_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_22_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 1, 0, ((rvi_22_a0_value == 0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_23_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x8), 1, 0, &rvi_23_condition_value) != 0) return -1;
    if (rvi_23_condition_value != 0) { goto rvi_label_000000000065f0e4; }
    }
rvi_label_000000000065f0ae: ;
    {
    uint64_t rvi_24_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_24_ptr_value) != 0) return -1;
      uint64_t rvi_24_loaded;
      uint64_t rvi_24_address = (rvi_24_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_24_address, 4, 0, &rvi_24_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_24_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_25_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_25_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_25_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0b0: ;
    {
    uint64_t rvi_26_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_26_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_26_a0_value + UINT64_C(0xc)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_27_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_27_ptr_value) != 0) return -1;
      uint64_t rvi_27_loaded;
      uint64_t rvi_27_address = (rvi_27_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_27_address, 4, 0, &rvi_27_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_27_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_28_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_28_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_28_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0b3: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (UINT64_C(0x1)) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0b8: ;
    {
    uint64_t rvi_30_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_30_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, (rvi_30_a0_value) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_31_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_31_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_31_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_32_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_32_ptr_value) != 0) return -1;
      uint64_t rvi_32_address = (rvi_32_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_32_address, 4, 0, UINT64_C(0x65f0ba)) != 0) return -1;
    }
    {
    uint64_t rvi_33_call_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x13), 4, 0, &rvi_33_call_target_value) != 0) return -1;
    if (rvi_call(ctx, rvi_33_call_target_value) != 0) return -1;
    }
rvi_label_000000000065f0ba: ;
    {
    uint64_t rvi_34_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_34_ptr_value) != 0) return -1;
      uint64_t rvi_34_loaded;
      uint64_t rvi_34_address = (rvi_34_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_34_address, 4, 0, &rvi_34_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_34_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_35_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_35_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_35_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0bc: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_37_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_37_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_37_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_38_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_38_ptr_value) != 0) return -1;
    uint64_t rvi_38_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, &rvi_38_value_value) != 0) return -1;
      uint64_t rvi_38_address = (rvi_38_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_38_address, 4, 0, rvi_38_value_value) != 0) return -1;
    }
rvi_label_000000000065f0be: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_40_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_40_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_40_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_41_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_41_ptr_value) != 0) return -1;
    uint64_t rvi_41_value_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x23), 4, 0, &rvi_41_value_value) != 0) return -1;
      uint64_t rvi_41_address = (rvi_41_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_41_address, 4, 0, rvi_41_value_value) != 0) return -1;
    }
rvi_label_000000000065f0c0: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (UINT64_C(0xaeff74)) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0c5: ;
    {
    uint64_t rvi_43_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_43_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_43_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_44_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_44_ptr_value) != 0) return -1;
      uint64_t rvi_44_address = (rvi_44_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_44_address, 4, 0, UINT64_C(0x65f0ca)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x649cb0)) != 0) return -1;
    }
rvi_label_000000000065f0ca: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_48_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_48_a0_value) != 0) return -1;
    uint64_t rvi_48_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 1, 0, &rvi_48_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, (((rvi_48_a0_value & rvi_48_a1_value) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_49_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_49_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_49_a0_value, UINT64_C(0x0), 1)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_50_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_50_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_50_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_51_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x27), 1, 0, &rvi_51_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 1, 0, (((rvi_51_a0_value & UINT64_C(0xff)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_52_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 1, 0, &rvi_52_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, (rvi_popcount(rvi_52_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_53_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, &rvi_53_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, (((rvi_53_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_54_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, &rvi_54_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_54_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000065f0cc: ;
    {
    uint64_t rvi_55_condition_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, &rvi_55_condition_value) != 0) return -1;
    if (rvi_55_condition_value != 0) { goto rvi_label_000000000065f0e4; }
    }
rvi_label_000000000065f0ce: ;
    {
    uint64_t rvi_56_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_56_ptr_value) != 0) return -1;
      uint64_t rvi_56_loaded;
      uint64_t rvi_56_address = (rvi_56_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_56_address, 4, 0, &rvi_56_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_56_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_57_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_57_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_57_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0d0: ;
    {
    uint64_t rvi_58_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, &rvi_58_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (rvi_58_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0d2: ;
    {
    uint64_t rvi_59_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_59_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_59_a0_value - UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_60_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_60_ptr_value) != 0) return -1;
      uint64_t rvi_60_address = (rvi_60_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_write_space(ctx, "ram", rvi_60_address, 4, 0, UINT64_C(0x65f0d7)) != 0) return -1;
    }
    {
    if (rvi_call(ctx, UINT64_C(0x655090)) != 0) return -1;
    }
rvi_label_000000000065f0d7: ;
    {
    uint64_t rvi_62_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, &rvi_62_ptr_value) != 0) return -1;
      uint64_t rvi_62_loaded;
      uint64_t rvi_62_address = (rvi_62_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_62_address, 4, 0, &rvi_62_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_62_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_63_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_63_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, (rvi_63_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0d9: ;
    {
    uint64_t rvi_64_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x4), 4, 0, &rvi_64_ptr_value) != 0) return -1;
      uint64_t rvi_64_loaded;
      uint64_t rvi_64_address = (rvi_64_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_64_address, 4, 0, &rvi_64_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_64_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_65_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_65_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_65_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0db: ;
    {
    uint64_t rvi_66_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_66_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, (((rvi_66_a0_value + UINT64_C(0x10)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_67_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x0), 4, 0, &rvi_67_ptr_value) != 0) return -1;
      uint64_t rvi_67_loaded;
      uint64_t rvi_67_address = (rvi_67_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_67_address, 4, 0, &rvi_67_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, (rvi_67_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_68_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x4), 4, 0, &rvi_68_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, (rvi_68_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0de: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_70_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_70_ptr_value) != 0) return -1;
      uint64_t rvi_70_loaded;
      uint64_t rvi_70_address = (rvi_70_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_70_address, 4, 0, &rvi_70_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (rvi_70_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_71_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_71_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_71_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_72_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, &rvi_72_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_72_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0df: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x200), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x20b), 1, 0, (UINT64_C(0x0)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_75_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_75_a0_value) != 0) return -1;
    uint64_t rvi_75_a1_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_75_a1_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, (((rvi_75_a0_value ^ rvi_75_a1_value) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_76_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_76_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x207), 1, 0, (rvi_signed_less(rvi_76_a0_value, UINT64_C(0x0), 4)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_77_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_77_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x206), 1, 0, ((rvi_77_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_78_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x8), 4, 0, &rvi_78_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 4, 0, (((rvi_78_a0_value & UINT64_C(0xff)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_79_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0xd), 4, 0, &rvi_79_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, (rvi_popcount(rvi_79_a0_value)) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_80_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x11), 1, 0, &rvi_80_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, (((rvi_80_a0_value & UINT64_C(0x1)) & rvi_mask(1))) & rvi_mask(1)) != 0) return -1;
    }
    {
    uint64_t rvi_81_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x12), 1, 0, &rvi_81_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x202), 1, 0, ((rvi_81_a0_value == UINT64_C(0x0))) & rvi_mask(1)) != 0) return -1;
    }
rvi_label_000000000065f0e1: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_83_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_83_ptr_value) != 0) return -1;
      uint64_t rvi_83_loaded;
      uint64_t rvi_83_address = (rvi_83_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_83_address, 4, 0, &rvi_83_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (rvi_83_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_84_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_84_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_84_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_85_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, &rvi_85_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_85_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0e2: ;
    {
    uint64_t rvi_86_branch_target_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x0), 4, 0, &rvi_86_branch_target_value) != 0) return -1;
    switch (rvi_86_branch_target_value) {
    case UINT64_C(0x65f0a0): goto rvi_label_000000000065f0a0;
    case UINT64_C(0x65f0a1): goto rvi_label_000000000065f0a1;
    case UINT64_C(0x65f0a3): goto rvi_label_000000000065f0a3;
    case UINT64_C(0x65f0a5): goto rvi_label_000000000065f0a5;
    case UINT64_C(0x65f0a9): goto rvi_label_000000000065f0a9;
    case UINT64_C(0x65f0aa): goto rvi_label_000000000065f0aa;
    case UINT64_C(0x65f0ac): goto rvi_label_000000000065f0ac;
    case UINT64_C(0x65f0ae): goto rvi_label_000000000065f0ae;
    case UINT64_C(0x65f0b0): goto rvi_label_000000000065f0b0;
    case UINT64_C(0x65f0b3): goto rvi_label_000000000065f0b3;
    case UINT64_C(0x65f0b8): goto rvi_label_000000000065f0b8;
    case UINT64_C(0x65f0ba): goto rvi_label_000000000065f0ba;
    case UINT64_C(0x65f0bc): goto rvi_label_000000000065f0bc;
    case UINT64_C(0x65f0be): goto rvi_label_000000000065f0be;
    case UINT64_C(0x65f0c0): goto rvi_label_000000000065f0c0;
    case UINT64_C(0x65f0c5): goto rvi_label_000000000065f0c5;
    case UINT64_C(0x65f0ca): goto rvi_label_000000000065f0ca;
    case UINT64_C(0x65f0cc): goto rvi_label_000000000065f0cc;
    case UINT64_C(0x65f0ce): goto rvi_label_000000000065f0ce;
    case UINT64_C(0x65f0d0): goto rvi_label_000000000065f0d0;
    case UINT64_C(0x65f0d2): goto rvi_label_000000000065f0d2;
    case UINT64_C(0x65f0d7): goto rvi_label_000000000065f0d7;
    case UINT64_C(0x65f0d9): goto rvi_label_000000000065f0d9;
    case UINT64_C(0x65f0db): goto rvi_label_000000000065f0db;
    case UINT64_C(0x65f0de): goto rvi_label_000000000065f0de;
    case UINT64_C(0x65f0df): goto rvi_label_000000000065f0df;
    case UINT64_C(0x65f0e1): goto rvi_label_000000000065f0e1;
    case UINT64_C(0x65f0e2): goto rvi_label_000000000065f0e2;
    case UINT64_C(0x65f0e4): goto rvi_label_000000000065f0e4;
    case UINT64_C(0x65f0e5): goto rvi_label_000000000065f0e5;
    case UINT64_C(0x65f0e6): goto rvi_label_000000000065f0e6;
    default:
        if (rvi_call(ctx, rvi_86_branch_target_value) != 0) return -1;
        return 0;
    }
    }
rvi_label_000000000065f0e4: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_88_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_88_ptr_value) != 0) return -1;
      uint64_t rvi_88_loaded;
      uint64_t rvi_88_address = (rvi_88_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_88_address, 4, 0, &rvi_88_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (rvi_88_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_89_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_89_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_89_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_90_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, &rvi_90_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x1c), 4, 0, (rvi_90_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0e5: ;
    {
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (UINT64_C(0x0)) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_92_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_92_ptr_value) != 0) return -1;
      uint64_t rvi_92_loaded;
      uint64_t rvi_92_address = (rvi_92_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_92_address, 4, 0, &rvi_92_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, (rvi_92_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_93_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_93_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_93_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_94_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "unique", UINT64_C(0x1f), 4, 0, &rvi_94_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x18), 4, 0, (rvi_94_a0_value) & rvi_mask(4)) != 0) return -1;
    }
rvi_label_000000000065f0e6: ;
    {
    uint64_t rvi_95_ptr_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_95_ptr_value) != 0) return -1;
      uint64_t rvi_95_loaded;
      uint64_t rvi_95_address = (rvi_95_ptr_value * UINT64_C(1)) & rvi_mask(4);
      if (rvi_read_space(ctx, "ram", rvi_95_address, 4, 0, &rvi_95_loaded) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x284), 4, 0, (rvi_95_loaded) & rvi_mask(4)) != 0) return -1;
    }
    {
    uint64_t rvi_96_a0_value;
    if (rvi_read_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, &rvi_96_a0_value) != 0) return -1;
    if (rvi_write_value(ctx, _unique, UINT64_C(0), _unique_size, "register", UINT64_C(0x10), 4, 0, (((rvi_96_a0_value + UINT64_C(0x4)) & rvi_mask(4))) & rvi_mask(4)) != 0) return -1;
    }
    {
    return 0;
    }
    return 0;
}
