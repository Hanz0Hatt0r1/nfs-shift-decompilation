#pragma once

#include "shift_fun_007618f0_local_sample_producer.hpp"
#include "shift_fun_007618f0_selected_bmw_source.hpp"
#include "shift_fun_007618f0_wheel_body_origin_ownership.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun007618f0SelectedBmwPrimaryReferenceSetupFormat =
    "SHIFT.Fun007618f0SelectedBMWPrimaryReferenceSetup/1";

inline constexpr std::size_t kFun007618f0RlWheelPointerOffset = 0x1d20u;
inline constexpr std::size_t kFun007618f0RrWheelPointerOffset = 0x27a0u;
inline constexpr std::size_t kFun007618f0RlWheelSlot = 2u;
inline constexpr std::size_t kFun007618f0RrWheelSlot = 3u;
inline constexpr std::size_t kFun007618f0BodyAeroRecordOffset = 0xca0u;
inline constexpr std::size_t kFun007618f0BodyCenterRelativeOffset = 0x30u;
inline constexpr std::size_t kFun007618f0BodyCenterAbsoluteOffset = 0xcd0u;
inline constexpr std::size_t kFun007618f0PrimaryReferenceOffset = 0x3b08u;

// Retail BMW M3 E36 CDF BODYAERO.BodyCenter=(0.0, 0.50, -1.40).
// FUN_007c27e0 parses the three lanes with FUN_007a6a90's %lf path into
// VehicleLoadData+0xca0+0x30 = +0xcd0/+0xcd8/+0xce0.
inline constexpr std::uint64_t kBmwM3E36BodyCenterXF64Bits =
    0x0000000000000000ull;
inline constexpr std::uint64_t kBmwM3E36BodyCenterYF64Bits =
    0x3fe0000000000000ull;
inline constexpr std::uint64_t kBmwM3E36BodyCenterZF64Bits =
    0xbff6666666666666ull;

struct Fun007618f0SelectedBmwPrimaryReferenceSetupResult {
    std::size_t rl_wheel_body_index = 0u;
    std::size_t rr_wheel_body_index = 0u;
    CollisionQueryVector3d rl_wheel_body_origin{};
    CollisionQueryVector3d rr_wheel_body_origin{};
    CollisionQueryVector3d rear_midpoint{};
    CollisionQueryVector3d local_base{};
    CollisionQueryVector3d body_center{};
    CollisionQueryVector3d primary_reference_3b08{};
};

inline CollisionQueryVector3d selected_bmw_m3_e36_body_aero_center() {
    return {
        fun_007618f0_double_from_bits(kBmwM3E36BodyCenterXF64Bits),
        fun_007618f0_double_from_bits(kBmwM3E36BodyCenterYF64Bits),
        fun_007618f0_double_from_bits(kBmwM3E36BodyCenterZF64Bits),
    };
}

// This is a setup-time producer. `setup_body_bytes` must represent the selected
// BMW persistent BODY domain at the same setup boundary as retail FUN_007618f0;
// callers must not silently recompute this setup value from later pass state.
inline Fun007618f0SelectedBmwPrimaryReferenceSetupResult
execute_fun_007618f0_selected_bmw_primary_reference_setup(
    const std::vector<std::uint8_t>& setup_body_bytes) {
    const auto& topology = bmw_m3_e36_retail_wheel_spindle_body_topology();
    if (!topology.wheel_spindle_body_indices_ready ||
        topology.body_count != kBmwM3E36RetailBodyCount ||
        setup_body_bytes.size() != topology.body_count * kBodyRecordSize) {
        throw std::invalid_argument(
            "FUN_007618f0 primary-reference setup requires selected BMW 11-BODY setup state");
    }

    Fun007618f0SelectedBmwPrimaryReferenceSetupResult result{};
    result.rl_wheel_body_index = topology.wheel_body_indices[kFun007618f0RlWheelSlot];
    result.rr_wheel_body_index = topology.wheel_body_indices[kFun007618f0RrWheelSlot];
    result.rl_wheel_body_origin = fun_007618f0_read_body_origin(
        setup_body_bytes,
        result.rl_wheel_body_index,
        "FUN_007618f0 RL wheel BODY setup origin must be finite");
    result.rr_wheel_body_origin = fun_007618f0_read_body_origin(
        setup_body_bytes,
        result.rr_wheel_body_index,
        "FUN_007618f0 RR wheel BODY setup origin must be finite");
    result.body_center = selected_bmw_m3_e36_body_aero_center();

    const auto selected_source = selected_bmw_m3_e36_fun_007618f0_source();
    Fun007618f0LocalSampleProducerInput producer{};
    producer.hdvehicle_pointer_vec_0820 = result.rl_wheel_body_origin;
    producer.hdvehicle_pointer_vec_12a0 = result.rr_wheel_body_origin;
    producer.source_scalar_0338 = selected_source.source_scalar_0338;
    producer.source_vec_0918 = result.body_center;

    // FUN_007618f0 uses the same add/0.5/Y-replacement/add primitive shape as
    // Phase728, with RL/RR and BODYAERO.BodyCenter as the concrete inputs here.
    const auto composed = execute_fun_007618f0_local_sample_producer(producer);
    result.rear_midpoint = composed.pointer_midpoint;
    result.local_base = composed.local_base;
    result.primary_reference_3b08 = composed.local_sample_3938;
    return result;
}

}  // namespace shift::runtime::physics
