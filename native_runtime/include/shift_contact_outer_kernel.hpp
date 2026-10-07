#pragma once

#include "shift_surface_probe.hpp"

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
inline constexpr const char* kFun007675f0DistanceFilterCapOwnershipFormat =
    "SHIFT.Fun007675f0DistanceFilterCapOwnership/1";
inline constexpr const char* kFun007675f0SurfaceProbeJoinFormat =
    "SHIFT.Fun007675f0SurfaceProbeJoin/1";
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
inline constexpr std::size_t kFun007675f0Body0PositionXOffset = 0x00u;
inline constexpr std::size_t kFun007675f0Body0PositionYOffset = 0x08u;
inline constexpr std::size_t kFun007675f0Body0PositionZOffset = 0x10u;
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

// Historical/lower-chain payload. Derived planar_delta/surface_scalar stay here
// because lower standalone fixtures predate the source-backed FUN_00759210 join.
// Production session code supplies surface_probe_node instead and resolves both
// derived values from current BODY0 position inside the native pass.
struct ContactOuterExternalInput {
    ContactOuterVector3d planar_delta{};
    double previous_distance_state = 0.0;
    double distance_filter_cap = 0.0;
    double surface_scalar = 0.0;
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    double param_3 = 0.0;
    const SurfaceProbeNode* surface_probe_node = nullptr;

    ContactOuterExternalInput() = default;

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

// Session-facing per-pass payload. PC retail proves planar_delta and
// surface_scalar are outputs of FUN_00759210 queried from current BODY0 position
// and the caller-supplied node pointer. Production therefore carries that node
// pointer instead of the two already-derived values. Compatibility outputs only
// preserve historical fixtures; they are not part of the production frontier.
struct ContactOuterSessionInput {
    const SurfaceProbeNode* surface_probe_node = nullptr;
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    double param_3 = 0.0;
    bool compatibility_surface_probe_outputs_present = false;
    ContactOuterVector3d compatibility_planar_delta{};
    double compatibility_surface_scalar = 0.0;
    bool compatibility_previous_distance_seed_present = false;
    double compatibility_previous_distance_seed = 0.0;
    bool compatibility_distance_filter_cap_seed_present = false;
    double compatibility_distance_filter_cap_seed = 0.0;

    ContactOuterSessionInput() = default;

    ContactOuterSessionInput(const ContactOuterKernelInput& legacy)
        : base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3),
          compatibility_surface_probe_outputs_present(true),
          compatibility_planar_delta(legacy.planar_delta),
          compatibility_surface_scalar(legacy.surface_scalar),
          compatibility_previous_distance_seed_present(true),
          compatibility_previous_distance_seed(legacy.previous_distance_state),
          compatibility_distance_filter_cap_seed_present(true),
          compatibility_distance_filter_cap_seed(legacy.distance_filter_cap) {}

    ContactOuterSessionInput(const ContactOuterExternalInput& legacy)
        : surface_probe_node(legacy.surface_probe_node),
          base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3),
          compatibility_surface_probe_outputs_present(
              legacy.surface_probe_node == nullptr),
          compatibility_planar_delta(legacy.planar_delta),
          compatibility_surface_scalar(legacy.surface_scalar),
          compatibility_previous_distance_seed_present(true),
          compatibility_previous_distance_seed(legacy.previous_distance_state),
          compatibility_distance_filter_cap_seed_present(true),
          compatibility_distance_filter_cap_seed(legacy.distance_filter_cap) {}
};

struct Fun007675f0BodyMotion {
    double speed_x = 0.0;
    double speed_z = 0.0;
};

struct Fun007675f0SurfaceProbeJoinResult {
    SurfaceProbeVector3d body_query_position{};
    SurfaceProbeResult probe{};
    ContactOuterVector3d planar_delta{};
    double surface_scalar = 0.0;
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

SurfaceProbeVector3d derive_fun_007675f0_body0_probe_query_position(
    const std::vector<std::uint8_t>& current_body_bytes);

Fun007675f0SurfaceProbeJoinResult execute_fun_007675f0_surface_probe_join(
    const SurfaceProbeVector3d& body_query_position,
    const SurfaceProbeNode& node);

ContactOuterExternalInput resolve_fun_007675f0_surface_probe_outputs(
    const ContactOuterExternalInput& external,
    const SurfaceProbeVector3d& body_query_position);

ContactOuterExternalInput compose_fun_007675f0_external_input(
    const ContactOuterSessionInput& session_input,
    double previous_distance_state,
    double distance_filter_cap);

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
