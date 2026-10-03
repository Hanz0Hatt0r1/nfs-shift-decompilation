#include "shift_body_point_transform.hpp"

#include <cmath>
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

void require_body(const BodyPointTransformState& body) {
    require_finite(body.angular, "BODY angular vector");
    require_finite(body.body_position, "BODY position vector");
    require_finite(body.translation, "BODY translation vector");
}

BodyPointVector3d cross_transform(
    const BodyPointVector3d& angular,
    const BodyPointVector3d& point,
    const BodyPointVector3d& translation) {

    BodyPointVector3d result = {
        point[2] * angular[1] - point[1] * angular[2] + translation[0],
        point[0] * angular[2] - angular[0] * point[2] + translation[1],
        angular[0] * point[1] - point[0] * angular[1] + translation[2],
    };
    require_finite(result, "BODY point transform result");
    return result;
}

}  // namespace

BodyPointVector3d transform_fun_007537b0_body_point(
    const BodyPointTransformState& body,
    const BodyPointVector3d& point) {

    require_body(body);
    require_finite(point, "FUN_007537b0 point");
    return cross_transform(body.angular, point, body.translation);
}

BodyPointVector3d transform_fun_00753810_body_point_relative(
    const BodyPointTransformState& body,
    const BodyPointVector3d& point) {

    require_body(body);
    require_finite(point, "FUN_00753810 point");
    const BodyPointVector3d relative = {
        point[0] - body.body_position[0],
        point[1] - body.body_position[1],
        point[2] - body.body_position[2],
    };
    require_finite(relative, "FUN_00753810 relative point");
    return cross_transform(body.angular, relative, body.translation);
}

}  // namespace shift::runtime::physics
