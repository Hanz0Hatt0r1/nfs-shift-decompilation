#include "shift_contact_outer_kernel.hpp"

#include "shift_body_record_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument(
            "FUN_007675f0 BODY0 read exceeds BODY buffer");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

double read_f64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    const char* label) {
    const std::uint64_t bits = read_u64_le(bytes, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    require_finite_value(value, label);
    return value;
}

double spill_f64_to_f32(double value, const char* label) {
    require_finite_value(value, label);
    const float spilled = static_cast<float>(value);
    if (!std::isfinite(spilled)) {
        throw std::invalid_argument(std::string(label) + " f32 spill is non-finite");
    }
    return static_cast<double>(spilled);
}

double planar_length_xz(const ContactOuterVector3d& vector) {
    const double length = std::sqrt(
        vector[0] * vector[0] + vector[2] * vector[2]);
    require_finite_value(length, "FUN_007675f0 planar distance");
    return length;
}

ContactOuterVector3d normalize_planar_xz(
    const ContactOuterVector3d& vector,
    double length) {

    if (length == 0.0) {
        throw std::invalid_argument(
            "FUN_007675f0 cannot normalize a zero X/Z delta");
    }
    const double inverse = 1.0 / length;
    ContactOuterVector3d result = {
        vector[0] * inverse,
        0.0,
        vector[2] * inverse,
    };
    require_finite(result, "FUN_007675f0 planar direction");
    return result;
}

double clamp_01(double value) {
    return std::min(1.0, std::max(0.0, value));
}

}  // namespace

Fun007675f0BodyProbeState derive_fun_007675f0_body0_probe_state(
    const std::vector<std::uint8_t>& current_body_bytes) {
    if (current_body_bytes.empty() ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007675f0 BODY state requires exact 0x170-byte BODY records");
    }

    Fun007675f0BodyProbeState state{};
    // PC FUN_007675f0 spills BODY0's f64 origin to three f32 locals before
    // passing that point as ECX to FUN_00759210. Preserve that rounding boundary.
    state.query_point = {
        spill_f64_to_f32(
            read_f64_le(
                current_body_bytes,
                kFun007675f0Body0PositionXOffset,
                "FUN_007675f0 BODY0 position X"),
            "FUN_007675f0 BODY0 position X"),
        spill_f64_to_f32(
            read_f64_le(
                current_body_bytes,
                kFun007675f0Body0PositionYOffset,
                "FUN_007675f0 BODY0 position Y"),
            "FUN_007675f0 BODY0 position Y"),
        spill_f64_to_f32(
            read_f64_le(
                current_body_bytes,
                kFun007675f0Body0PositionZOffset,
                "FUN_007675f0 BODY0 position Z"),
            "FUN_007675f0 BODY0 position Z"),
    };
    state.motion.speed_x = read_f64_le(
        current_body_bytes,
        kFun007675f0Body0SpeedXOffset,
        "FUN_007675f0 BODY0 speed X");
    state.motion.speed_z = read_f64_le(
        current_body_bytes,
        kFun007675f0Body0SpeedZOffset,
        "FUN_007675f0 BODY0 speed Z");
    return state;
}

Fun007675f0BodyMotion derive_fun_007675f0_body0_motion(
    const std::vector<std::uint8_t>& current_body_bytes) {
    return derive_fun_007675f0_body0_probe_state(current_body_bytes).motion;
}

ContactOuterExternalInput compose_fun_007675f0_external_input(
    const ContactOuterSessionInput& session_input,
    double previous_distance_state,
    double distance_filter_cap) {
    require_finite_value(
        previous_distance_state,
        "FUN_007675f0 previous distance state");
    require_finite_value(
        distance_filter_cap,
        "FUN_007675f0 distance filter cap setup state");

    ContactOuterExternalInput external{};
    external.previous_distance_state = previous_distance_state;
    external.distance_filter_cap = distance_filter_cap;
    external.base_scalar = session_input.base_scalar;
    external.projected_scalar = session_input.projected_scalar;
    external.alignment_scalar = session_input.alignment_scalar;
    external.param_3 = session_input.param_3;
    external.surface_probe_node = session_input.surface_probe_node;

    if (session_input.compatibility_planar_surface_present) {
        external.planar_delta = session_input.compatibility_planar_delta;
        external.surface_scalar = session_input.compatibility_surface_scalar;
    }
    return external;
}

ContactOuterExternalInput resolve_fun_007675f0_surface_probe_input(
    const ContactOuterExternalInput& external,
    const Fun007675f0BodyProbeState& body_state) {
    require_finite(body_state.query_point, "FUN_007675f0 BODY0 probe point");
    require_finite_value(body_state.motion.speed_x, "FUN_007675f0 BODY0 speed X");
    require_finite_value(body_state.motion.speed_z, "FUN_007675f0 BODY0 speed Z");

    if (external.surface_probe_node == nullptr) {
        // Historical lower-chain path: planar_delta/surface_scalar were already
        // materialized by the caller before Phase 732.
        require_finite(external.planar_delta, "FUN_007675f0 historical planar delta");
        require_finite_value(
            external.surface_scalar,
            "FUN_007675f0 historical surface scalar");
        return external;
    }

    const auto probe = execute_fun_00759210_surface_probe(
        body_state.query_point,
        *external.surface_probe_node);

    ContactOuterExternalInput resolved = external;
    // PC FUN_00759210 writes f32 outputs, then FUN_007675f0 subtracts the f32
    // BODY query point through the exact vector-subtract helper at 0x004a7870.
    const float query_x = static_cast<float>(body_state.query_point[0]);
    const float query_y = static_cast<float>(body_state.query_point[1]);
    const float query_z = static_cast<float>(body_state.query_point[2]);
    const float probe_x = static_cast<float>(probe.point[0]);
    const float probe_y = static_cast<float>(probe.point[1]);
    const float probe_z = static_cast<float>(probe.point[2]);
    resolved.planar_delta = {
        static_cast<double>(static_cast<float>(probe_x - query_x)),
        static_cast<double>(static_cast<float>(probe_y - query_y)),
        static_cast<double>(static_cast<float>(probe_z - query_z)),
    };
    resolved.surface_scalar =
        static_cast<double>(static_cast<float>(probe.scalar));
    require_finite(resolved.planar_delta, "FUN_007675f0 surface-probe planar delta");
    require_finite_value(
        resolved.surface_scalar,
        "FUN_007675f0 surface-probe scalar");
    return resolved;
}

