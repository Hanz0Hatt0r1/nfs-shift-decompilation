#pragma once

#include <array>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeContactOuterKernelFormat =
    "SHIFT.NativeContactOuterKernel/1";
inline constexpr const char* kFun007675f0BodyMotionOwnershipFormat =
    "SHIFT.Fun007675f0BodyMotionOwnership/1";
inline constexpr const char* kFun007675f0DistanceStateOwnershipFormat =
    "SHIFT.Fun007675f0DistanceStateOwnership/1";
inline constexpr const char* kContactOuterKernelFunction = "FUN_007675f0";
inline constexpr const char* kContactDistanceFilterFunction = "FUN_00783a30";

inline constexpr double kContactDistanceLimit = 200.0;
inline constexpr double kContactDistanceGateMinimum = 5.0;
inline constexpr double kContactSpeedGateMinimum = 1.0;
inline constexpr double kContactSpeedFactorOffset = 13.888889;
inline constexpr double kContactSpeedFactorScale = 5.5555553;
inline constexpr double kContactGapOffset = 1.5;
inline constexpr double kContactGapScale = 2.5;
inline constexpr double kContactForceMultiplier = 1.5;
inline constexpr double kContactNegativeSubmissionScale = -0.05;
inline constexpr double kContactDistanceFilterResponse = 0.5;
inline constexpr std::size_t kFun007675f0Body0SpeedXOffset = 0x78u;
inline constexpr std::size_t kFun007675f0Body0SpeedZOffset = 0x88u;

using ContactOuterVector3d = std::array<double, 3>;

struct ContactOuterKernelInput {
    ContactOuterVector3d planar_delta{};
    double previous_distance_state = 0.0;
    double distance_filter_cap = 0.0;
    double speed_x = 0.0;
    double speed_z = 0.0;
    double surface_scalar = 0.0;
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    double param_3 = 0.0;
};

// Historical/lower-chain external payload. BODY0 motion is already absent, but
// previous_distance_state is retained here because lower standalone Phase 693
// fixtures predate the session-owned HDVehicle+0x4080 state. Production session
// code resolves this field from its persistent state before entering the chain.
struct ContactOuterExternalInput {
    ContactOuterVector3d planar_delta{};
    double previous_distance_state = 0.0;
    double distance_filter_cap = 0.0;
    double surface_scalar = 0.0;
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    double param_3 = 0.0;

    ContactOuterExternalInput() = default;

    // Compatibility conversion for older fixtures. Legacy speed fields are
    // intentionally ignored because production reads current BODY0 motion.
    ContactOuterExternalInput(const ContactOuterKernelInput& legacy)
        : planar_delta(legacy.planar_delta),
          previous_distance_state(legacy.previous_distance_state),
          distance_filter_cap(legacy.distance_filter_cap),
          surface_scalar(legacy.surface_scalar),
          base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3) {}
};

// Session-facing per-pass payload. Both BODY motion and HDVehicle+0x4080 are
// absent from the production fields: the session owns those persistent values.
// The compatibility seed exists only so historical fixtures that return the old
// complete input can initialize the one-time state without being rewritten.
struct ContactOuterSessionInput {
    ContactOuterVector3d planar_delta{};
    double distance_filter_cap = 0.0;
    double surface_scalar = 0.0;
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    double param_3 = 0.0;
    bool compatibility_previous_distance_seed_present = false;
    double compatibility_previous_distance_seed = 0.0;

    ContactOuterSessionInput() = default;

    ContactOuterSessionInput(const ContactOuterKernelInput& legacy)
        : planar_delta(legacy.planar_delta),
          distance_filter_cap(legacy.distance_filter_cap),
          surface_scalar(legacy.surface_scalar),
          base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3),
          compatibility_previous_distance_seed_present(true),
          compatibility_previous_distance_seed(legacy.previous_distance_state) {}

    ContactOuterSessionInput(const ContactOuterExternalInput& legacy)
        : planar_delta(legacy.planar_delta),
          distance_filter_cap(legacy.distance_filter_cap),
          surface_scalar(legacy.surface_scalar),
          base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3),
          compatibility_previous_distance_seed_present(true),
          compatibility_previous_distance_seed(legacy.previous_distance_state) {}
};

struct Fun007675f0BodyMotion {
    double speed_x = 0.0;
    double speed_z = 0.0;
};

struct ContactOuterKernelResult {
    double distance = 0.0;
    ContactOuterVector3d planar_direction{};
    double filtered_distance_state = 0.0;
    double speed = 0.0;
    double speed_factor = 0.0;
    bool gate_open = false;
    double gap = 0.0;
    double gap_shape = 0.0;
    double force_scalar = 0.0;
    double first_submission_scale = 0.0;
    double second_submission_scale = 0.0;
};

Fun007675f0BodyMotion derive_fun_007675f0_body0_motion(
    const std::vector<std::uint8_t>& current_body_bytes);

ContactOuterExternalInput compose_fun_007675f0_external_input(
    const ContactOuterSessionInput& session_input,
    double previous_distance_state);

ContactOuterKernelInput compose_fun_007675f0_input(
    const ContactOuterExternalInput& external,
    const Fun007675f0BodyMotion& motion);

double execute_fun_00783a30_distance_filter(
    double previous,
    double distance,
    double cap,
    double response = kContactDistanceFilterResponse);

ContactOuterKernelResult execute_fun_007675f0_outer_arithmetic(
    const ContactOuterKernelInput& input);

}  // namespace shift::runtime::physics
