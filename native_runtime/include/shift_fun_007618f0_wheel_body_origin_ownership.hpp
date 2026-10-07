#pragma once

#include "shift_bmw_wheel_spindle_body_topology.hpp"
#include "shift_body_record_adapter.hpp"
#include "shift_fun_007618f0_local_sample_producer.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun007618f0WheelBodyOriginOwnershipFormat =
    "SHIFT.Fun007618f0WheelBodyOriginOwnership/1";

inline constexpr std::size_t kFun007618f0HdVehicleWheelPointer0820 = 0x820u;
inline constexpr std::size_t kFun007618f0HdVehicleWheelPointer12a0 = 0x12a0u;
inline constexpr std::size_t kFun007618f0FlWheelSlot = 0u;
inline constexpr std::size_t kFun007618f0FrWheelSlot = 1u;

struct Fun007618f0RemainingSourceInput {
    double source_scalar_0338 = 0.0;
    CollisionQueryVector3d source_vec_0918{};
};

struct Fun007618f0WheelBodyOriginOwnershipResult {
    std::size_t fl_wheel_body_index = 0u;
    std::size_t fr_wheel_body_index = 0u;
    CollisionQueryVector3d fl_wheel_body_origin{};
    CollisionQueryVector3d fr_wheel_body_origin{};
    Fun007618f0LocalSampleProducerInput producer_input{};
};

inline double fun_007618f0_read_body_f64_le(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_index,
    std::size_t body_relative_offset,
    const char* label) {
    if (body_bytes.empty() || body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007618f0 wheel BODY ownership requires exact 0x170-byte BODY records");
    }
    const std::size_t body_count = body_bytes.size() / kBodyRecordSize;
    if (body_index >= body_count) {
        throw std::invalid_argument(
            "FUN_007618f0 wheel BODY index exceeds persistent BODY domain");
    }
    const std::size_t offset = body_index * kBodyRecordSize + body_relative_offset;
    if (offset > body_bytes.size() || body_bytes.size() - offset < sizeof(double)) {
        throw std::invalid_argument(
            "FUN_007618f0 wheel BODY origin read exceeds persistent BODY buffer");
    }
    std::uint64_t bits = 0u;
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bits |= static_cast<std::uint64_t>(body_bytes[offset + byte]) << (byte * 8u);
    }
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
    return value;
}

inline CollisionQueryVector3d fun_007618f0_read_body_origin(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_index,
    const char* label) {
    return {
        fun_007618f0_read_body_f64_le(
            body_bytes, body_index, body_record_offset::kOrigin[0], label),
        fun_007618f0_read_body_f64_le(
            body_bytes, body_index, body_record_offset::kOrigin[1], label),
        fun_007618f0_read_body_f64_le(
            body_bytes, body_index, body_record_offset::kOrigin[2], label),
    };
}

inline Fun007618f0WheelBodyOriginOwnershipResult
compose_fun_007618f0_input_from_current_bmw_wheel_bodies(
    const std::vector<std::uint8_t>& current_body_bytes,
    const Fun007618f0RemainingSourceInput& remaining_source) {
    const auto& topology = bmw_m3_e36_retail_wheel_spindle_body_topology();
    if (!topology.wheel_spindle_body_indices_ready ||
        topology.body_count != kBmwM3E36RetailBodyCount) {
        throw std::logic_error(
            "FUN_007618f0 BMW wheel BODY topology is not source-backed and ready");
    }
    if (current_body_bytes.size() != topology.body_count * kBodyRecordSize) {
        throw std::invalid_argument(
            "FUN_007618f0 selected BMW BODY buffer cardinality mismatch");
    }
    if (!std::isfinite(remaining_source.source_scalar_0338) ||
        !std::isfinite(remaining_source.source_vec_0918[0]) ||
        !std::isfinite(remaining_source.source_vec_0918[1]) ||
        !std::isfinite(remaining_source.source_vec_0918[2])) {
        throw std::invalid_argument(
            "FUN_007618f0 remaining source fields must be finite");
    }

    Fun007618f0WheelBodyOriginOwnershipResult result{};
    result.fl_wheel_body_index =
        topology.wheel_body_indices[kFun007618f0FlWheelSlot];
    result.fr_wheel_body_index =
        topology.wheel_body_indices[kFun007618f0FrWheelSlot];
    result.fl_wheel_body_origin = fun_007618f0_read_body_origin(
        current_body_bytes,
        result.fl_wheel_body_index,
        "FUN_007618f0 FL wheel BODY origin must be finite");
    result.fr_wheel_body_origin = fun_007618f0_read_body_origin(
        current_body_bytes,
        result.fr_wheel_body_index,
        "FUN_007618f0 FR wheel BODY origin must be finite");
    result.producer_input.hdvehicle_pointer_vec_0820 =
        result.fl_wheel_body_origin;
    result.producer_input.hdvehicle_pointer_vec_12a0 =
        result.fr_wheel_body_origin;
    result.producer_input.source_scalar_0338 =
        remaining_source.source_scalar_0338;
    result.producer_input.source_vec_0918 =
        remaining_source.source_vec_0918;
    return result;
}

}  // namespace shift::runtime::physics
