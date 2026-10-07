#include "shift_fun_007594e0_machine_angle.hpp"

#include "shift_body_record_adapter.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr double kRetailPlanarSquaredGate = 0.1;

std::uint32_t read_u32_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint32_t)) {
        throw std::invalid_argument("FUN_007594e0 BODY0 f32 read exceeds persistent BODY record");
    }
    std::uint32_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint32_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument("FUN_007594e0 BODY0 f64 read exceeds persistent BODY record");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

float read_f32_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    const std::uint32_t bits = read_u32_le(bytes, offset);
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
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

// PC x87 precision-control is 10b (53-bit/double precision). Keep every
// multiply/add as an explicit f64 boundary so a host compiler cannot contract
// or reassociate the BODY-basis transform.
double mul64(double lhs, double rhs) {
    volatile double result = lhs * rhs;
    return result;
}

double add64(double lhs, double rhs) {
    volatile double result = lhs + rhs;
    return result;
}

float retail_crt_atan2_to_f32(double numerator, double denominator) {
    require_finite(numerator, "FUN_007594e0 atan2 numerator is non-finite");
    require_finite(denominator, "FUN_007594e0 atan2 denominator is non-finite");

#if defined(__i386__) || defined(__x86_64__)
    const bool denominator_negative = std::signbit(denominator);
    const bool numerator_negative = std::signbit(numerator);
    const double absolute_denominator = std::fabs(denominator);
    const double absolute_numerator = std::fabs(numerator);

    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));

    if (denominator_negative && numerator_negative) {
        // PC CRT normal path at 0x00910773..0x0091078b:
        // abs/abs -> FPATAN -> pi-angle for negative denominator -> FCHS for
        // negative numerator -> f32 store at the FUN_0076f970 caller.
        asm volatile(
            "fldl %[num]; fldl %[den]; fpatan; fldpi; "
            ".byte 0xde, 0xe1; fchs; fstps %[out]"
            : [out] "=m"(output)
            : [num] "m"(absolute_numerator),
              [den] "m"(absolute_denominator));
    } else if (denominator_negative) {
        asm volatile(
            "fldl %[num]; fldl %[den]; fpatan; fldpi; "
            ".byte 0xde, 0xe1; fstps %[out]"
            : [out] "=m"(output)
            : [num] "m"(absolute_numerator),
              [den] "m"(absolute_denominator));
    } else if (numerator_negative) {
        asm volatile(
            "fldl %[num]; fldl %[den]; fpatan; fchs; fstps %[out]"
            : [out] "=m"(output)
            : [num] "m"(absolute_numerator),
              [den] "m"(absolute_denominator));
    } else {
        asm volatile(
            "fldl %[num]; fldl %[den]; fpatan; fstps %[out]"
            : [out] "=m"(output)
            : [num] "m"(absolute_numerator),
              [den] "m"(absolute_denominator));
    }

    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_007594e0 retail atan2 requires x87-capable x86 host");
#endif
}

}  // namespace

Fun007594e0MachineAngleResult execute_fun_007594e0_machine_angle(
    const std::vector<std::uint8_t>& current_body_bytes) {
    if (current_body_bytes.size() < kBodyRecordSize ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007594e0 machine angle requires complete persistent BODY records");
    }

    const double velocity_x =
        read_f64_le(current_body_bytes, body_record_offset::kMotionTriplet[0]);
    const double velocity_y =
        read_f64_le(current_body_bytes, body_record_offset::kMotionTriplet[1]);
    const double velocity_z =
        read_f64_le(current_body_bytes, body_record_offset::kMotionTriplet[2]);
    require_finite(velocity_x, "FUN_007594e0 BODY0 +0x78 is non-finite");
    require_finite(velocity_y, "FUN_007594e0 BODY0 +0x80 is non-finite");
    require_finite(velocity_z, "FUN_007594e0 BODY0 +0x88 is non-finite");

    std::array<float, 9> basis{};
    for (std::size_t index = 0u; index < basis.size(); ++index) {
        basis[index] = read_f32_le(
            current_body_bytes,
            body_record_offset::kBasis[index]);
        require_finite(
            static_cast<double>(basis[index]),
            "FUN_007594e0 BODY0 basis contains non-finite f32");
    }

    // Exact FUN_007af0a0 operation order for the two components consumed by
    // FUN_007594e0. The BODY basis is stored as nine f32 values while motion is
    // f64. out.x = m3*vy + m0*vx + m6*vz; out.z = m2*vx + m5*vy + m8*vz.
    const double local_x = add64(
        add64(
            mul64(static_cast<double>(basis[3]), velocity_y),
            mul64(static_cast<double>(basis[0]), velocity_x)),
        mul64(static_cast<double>(basis[6]), velocity_z));
    const double local_z = add64(
        add64(
            mul64(static_cast<double>(basis[2]), velocity_x),
            mul64(static_cast<double>(basis[5]), velocity_y)),
        mul64(static_cast<double>(basis[8]), velocity_z));
    require_finite(local_x, "FUN_007594e0 transformed local X is non-finite");
    require_finite(local_z, "FUN_007594e0 transformed local Z is non-finite");

    // PC sequence squares Z first and X second, then compares the f64 sum with
    // 0.1. Equal, lower, or unordered values return +0.0.
    const double planar_squared = add64(
        mul64(local_z, local_z),
        mul64(local_x, local_x));
    require_finite(
        planar_squared,
        "FUN_007594e0 planar squared magnitude is non-finite");

    Fun007594e0MachineAngleResult result{};
    result.local_x = local_x;
    result.local_z = local_z;
    result.planar_squared = planar_squared;
    result.x87_fpatan_used = true;
    if (!(planar_squared > kRetailPlanarSquaredGate)) {
        return result;
    }

    result.planar_gate_open = true;
    result.steering = retail_crt_atan2_to_f32(-local_x, -local_z);
    return result;
}

}  // namespace shift::runtime::physics
