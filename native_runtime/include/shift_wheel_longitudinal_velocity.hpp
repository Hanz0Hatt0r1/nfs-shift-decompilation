#pragma once

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelLongitudinalVelocityFormat =
    "SHIFT.NativeWheelLongitudinalVelocity/1";
inline constexpr const char* kWheelLongitudinalFunction = "FUN_00755f80";
inline constexpr const char* kWheelLongitudinalCallerFunction = "FUN_00763570";
inline constexpr std::size_t kWheelLongitudinalBaseOffset = 0x400u;
inline constexpr std::size_t kWheelLongitudinalStride = 0xa80u;
inline constexpr std::size_t kWheelLongitudinalCount = 4u;
inline constexpr std::size_t kWheelLongitudinalVelocityOffset = 0x48u;
inline constexpr std::size_t kWheelLongitudinalPoseOffset = 0xd4u;
inline constexpr std::size_t kWheelLongitudinalPairAverageFlagOffset = 0x3ee0u;
inline constexpr std::size_t kWheelLongitudinalPairAverageModeOffset = 0x3eb8u;

using WheelLongitudinalVector3d = std::array<double, 3>;

struct WheelLongitudinalInput {
    std::size_t wheel_index = 0u;
    WheelLongitudinalVector3d shared_velocity{};
    WheelLongitudinalVector3d local_velocity{};
    WheelLongitudinalVector3d reconstructed_world_velocity{};
};

struct WheelLongitudinalObservation {
    std::size_t wheel_index = 0u;
    std::size_t wheel_object_offset = kWheelLongitudinalBaseOffset;
    WheelLongitudinalVector3d input_velocity{};
    WheelLongitudinalVector3d local_velocity{};
    double longitudinal_component = 0.0;
    WheelLongitudinalVector3d reconstructed_world_velocity{};
    WheelLongitudinalVector3d shared_velocity_after{};
};

struct WheelLongitudinalBatchResult {
    std::array<WheelLongitudinalObservation, kWheelLongitudinalCount> observations{};
    std::array<double, kWheelLongitudinalCount> reported_components{};
};

WheelLongitudinalVector3d apply_fun_00755f80_reconstructed_subtraction(
    const WheelLongitudinalVector3d& shared_velocity,
    const WheelLongitudinalVector3d& reconstructed_world_velocity);

WheelLongitudinalObservation execute_fun_00755f80_precomputed_handoff(
    const WheelLongitudinalInput& input);

WheelLongitudinalBatchResult execute_fun_00763570_precomputed_batch(
    const std::array<WheelLongitudinalInput, kWheelLongitudinalCount>& inputs,
    bool rear_pair_average_enabled,
    int mode,
    bool global_config_byte);

}  // namespace shift::runtime::physics
