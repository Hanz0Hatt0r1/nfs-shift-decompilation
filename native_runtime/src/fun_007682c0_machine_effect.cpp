#include "shift_fun_007682c0_machine_effect.hpp"

#include "shift_body_record_adapter.hpp"
#include "shift_fun_007682c0_machine_magnitude.hpp"

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
constexpr std::uint16_t kRetailX87ControlWord = 0x027fu;

constexpr double kCallerGravity = 9.81;
constexpr double kResponseGravity = 9.81000041961669921875;
constexpr double kResponseScale = 1.2999999523162841796875;
constexpr double kHalf = 0.5;
constexpr double kPositiveGain = 0.300000011920928955078125;
constexpr float kProjectionEpsilon = 0.0010000000474974513f;
constexpr float kResponseAngle = 0.52359879016876220703125f;
constexpr float kAngleLimitModeLt2 = 0.698131740093231201171875f;
constexpr float kAngleLimitModeGe2 = 0.9599311351776123046875f;

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument("FUN_007682c0 BODY0 read exceeds record");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < 8u; ++byte) {
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

void require_finite(double value, const char* message) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(message);
    }
}

void validate_input(const Fun007682c0MachineInput& input) {
    require_finite(input.steering, "FUN_007682c0 steering is non-finite");
    for (double value : input.load_terms) {
        require_finite(value, "FUN_007682c0 load term is non-finite");
    }
    require_finite(input.projection_field_x, "FUN_007682c0 projection X is non-finite");
    require_finite(input.projection_field_z, "FUN_007682c0 projection Z is non-finite");
    require_finite(input.response_field_4054, "FUN_007682c0 +0x4054 is non-finite");
}

#if defined(__i386__) || defined(__x86_64__)
struct ScopedRetailX87ControlWord {
    std::uint16_t saved = 0u;
    ScopedRetailX87ControlWord() {
        __asm__ __volatile__("fnstcw %0" : "=m"(saved));
        __asm__ __volatile__("fldcw %0" :: "m"(kRetailX87ControlWord));
    }
    ~ScopedRetailX87ControlWord() {
        __asm__ __volatile__("fldcw %0" :: "m"(saved));
    }
};

float spill_f32(double value) {
    ScopedRetailX87ControlWord cw{};
    float output = 0.0f;
    __asm__ __volatile__(
        "fldl %[in]\n\t"
        "fstps %[out]\n\t"
        : [out] "=m"(output)
        : [in] "m"(value));
    return output;
}

double add64(double lhs, double rhs) {
    ScopedRetailX87ControlWord cw{};
    double output = 0.0;
    __asm__ __volatile__(
        "fldl %[lhs]\n\t"
        "faddl %[rhs]\n\t"
        "fstpl %[out]\n\t"
        : [out] "=m"(output)
        : [lhs] "m"(lhs), [rhs] "m"(rhs));
    return output;
}

double sub64(double lhs, double rhs) {
    ScopedRetailX87ControlWord cw{};
    double output = 0.0;
    __asm__ __volatile__(
        "fldl %[lhs]\n\t"
        "fsubl %[rhs]\n\t"
        "fstpl %[out]\n\t"
        : [out] "=m"(output)
        : [lhs] "m"(lhs), [rhs] "m"(rhs));
    return output;
}

double mul64(double lhs, double rhs) {
    ScopedRetailX87ControlWord cw{};
    double output = 0.0;
    __asm__ __volatile__(
        "fldl %[lhs]\n\t"
        "fmull %[rhs]\n\t"
        "fstpl %[out]\n\t"
        : [out] "=m"(output)
        : [lhs] "m"(lhs), [rhs] "m"(rhs));
    return output;
}

