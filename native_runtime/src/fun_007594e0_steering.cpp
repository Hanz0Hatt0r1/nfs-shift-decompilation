#include "shift_fun_007594e0_steering.hpp"

#include "shift_body_record_adapter.hpp"

#include <array>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::size_t kBody0VelocityX = 0x78u;
constexpr std::size_t kBody0VelocityY = 0x80u;
constexpr std::size_t kBody0VelocityZ = 0x88u;
constexpr double kRetailPlanarSquaredGate = 0.1;

std::uint32_t read_u32_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint32_t)) {
        throw std::invalid_argument("FUN_007594e0 BODY0 f32 read exceeds record");
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
        throw std::invalid_argument("FUN_007594e0 BODY0 f64 read exceeds record");
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

// PC retail runs these x87 operations with precision-control 10b (53-bit).
// Volatile binary64 checkpoints preserve the same operation boundaries for the
// basis transform and planar squared sum on x86_64 SSE builds.
double add64(double lhs, double rhs) {
    volatile double result = lhs + rhs;
    return result;
}

double mul64(double lhs, double rhs) {
    volatile double result = lhs * rhs;
    return result;
}

double transform_axis(
    double vx,
    double vy,
    double vz,
    float basis_x,
    float basis_y,
    float basis_z) {
    const double y_term = mul64(static_cast<double>(basis_y), vy);
    const double x_term = mul64(static_cast<double>(basis_x), vx);
    const double xy = add64(y_term, x_term);
    const double z_term = mul64(static_cast<double>(basis_z), vz);
    return add64(xy, z_term);
}

float retail_fpatan_to_f32(double y, double x) {
    require_finite(y, "FUN_007594e0 FPATAN y input is non-finite");
    require_finite(x, "FUN_007594e0 FPATAN x input is non-finite");
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    // FPATAN computes atan2(ST1, ST0). Load y first and x second so ST1=y,
    // ST0=x, matching the finite normal path of the retail CRT helper.
    asm volatile(
        "fldl %2; fldl %1; fpatan; fstps %0"
        : "=m"(output)
        : "m"(x), "m"(y));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_007594e0 retail FPATAN requires x87-capable x86 host");
#endif
}

}  // namespace

Fun007594e0SteeringResult execute_fun_007594e0_steering(
    const std::vector<std::uint8_t>& current_body_bytes) {
    if (current_body_bytes.size() < kBodyRecordSize ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007594e0 steering requires complete persistent BODY records");
    }

    const double vx = read_f64_le(current_body_bytes, kBody0VelocityX);
    const double vy = read_f64_le(current_body_bytes, kBody0VelocityY);
    const double vz = read_f64_le(current_body_bytes, kBody0VelocityZ);
    require_finite(vx, "FUN_007594e0 BODY0 +0x78 is non-finite");
    require_finite(vy, "FUN_007594e0 BODY0 +0x80 is non-finite");
    require_finite(vz, "FUN_007594e0 BODY0 +0x88 is non-finite");

    std::array<float, 9> basis{};
    for (std::size_t index = 0u; index < basis.size(); ++index) {
        basis[index] = read_f32_le(
            current_body_bytes,
            body_record_offset::kBasis[index]);
        require_finite(basis[index], "FUN_007594e0 BODY0 basis is non-finite");
    }

    // Helper 0x007af0a0 computes basis^T * velocity. FUN_007594e0 only uses
    // the transformed X/Z components for its angle gate and FPATAN operands.
    const double local_x = transform_axis(
        vx, vy, vz, basis[0], basis[3], basis[6]);
    const double local_z = transform_axis(
        vx, vy, vz, basis[2], basis[5], basis[8]);
    require_finite(local_x, "FUN_007594e0 transformed X is non-finite");
    require_finite(local_z, "FUN_007594e0 transformed Z is non-finite");

    const double x2 = mul64(local_x, local_x);
    const double z2 = mul64(local_z, local_z);
    const double planar_squared = add64(x2, z2);
    require_finite(planar_squared, "FUN_007594e0 planar square sum is non-finite");

    Fun007594e0SteeringResult result{};
    result.local_velocity_x = local_x;
    result.local_velocity_z = local_z;
    result.planar_squared = planar_squared;
    if (planar_squared <= kRetailPlanarSquaredGate) {
        return result;
    }

    result.angle_gate_open = true;
    result.x87_fpatan_used = true;
    // Retail stack before helper 0x0090285a is ST0=-local_z, ST1=-local_x;
    // its finite normal path reaches FPATAN at 0x0091077b.
    result.steering = retail_fpatan_to_f32(-local_x, -local_z);
    if (!std::isfinite(result.steering)) {
        throw std::invalid_argument("FUN_007594e0 steering result is non-finite");
    }
    return result;
}

}  // namespace shift::runtime::physics
