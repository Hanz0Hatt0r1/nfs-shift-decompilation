#include "shift_fun_007682c0_machine_effect.hpp"

#include "shift_body_record_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::size_t kBody0CrossY = 0x20u;
constexpr std::size_t kBody0VelocityX = 0x78u;
constexpr std::size_t kBody0VelocityY = 0x80u;
constexpr std::size_t kBody0VelocityZ = 0x88u;
constexpr std::size_t kBody0Scalar120 = 0x120u;

constexpr double kRetailGravity = 9.81000041961669921875;
constexpr double kRetailResponseScale = 1.2999999523162841796875;
constexpr double kRetailHalf = 0.5;
constexpr double kRetailSpeedOffset = 5.0;
constexpr double kRetailSpeedRange = 15.0;

float f32_from_bits(std::uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument("FUN_007682c0 BODY0 read exceeds persistent BODY record");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

double read_f64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    const std::uint64_t bits = read_u64_le(bytes, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
}

void validate_input(const Fun007682c0MachineInput& input) {
    require_finite(input.steering, "FUN_007682c0 steering is non-finite");
    for (const double value : input.load_terms) {
        require_finite(value, "FUN_007682c0 caller load term is non-finite");
    }
    require_finite(
        input.projection_field_x,
        "FUN_007682c0 projection field X is non-finite");
    require_finite(
        input.projection_field_z,
        "FUN_007682c0 projection field Z is non-finite");
    require_finite(
        input.response_field_4054,
        "FUN_007682c0 response field +0x4054 is non-finite");
}

// Force the same f64 precision boundary used by PC x87 with precision-control
// 10b (double precision). Volatile prevents contraction/reassociation across
// the explicit retail operation boundaries.
double add64(double lhs, double rhs) {
    volatile double result = lhs + rhs;
    return result;
}

double sub64(double lhs, double rhs) {
    volatile double result = lhs - rhs;
    return result;
}

double mul64(double lhs, double rhs) {
    volatile double result = lhs * rhs;
    return result;
}

double div64(double lhs, double rhs) {
    volatile double result = lhs / rhs;
    return result;
}

float retail_f32_spill(double value) {
    require_finite(value, "FUN_007682c0 f32 spill source is non-finite");
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    asm volatile("fldl %1; fstps %0" : "=m"(output) : "m"(value));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_007682c0 retail f32 spill requires x87-capable x86 host");
#endif
}

float retail_x87_fsqrt_to_f32(double value) {
    require_finite(value, "FUN_007682c0 FSQRT source is non-finite");
    if (value < 0.0) {
        throw std::invalid_argument("FUN_007682c0 FSQRT source is negative");
    }
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    asm volatile("fldl %1; fsqrt; fstps %0" : "=m"(output) : "m"(value));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_007682c0 retail FSQRT requires x87-capable x86 host");
#endif
}

float clamp01_f32(float value) {
    if (value <= 0.0f) {
        return 0.0f;
    }
    if (value >= 1.0f) {
        return 1.0f;
    }
    return value;
}

struct PlanarGeometry {
    float speed = 0.0f;
    float reciprocal_like = 0.0f;
    bool valid = false;
};

PlanarGeometry execute_fun_0075ada0_machine_shape(
    double velocity_x,
    double velocity_z,
    float projection_field_x,
    float projection_field_z) {
    const float vx = retail_f32_spill(velocity_x);
    const float vz = retail_f32_spill(velocity_z);

    // FUN_0075ada0 spills the squared magnitude to f32 before calling the CRT
    // sqrt helper, unlike the initial FUN_007682c0 3D magnitude.
    const double vx2 = mul64(static_cast<double>(vx), static_cast<double>(vx));
    const double vz2 = mul64(static_cast<double>(vz), static_cast<double>(vz));
    const float squared = retail_f32_spill(add64(vx2, vz2));
    const float speed = retail_x87_fsqrt_to_f32(static_cast<double>(squared));

    PlanarGeometry result{};
    result.speed = speed;
    if (speed < 4.0f) {
        return result;
    }
    result.valid = true;

    const float reciprocal_speed =
        retail_f32_spill(div64(1.0, static_cast<double>(speed)));
    const float direction_x = retail_f32_spill(
        mul64(static_cast<double>(vx), static_cast<double>(reciprocal_speed)));
    const float direction_z = retail_f32_spill(
        mul64(static_cast<double>(vz), static_cast<double>(reciprocal_speed)));

    // Exact direction x (0,1,0) shape from helper 0x0047bdb0.
    const float lateral_x = retail_f32_spill(-static_cast<double>(direction_z));
    const float lateral_z = retail_f32_spill(static_cast<double>(direction_x));

    const double projected_x = mul64(
        static_cast<double>(lateral_x),
        static_cast<double>(projection_field_x));
    const double projected_z = mul64(
        static_cast<double>(lateral_z),
        static_cast<double>(projection_field_z));
    const float projection = retail_f32_spill(add64(projected_x, projected_z));
    const float absolute_projection =
        retail_f32_spill(std::fabs(static_cast<double>(projection)));
    if (absolute_projection < f32_from_bits(0x3a83126fu)) { // 0.001f
        result.reciprocal_like = 0.0f;
        return result;
    }

    const float speed_squared = retail_f32_spill(
        mul64(static_cast<double>(speed), static_cast<double>(speed)));
    const float radius_like = retail_f32_spill(
        div64(static_cast<double>(speed_squared), static_cast<double>(projection)));
    result.reciprocal_like = retail_f32_spill(
        -div64(static_cast<double>(speed), static_cast<double>(radius_like)));
    return result;
}

float execute_fun_007595d0_machine_shape(
    float body_cross_y,
    float steering,
    float angle_limit,
    float speed_factor,
    float reciprocal_like,
    float response_field_4054,
    float body_scalar_120) {
    const float delta = retail_f32_spill(
        sub64(static_cast<double>(body_cross_y), static_cast<double>(reciprocal_like)));
    float angle_delta = retail_f32_spill(
        sub64(std::fabs(static_cast<double>(steering)), static_cast<double>(angle_limit)));
    if (angle_delta < 0.0f) {
        return 0.0f;
    }

    const float response_angle = f32_from_bits(0x3f060a92u); // 0.5235988f
    if (angle_delta > response_angle) {
        angle_delta = response_angle;
    }

    const float sign = steering > 0.0f ? 1.0f : steering < 0.0f ? -1.0f : 0.0f;

    const double body_scaled = mul64(
        mul64(static_cast<double>(body_scalar_120), kRetailGravity),
        kRetailResponseScale);
    const double field_scaled =
        mul64(static_cast<double>(response_field_4054), kRetailHalf);
    const float base = retail_f32_spill(mul64(field_scaled, body_scaled));
    const float negative_speed_factor =
        retail_f32_spill(-static_cast<double>(speed_factor));

    const float signed_delta = retail_f32_spill(
        mul64(-static_cast<double>(sign), static_cast<double>(delta)));

    float response_gain = 5.0f;
    if (signed_delta >= 0.0f) {
        const float normalized_angle = clamp01_f32(retail_f32_spill(
            div64(static_cast<double>(angle_delta), static_cast<double>(response_angle))));
        response_gain = retail_f32_spill(
            mul64(static_cast<double>(normalized_angle),
                  static_cast<double>(f32_from_bits(0x3e99999au)))); // 0.3f
    }

    const double term_a = mul64(
        mul64(
            mul64(static_cast<double>(base), static_cast<double>(response_gain)),
            static_cast<double>(negative_speed_factor)),
        static_cast<double>(signed_delta));
    const double term_b = mul64(
        mul64(static_cast<double>(base), static_cast<double>(negative_speed_factor)),
        static_cast<double>(angle_delta));
    const float combined = retail_f32_spill(add64(term_a, term_b));

    if (combined >= 0.0f) {
        return 0.0f;
    }
    return retail_f32_spill(
        mul64(-static_cast<double>(sign), static_cast<double>(combined)));
}

}  // namespace