double div64(double lhs, double rhs) {
    ScopedRetailX87ControlWord cw{};
    double output = 0.0;
    __asm__ __volatile__(
        "fldl %[lhs]\n\t"
        "fdivl %[rhs]\n\t"
        "fstpl %[out]\n\t"
        : [out] "=m"(output)
        : [lhs] "m"(lhs), [rhs] "m"(rhs));
    return output;
}
#else
float spill_f32(double) {
    throw std::runtime_error("FUN_007682c0 PC f32 spill requires x87-capable x86 host");
}
double add64(double, double) {
    throw std::runtime_error("FUN_007682c0 PC arithmetic requires x87-capable x86 host");
}
double sub64(double, double) { return add64(0.0, 0.0); }
double mul64(double, double) { return add64(0.0, 0.0); }
double div64(double, double) { return add64(0.0, 0.0); }
#endif

float clamp01(float value) {
    if (value <= 0.0f) return 0.0f;
    if (value >= 1.0f) return 1.0f;
    return value;
}

struct PlanarGeometry {
    float speed = 0.0f;
    float reciprocal = 0.0f;
    bool valid = false;
};

PlanarGeometry execute_planar_geometry(
    double velocity_x,
    double velocity_z,
    float projection_x,
    float projection_z) {
    PlanarGeometry result{};
    result.speed = fun_0075ada0_pc_x87_planar_speed_f32(
        velocity_x, velocity_z);
    if (result.speed < 4.0f) {
        return result;
    }
    result.valid = true;

    const float vx = spill_f32(velocity_x);
    const float vz = spill_f32(velocity_z);
    const float inv_speed = spill_f32(div64(1.0, static_cast<double>(result.speed)));
    const float dir_x = spill_f32(mul64(vx, inv_speed));
    const float dir_z = spill_f32(mul64(vz, inv_speed));
    const float lateral_x = spill_f32(-static_cast<double>(dir_z));
    const float lateral_z = spill_f32(static_cast<double>(dir_x));

    const double x_part = mul64(lateral_x, projection_x);
    const double z_part = mul64(lateral_z, projection_z);
    const float projection = spill_f32(add64(x_part, z_part));
    if (std::fabs(projection) < kProjectionEpsilon) {
        result.reciprocal = 0.0f;
        return result;
    }

    const double speed_sq = mul64(result.speed, result.speed);
    const float radius = spill_f32(div64(speed_sq, projection));
    result.reciprocal = spill_f32(
        -div64(static_cast<double>(result.speed), static_cast<double>(radius)));
    return result;
}

float execute_response(
    float body_cross_y,
    float steering,
    float angle_limit,
    float speed_factor,
    float reciprocal,
    float response_field_4054,
    float body_scalar_120) {
    const float delta = spill_f32(sub64(body_cross_y, reciprocal));
    float angle_delta = spill_f32(
        sub64(std::fabs(static_cast<double>(steering)), angle_limit));
    if (angle_delta < 0.0f) {
        return 0.0f;
    }
    if (angle_delta > kResponseAngle) {
        angle_delta = kResponseAngle;
    }

    const float sign = steering > 0.0f ? 1.0f : steering < 0.0f ? -1.0f : 0.0f;

    double body_scaled = mul64(body_scalar_120, kResponseGravity);
    body_scaled = mul64(body_scaled, kResponseScale);
    const double vehicle_scaled = mul64(response_field_4054, kHalf);
    const float base = spill_f32(mul64(vehicle_scaled, body_scaled));
    const float negative_speed_factor = spill_f32(-static_cast<double>(speed_factor));

    double term_b_extended = mul64(negative_speed_factor, 1.0);
    term_b_extended = mul64(term_b_extended, angle_delta);
    term_b_extended = mul64(base, term_b_extended);
    const float term_b = spill_f32(term_b_extended);

    const float signed_delta = spill_f32(mul64(-static_cast<double>(sign), delta));
    float gain = 5.0f;
    if (signed_delta >= 0.0f) {
        float normalized = spill_f32(div64(angle_delta, kResponseAngle));
        normalized = clamp01(normalized);
        gain = spill_f32(mul64(normalized, kPositiveGain));
    }
    const float scaled_gain = spill_f32(mul64(gain, 1.0));

    double term_a_extended = mul64(base, scaled_gain);
    term_a_extended = mul64(term_a_extended, negative_speed_factor);
    term_a_extended = mul64(term_a_extended, signed_delta);
    const float term_a = spill_f32(term_a_extended);
    const float combined = spill_f32(add64(term_a, term_b));

    if (combined < 0.0f) {
        return spill_f32(mul64(-static_cast<double>(sign), combined));
    }
    return 0.0f;
}

}  // namespace

