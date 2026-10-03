#pragma once

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelKinematicsFormat =
    "SHIFT.NativeWheelKinematics/1";
inline constexpr const char* kWheelKinematicsFunction = "FUN_00758b50";
inline constexpr const char* kWheelKinematicsCallerFunction = "FUN_0076d100";
inline constexpr const char* kWheelKinematicsPreHelperFunction = "FUN_00755950";
inline constexpr const char* kWheelKinematicsSpringHelperFunction = "FUN_007555b0";

inline constexpr std::size_t kWheelKinematicsCount = 4u;
inline constexpr std::size_t kWheelKinematicsStateBase = 0x848u;
inline constexpr std::size_t kWheelKinematicsStateStride = 0xa80u;
inline constexpr std::size_t kWheelKinematicsRuntimeBase = 0x400u;
inline constexpr std::size_t kWheelKinematicsRuntimeStride = 0xa80u;
inline constexpr std::size_t kWheelKinematicsSkipFlagOffset = 0xf8u;
inline constexpr std::size_t kWheelKinematicsFinalFlagOffset = 0x11cu;
inline constexpr std::size_t kWheelKinematicsDistanceReferenceOffset = 0x138u;
inline constexpr std::size_t kWheelKinematicsDistanceErrorOffset = 0x128u;
inline constexpr std::size_t kWheelKinematicsProjectionOffset = 0x130u;
inline constexpr std::size_t kWheelKinematicsHelperOutputOffset = 0x148u;

inline constexpr std::size_t kWheelKinematicsFrontScaleOffset = 0x2e20u;
inline constexpr std::size_t kWheelKinematicsRearScaleOffset = 0x2e28u;
inline constexpr std::array<std::size_t, 4> kWheelKinematicsFrontDeltaSources = {
    0x928u, 0x938u, 0x13a8u, 0x13b8u};
inline constexpr std::array<std::size_t, 2> kWheelKinematicsFrontDestinations = {
    0x948u, 0x13c8u};
inline constexpr std::array<std::size_t, 4> kWheelKinematicsRearDeltaSources = {
    0x1e28u, 0x1e38u, 0x28a8u, 0x28b8u};
inline constexpr std::array<std::size_t, 2> kWheelKinematicsRearDestinations = {
    0x1e48u, 0x28c8u};

using WheelKinematicsVector3d = std::array<double, 3>;

struct WheelKinematicSlotInput {
    bool skip_flag_nonzero = false;
    WheelKinematicsVector3d relative_vector{};
    double reference_length = 0.0;
    double projection_input = 0.0;
};

struct WheelKinematicObservation {
    std::size_t wheel_index = 0u;
    std::size_t wheel_state_offset = kWheelKinematicsStateBase;
    std::size_t wheel_runtime_offset = kWheelKinematicsRuntimeBase;
    WheelKinematicsVector3d relative_vector{};
    double relative_length = 0.0;
    WheelKinematicsVector3d relative_unit{};
    double reference_length = 0.0;
    double distance_error = 0.0;
    double projection_input = 0.0;
    double stored_projection_value = 0.0;
};

struct WheelKinematicsBatchResult {
    std::array<bool, kWheelKinematicsCount> processed{};
    std::array<WheelKinematicObservation, kWheelKinematicsCount> observations{};
    std::size_t processed_count = 0u;
};

struct WheelKinematicsPairInput {
    double source_a_left = 0.0;
    double source_b_left = 0.0;
    double source_a_right = 0.0;
    double source_b_right = 0.0;
    double scale = 0.0;
    double left_destination_before = 0.0;
    double right_destination_before = 0.0;
};

struct WheelKinematicsPairResult {
    double delta = 0.0;
    double left_destination_after = 0.0;
    double right_destination_after = 0.0;
};

WheelKinematicObservation prepare_fun_00758b50_wheel_kinematics(
    std::size_t wheel_index,
    const WheelKinematicSlotInput& input);

WheelKinematicsBatchResult execute_fun_00758b50_prehelper_batch(
    const std::array<WheelKinematicSlotInput, kWheelKinematicsCount>& inputs);

WheelKinematicsPairResult apply_fun_00758b50_pair_delta(
    const WheelKinematicsPairInput& input);

bool fun_00758b50_final_transform_eligible(
    bool input_pointer_present,
    bool block_flag_0x11c_nonzero);

}  // namespace shift::runtime::physics