ContactOuterKernelInput compose_fun_007675f0_input(
    const ContactOuterExternalInput& external,
    const Fun007675f0BodyMotion& motion) {
    require_finite_value(motion.speed_x, "FUN_007675f0 BODY0 speed X");
    require_finite_value(motion.speed_z, "FUN_007675f0 BODY0 speed Z");

    ContactOuterKernelInput input{};
    input.planar_delta = external.planar_delta;
    input.previous_distance_state = external.previous_distance_state;
    input.distance_filter_cap = external.distance_filter_cap;
    input.speed_x = motion.speed_x;
    input.speed_z = motion.speed_z;
    input.surface_scalar = external.surface_scalar;
    input.base_scalar = external.base_scalar;
    input.projected_scalar = external.projected_scalar;
    input.alignment_scalar = external.alignment_scalar;
    input.param_3 = external.param_3;
    return input;
}

double execute_fun_00783a30_distance_filter(
    double previous,
    double distance,
    double cap,
    double response) {

    require_finite_value(previous, "FUN_00783a30 previous");
    require_finite_value(distance, "FUN_00783a30 distance");
    require_finite_value(cap, "FUN_00783a30 cap");
    require_finite_value(response, "FUN_00783a30 response");

    const double denominator = cap + response;
    if (denominator == 0.0) {
        throw std::invalid_argument(
            "FUN_00783a30 cap + response must be non-zero");
    }

    const double result =
        (distance - previous) * (response / denominator) + previous;
    require_finite_value(result, "FUN_00783a30 result");
    return result;
}

ContactOuterKernelResult execute_fun_007675f0_outer_arithmetic(
    const ContactOuterKernelInput& input) {

    require_finite(input.planar_delta, "FUN_007675f0 planar delta");
    require_finite_value(
        input.previous_distance_state,
        "FUN_007675f0 previous distance state");
    require_finite_value(
        input.distance_filter_cap,
        "FUN_007675f0 distance filter cap");
    require_finite_value(input.speed_x, "FUN_007675f0 speed X");
    require_finite_value(input.speed_z, "FUN_007675f0 speed Z");
    require_finite_value(input.surface_scalar, "FUN_007675f0 surface scalar");
    require_finite_value(input.base_scalar, "FUN_007675f0 base scalar");
    require_finite_value(
        input.projected_scalar,
        "FUN_007675f0 projected scalar");
    require_finite_value(
        input.alignment_scalar,
        "FUN_007675f0 alignment scalar");
    require_finite_value(input.param_3, "FUN_007675f0 param_3");

    ContactOuterKernelResult result{};
    result.distance = planar_length_xz(input.planar_delta);
    result.planar_direction =
        normalize_planar_xz(input.planar_delta, result.distance);

    if (result.distance <= kContactDistanceLimit) {
        result.filtered_distance_state =
            execute_fun_00783a30_distance_filter(
                input.previous_distance_state,
                result.distance,
                input.distance_filter_cap,
                kContactDistanceFilterResponse);
    } else {
        result.filtered_distance_state = kContactDistanceLimit;
    }

    result.speed = std::sqrt(
        input.speed_x * input.speed_x +
        input.speed_z * input.speed_z);
    require_finite_value(result.speed, "FUN_007675f0 speed");
    result.speed_factor = clamp_01(
        (result.speed - kContactSpeedFactorOffset) /
        kContactSpeedFactorScale);

    result.gate_open =
        result.distance < kContactDistanceLimit &&
        result.distance > kContactDistanceGateMinimum &&
        result.speed > kContactSpeedGateMinimum;

    // Direct PC machine code at 0x00767937..0x00767949 reloads the value
    // committed to HDVehicle+0x4080, not the raw planar distance, before forming
    // the gap against FUN_00759210's returned scalar.
    result.gap =
        result.filtered_distance_state -
        (input.surface_scalar - kContactGapOffset);
    if (result.gap <= 0.0) {
        result.gap_shape = 0.0;
    } else if (result.gap >= kContactGapScale) {
        result.gap_shape = 1.0;
    } else {
        result.gap_shape = result.gap / kContactGapScale;
    }

    result.force_scalar =
        (input.base_scalar * kContactForceMultiplier -
         input.projected_scalar) *
        (2.0 - result.gap_shape) *
        result.gap_shape *
        input.alignment_scalar *
        result.speed_factor;
    require_finite_value(result.force_scalar, "FUN_007675f0 force scalar");

    result.first_submission_scale =
        result.force_scalar * input.param_3;
    result.second_submission_scale =
        result.first_submission_scale * kContactNegativeSubmissionScale;
    require_finite_value(
        result.first_submission_scale,
        "FUN_007675f0 first submission scale");
    require_finite_value(
        result.second_submission_scale,
        "FUN_007675f0 second submission scale");

    return result;
}

}  // namespace shift::runtime::physics