Fun007682c0MachineEffectResult execute_fun_007682c0_machine_effect(
    const Fun007682c0MachineInput& input,
    const std::vector<std::uint8_t>& current_body_bytes) {
    validate_input(input);
    if (current_body_bytes.size() < kBodyRecordSize ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007682c0 machine effect requires complete persistent BODY records");
    }

    Fun007682c0MachineEffectResult result{};
    result.caller_gate_open = input.caller_gate_open;
    result.x87_fsqrt_used = true;
    if (!input.caller_gate_open) {
        return result;
    }

    const double body_cross_y = read_f64_le(current_body_bytes, kBody0CrossY);
    const double velocity_x = read_f64_le(current_body_bytes, kBody0VelocityX);
    const double velocity_y = read_f64_le(current_body_bytes, kBody0VelocityY);
    const double velocity_z = read_f64_le(current_body_bytes, kBody0VelocityZ);
    const double body_scalar_120 = read_f64_le(current_body_bytes, kBody0Scalar120);
    require_finite(body_cross_y, "FUN_007682c0 BODY0 +0x20 is non-finite");
    require_finite(velocity_x, "FUN_007682c0 BODY0 +0x78 is non-finite");
    require_finite(velocity_y, "FUN_007682c0 BODY0 +0x80 is non-finite");
    require_finite(velocity_z, "FUN_007682c0 BODY0 +0x88 is non-finite");
    require_finite(body_scalar_120, "FUN_007682c0 BODY0 +0x120 is non-finite");
    if (body_scalar_120 == 0.0) {
        throw std::invalid_argument("FUN_007682c0 BODY0 +0x120 cannot be zero");
    }

    // FUN_00769ef0 caller-side param_2 production.
    double load_sum = 0.0;
    for (const double term : input.load_terms) {
        load_sum = add64(load_sum, term);
    }
    const double denominator = mul64(body_scalar_120, kRetailGravity);
    result.caller_scale = clamp01_f32(retail_f32_spill(div64(load_sum, denominator)));

    // FUN_007682c0 initial 3D magnitude keeps f64 precision through the square
    // sum and spills only the FSQRT result to f32 at 0x00768305.
    const double x2 = mul64(velocity_x, velocity_x);
    const double y2 = mul64(velocity_y, velocity_y);
    const double z2 = mul64(velocity_z, velocity_z);
    const double speed_squared = add64(add64(y2, x2), z2);
    result.speed_3d = retail_x87_fsqrt_to_f32(speed_squared);
    if (result.speed_3d < 5.0f) {
        return result;
    }
    result.speed_gate_open = true;

    result.speed_factor = clamp01_f32(retail_f32_spill(div64(
        sub64(static_cast<double>(result.speed_3d), kRetailSpeedOffset),
        kRetailSpeedRange)));

    const PlanarGeometry geometry = execute_fun_0075ada0_machine_shape(
        velocity_x,
        velocity_z,
        input.projection_field_x,
        input.projection_field_z);
    result.planar_speed = geometry.speed;
    result.reciprocal_like = geometry.reciprocal_like;
    result.planar_geometry_valid = geometry.valid;

    const float angle_limit = input.angle_mode >= 2
        ? f32_from_bits(0x3f75be0cu) // 0.95993114f
        : f32_from_bits(0x3f32b8c3u); // 0.69813174f
    const float body_cross_y_f32 = retail_f32_spill(body_cross_y);
    const float body_scalar_120_f32 = retail_f32_spill(body_scalar_120);
    result.response = execute_fun_007595d0_machine_shape(
        body_cross_y_f32,
        input.steering,
        angle_limit,
        result.speed_factor,
        result.reciprocal_like,
        input.response_field_4054,
        body_scalar_120_f32);

    const float delta = retail_f32_spill(mul64(
        static_cast<double>(result.response),
        static_cast<double>(result.caller_scale)));
    result.effect.gate_open = true;
    result.effect.accumulator_y_delta = static_cast<double>(delta);
    return result;
}

}  // namespace shift::runtime::physics
