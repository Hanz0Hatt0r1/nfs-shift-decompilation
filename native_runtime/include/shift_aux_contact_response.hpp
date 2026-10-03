#pragma once

#include "shift_body_accumulator_primitives.hpp"
#include "shift_body_point_transform.hpp"
#include "shift_constraint_sample_refresh.hpp"
#include "shift_wheel_contact_response.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kNativeAuxContactResponseFormat =
    "SHIFT.NativeAuxContactResponse/1";
inline constexpr const char* kAuxContactResponseFunction = "FUN_00758fc0";

struct AuxContactRecord {
    bool active = false;
    ConstraintRefreshVector3d point{};
    WheelContactCurveParameters directional_curve{};
    double gain = 0.0;
    double scale = 0.0;
};

struct AuxContactResponseInput {
    ConstraintRefreshFrame3f body_frame{};
    BodyPointTransformState body_transform{};
    BodyAccumulatorState body_accumulator{};
    ConstraintRefreshVector3d reference_point{};
    AuxContactRecord record{};
};

struct AuxContactResponseResult {
    bool applied = false;
    ConstraintRefreshVector3d transformed_record_point{};
    BodyPointVector3d body_point_output{};
    ConstraintRefreshVector3d local_point{};
    ConstraintRefreshVector3d relative_point{};
    double square_negative_z = 0.0;
    double directional_multiplier = 0.0;
    ConstraintRefreshVector3d local_response{};
    ConstraintRefreshVector3d transformed_response{};
    BodyAccumulatorState body_accumulator{};
};

AuxContactResponseResult execute_fun_00758fc0_aux_contact_response(
    const AuxContactResponseInput& input);

}  // namespace shift::runtime::physics
