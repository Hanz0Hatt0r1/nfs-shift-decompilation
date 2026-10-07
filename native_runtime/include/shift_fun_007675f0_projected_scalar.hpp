#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_fun_007675f0_body_owned_scalars.hpp"
#include "shift_wheel_force_aggregate.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0ProjectedScalarJoinFormat =
    "SHIFT.Fun007675f0ProjectedScalarJoin/1";

struct Fun007675f0ProjectedScalarJoinResult {
    WheelForceAggregateVectorOutputs aggregate{};
    std::array<float, 3> planar_direction{};
    float aggregate_x = 0.0f;
    float aggregate_z = 0.0f;
    float projected_scalar = 0.0f;
};

inline double fun_00759c90_read_body0_f64(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t offset) {
    if (body_bytes.size() < kBodyRecordSize ||
        body_bytes.size() % kBodyRecordSize != 0u ||
        offset > body_bytes.size() ||
        body_bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument(
            "FUN_00759c90 BODY0 position requires complete BODY records");
    }
    std::uint64_t bits = 0u;
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bits |= static_cast<std::uint64_t>(body_bytes[offset + byte])
            << (byte * 8u);
    }
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "FUN_00759c90 BODY0 position contains non-finite value");
    }
    return value;
}

inline WheelForceAggregateVector3d derive_fun_00759c90_body0_position(
    const std::vector<std::uint8_t>& body_bytes) {
    return {
        fun_00759c90_read_body0_f64(body_bytes, body_record_offset::kOrigin[0]),
        fun_00759c90_read_body0_f64(body_bytes, body_record_offset::kOrigin[1]),
        fun_00759c90_read_body0_f64(body_bytes, body_record_offset::kOrigin[2]),
    };
}

inline std::array<float, 3> derive_fun_007675f0_source_planar_direction(
    const ContactOuterVector3d& planar_delta) {
    const float delta_x = fun_007675f0_source_f32(
        planar_delta[0], "FUN_007675f0 projected-scalar delta X invalid");
    const float delta_z = fun_007675f0_source_f32(
        planar_delta[2], "FUN_007675f0 projected-scalar delta Z invalid");
    const float distance_sq = fun_007675f0_source_f32(
        static_cast<double>(delta_x) * delta_x + 0.0 +
            static_cast<double>(delta_z) * delta_z,
        "FUN_007675f0 projected-scalar distance square invalid");
    const float distance = fun_007675f0_source_sqrt_f32(
        distance_sq,
        "FUN_007675f0 projected-scalar distance invalid");
    if (distance == 0.0f) {
        throw std::invalid_argument(
            "FUN_007675f0 projected scalar requires non-zero planar distance");
    }
    const float inverse = fun_007675f0_source_f32(
        1.0 / static_cast<double>(distance),
        "FUN_007675f0 projected-scalar reciprocal invalid");
    return {
        fun_007675f0_source_f32(
            static_cast<double>(inverse) * delta_x,
            "FUN_007675f0 projected-scalar direction X invalid"),
        0.0f,
        fun_007675f0_source_f32(
            static_cast<double>(inverse) * delta_z,
            "FUN_007675f0 projected-scalar direction Z invalid"),
    };
}

inline float fun_007675f0_project_total_xz_source_f32(
    float total_x,
    float total_z,
    const std::array<float, 3>& direction) {
    // PC 0x007677c6..0x007677df evaluates X*dirX + dirY*0.0 + Z*dirZ
    // on x87 and spills only the final sum to f32. A binary64 expression keeps
    // that no-intermediate-f32-spill property without claiming host x87 identity.
    const double value =
        static_cast<double>(total_x) * direction[0] +
        static_cast<double>(direction[1]) * 0.0 +
        static_cast<double>(total_z) * direction[2];
    return fun_007675f0_source_f32(
        value,
        "FUN_007675f0 projected scalar overflow");
}

inline Fun007675f0ProjectedScalarJoinResult
execute_fun_007675f0_projected_scalar_join(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position,
    const ContactOuterVector3d& planar_delta) {
    Fun007675f0ProjectedScalarJoinResult result{};
    result.aggregate = execute_fun_00759c90_vector_outputs(records, body_position);
    result.planar_direction =
        derive_fun_007675f0_source_planar_direction(planar_delta);
    result.aggregate_x = fun_007675f0_source_f32(
        result.aggregate.total[0],
        "FUN_007675f0 FUN_00759c90 total X f32 spill invalid");
    result.aggregate_z = fun_007675f0_source_f32(
        result.aggregate.total[2],
        "FUN_007675f0 FUN_00759c90 total Z f32 spill invalid");
    result.projected_scalar = fun_007675f0_project_total_xz_source_f32(
        result.aggregate_x,
        result.aggregate_z,
        result.planar_direction);
    return result;
}

}  // namespace shift::runtime::physics