Fun007682c0MachineEffectResult execute_fun_007682c0_machine_effect(
    const Fun007682c0MachineInput& input,
    const std::vector<std::uint8_t>& current_body_bytes) {
    validate_input(input);
    if (current_body_bytes.size() < kBodyRecordSize ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007682c0 machine effect requires complete BODY records");
    }

    Fun007682c0MachineEffectResult result{};
    result.caller_gate_open = input.caller_gate_open;
    result.upstream_machine_magnitude_used = true;
    if (!input.caller_gate_open) {
        return result;
    }

    const double body_cross_y = read_f64_le(current_body_bytes, kBody0CrossY);
    const double velocity_x = read_f64_le(current_body_bytes, kBody0VelocityX);
    const double velocity_y = read_f64_le(current_body_bytes, kBody0VelocityY);
    const double velocity_z = read_f64_le(current_body_bytes, kBody0VelocityZ);
    const double body_scalar_120 = read_f64_le(current_body_bytes, kBody0Scalar120);
    require_finite(body_cross_y, "FUN_007682c0 BODY0+0x20 is non-finite");
    require_finite(velocity_x, "FUN_007682c0 BODY0+0x78 is non-finite");
    require_finite(velocity_y, "FUN_007682c0 BODY0+0x80 is non-finite");
    require_finite(velocity_z, "FUN_007682c0 BODY0+0x88 is non-finite");
    require_finite(body_scalar_120, "FUN_007682c0 BODY0+0x120 is non-finite");
    if (body_scalar_120 == 0.0) {
        throw std::invalid_argument("FUN_007682c0 BODY0+0x120 cannot be zero");
    }

    double load_sum = 0.0; // FUN_00769ef0 also adds a proven zero QWORD constant.
    for (double term : input.load_terms) {
        load_sum = add64(load_sum, term);
    }
    const double denominator = mul64(body_scalar_120, kCallerGravity);
    result.caller_scale = clamp01(spill_f32(div64(load_sum, denominator)));

    const auto magnitude = fun_007682c0_pc_machine_magnitude(
        velocity_x, velocity_y, velocity_z);
    result.speed_3d = magnitude.speed_3d;
    result.speed_gate_open = magnitude.speed_gate_open;
    result.speed_factor = magnitude.speed_factor;
    if (!result.speed_gate_open) {
        return result;
    }

    const PlanarGeometry geometry = execute_planar_geometry(
        velocity_x,
        velocity_z,
        input.projection_field_x,
        input.projection_field_z);
    result.planar_speed = geometry.speed;
    result.reciprocal_like = geometry.reciprocal;
    result.planar_geometry_valid = geometry.valid;

    const float body_cross_y_f32 = spill_f32(body_cross_y);
    const float body_scalar_120_f32 = spill_f32(body_scalar_120);
    const float angle_limit = input.angle_mode >= 2
        ? kAngleLimitModeGe2
        : kAngleLimitModeLt2;
    result.response = execute_response(
        body_cross_y_f32,
        input.steering,
        angle_limit,
        result.speed_factor,
        result.reciprocal_like,
        input.response_field_4054,
        body_scalar_120_f32);

    const float delta = spill_f32(mul64(result.response, result.caller_scale));
    result.effect.gate_open = true;
    result.effect.accumulator_y_delta = static_cast<double>(delta);
    return result;
}

}  // namespace shift::runtime::physics
