#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_surface_probe.hpp"
#include "shift_wheel_force_aggregate.hpp"

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
inline constexpr const char* kFun007675f0Param3OwnershipFormat =
    "SHIFT.Fun007675f0Param3Ownership/1";
inline constexpr const char* kFun007675f0BodyOwnedScalarOwnershipFormat =
    "SHIFT.Fun007675f0BodyOwnedScalarOwnership/1";
inline constexpr const char* kFun007675f0ProjectedScalarOwnershipFormat =
    "SHIFT.Fun007675f0ProjectedScalarOwnership/1";
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
using Fun00759c90RecordSet =
    std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>;

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
    double body_field_120 = 0.0;
    Fun00759c90RecordSet fun_00759c90_records{};
    bool derive_projected_scalar = false;
    bool derive_body_owned_scalars = false;
};

// Historical/lower-chain payload. Derived probe outputs, projected/base/alignment
// scalar intermediates, and final param_3 remain representable because standalone
// fixtures predate the source-backed caller joins. Production session code supplies
// the earlier FUN_00759c90 record boundary instead of an already-projected scalar.
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
    Fun00759c90RecordSet fun_00759c90_records{};
    bool compatibility_projected_scalar_present = false;
    Fun00765c40LoadTerms fun_00769ef0_param_3_load_terms{};
    bool fun_00769ef0_param_3_load_terms_present = false;
    double fun_007675f0_body_field_120 = 0.0;
    bool fun_007675f0_body_field_120_present = false;
    bool compatibility_body_owned_scalars_present = false;

    ContactOuterExternalInput() = default;

    ContactOuterExternalInput(const ContactOuterKernelInput& legacy)
        : planar_delta(legacy.planar_delta),
          previous_distance_state(legacy.previous_distance_state),
          distance_filter_cap(legacy.distance_filter_cap),
          surface_scalar(legacy.surface_scalar),
          base_scalar(legacy.base_scalar),
          projected_scalar(legacy.projected_scalar),
          alignment_scalar(legacy.alignment_scalar),
          param_3(legacy.param_3),
          fun_00759c90_records(legacy.fun_00759c90_records),
          compatibility_projected_scalar_present(!legacy.derive_projected_scalar),
          compatibility_body_owned_scalars_present(true) {}
};

// Session-facing per-pass payload. Production now carries the exact three-record
// FUN_00759c90 source boundary rather than projected_scalar. The projection is
// derived inside FUN_007675f0 from the aggregate's first output X/Z and the
// probe-derived planar direction. Compatibility fields preserve historical fixtures.
struct ContactOuterSessionInput {
    const SurfaceProbeNode* surface_probe_node = nullptr;
    Fun00759c90RecordSet fun_00759c90_records{};
    bool compatibility_projected_scalar_present = false;
    double compatibility_projected_scalar = 0.0;
    bool compatibility_surface_probe_outputs_present = false;
    ContactOuterVector3d compatibility_planar_delta{};
    double compatibility_surface_scalar = 0.0;
    bool compatibility_body_owned_scalars_present = false;
    double compatibility_base_scalar = 0.0;
    double compatibility_alignment_scalar = 0.0;
    bool compatibility_param_3_present = false;
    double compatibility_param_3 = 0.0;
    bool compatibility_previous_distance_seed_present = false;
    double compatibility_previous_distance_seed = 0.0;
    bool compatibility_distance_filter_cap_seed_present = false;
    double compatibility_distance_filter_cap_seed = 0.0;

    ContactOuterSessionInput() = default;

    ContactOuterSessionInput(const ContactOuterKernelInput& legacy)
        : fun_00759c90_records(legacy.fun_00759c90_records),
          compatibility_projected_scalar_present(!legacy.derive_projected_scalar),
          compatibility_projected_scalar(legacy.projected_scalar),
          compatibility_surface_probe_outputs_present(true),
          compatibility_planar_delta(legacy.planar_delta),
          compatibility_surface_scalar(legacy.surface_scalar),
          compatibility_body_owned_scalars_present(true),
          compatibility_base_scalar(legacy.base_scalar),
          compatibility_alignment_scalar(legacy.alignment_scalar),
          compatibility_param_3_present(true),
          compatibility_param_3(legacy.param_3),
          compatibility_previous_distance_seed_present(true),
          compatibility_previous_distance_seed(legacy.previous_distance_state),
          compatibility_distance_filter_cap_seed_present(true),
          compatibility_distance_filter_cap_seed(legacy.distance_filter_cap) {}

    ContactOuterSessionInput(const ContactOuterExternalInput& legacy)
        : surface_probe_node(legacy.surface_probe_node),
          fun_00759c90_records(legacy.fun_00759c90_records),
          compatibility_projected_scalar_present(
              legacy.compatibility_projected_scalar_present),
          compatibility_projected_scalar(legacy.projected_scalar),
          compatibility_surface_probe_outputs_present(
              legacy.surface_probe_node == nullptr),
          compatibility_planar_delta(legacy.planar_delta),
          compatibility_surface_scalar(legacy.surface_scalar),
          compatibility_body_owned_scalars_present(true),
          compatibility_base_scalar(legacy.base_scalar),
          compatibility_alignment_scalar(legacy.alignment_scalar),
          compatibility_param_3_present(
              !legacy.fun_00769ef0_param_3_load_terms_present),
          compatibility_param_3(legacy.param_3),
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
    double base_scalar = 0.0;
    double projected_scalar = 0.0;
    double alignment_scalar = 0.0;
    bool projected_scalar_derived = false;
    bool body_owned_scalars_derived = false;
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

double execute_fun_007675f0_projected_scalar(
    const Fun00759c90RecordSet& records,
    const ContactOuterVector3d& planar_delta);

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
