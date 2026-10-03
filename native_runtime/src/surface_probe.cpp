#include "shift_surface_probe.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

constexpr float kNormalizeThreshold = 0.01f;

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

SurfaceProbeVector3d subtract(
    const SurfaceProbeVector3d& left,
    const SurfaceProbeVector3d& right) {

    return {
        left[0] - right[0],
        left[1] - right[1],
        left[2] - right[2],
    };
}

SurfaceProbeVector3d add(
    const SurfaceProbeVector3d& left,
    const SurfaceProbeVector3d& right) {

    return {
        left[0] + right[0],
        left[1] + right[1],
        left[2] + right[2],
    };
}

SurfaceProbeVector3d scale(
    const SurfaceProbeVector3d& vector,
    double scalar) {

    return {
        vector[0] * scalar,
        vector[1] * scalar,
        vector[2] * scalar,
    };
}

double dot(
    const SurfaceProbeVector3d& left,
    const SurfaceProbeVector3d& right) {

    return
        left[0] * right[0] +
        left[1] * right[1] +
        left[2] * right[2];
}

int sign(double value) {
    if (value > 0.0) {
        return 1;
    }
    if (value < 0.0) {
        return -1;
    }
    return 0;
}

void require_node(const SurfaceProbeNode& node) {
    require_finite(node.point, "FUN_00759210 node point");
    require_finite(node.normal, "FUN_00759210 node normal");
    require_finite_value(node.distance, "FUN_00759210 node distance");
    require_finite_value(node.radius, "FUN_00759210 node radius");
}

}  // namespace

HorizontalPerpendicularResult execute_fun_007ade70_horizontal_perpendicular(
    const SurfaceProbeVector3d& source_direction) {

    require_finite(source_direction, "FUN_007ade70 source direction");

    const float sx = static_cast<float>(source_direction[0]);
    const float sy = static_cast<float>(source_direction[1]);
    const float sz = static_cast<float>(source_direction[2]);
    (void)sy;

    const float cx = static_cast<float>(sz);
    const float cy = 0.0f;
    const float cz = static_cast<float>(-sx);
    const float length_sq = static_cast<float>(
        static_cast<double>(cx) * static_cast<double>(cx) +
        static_cast<double>(cy) * static_cast<double>(cy) +
        static_cast<double>(cz) * static_cast<double>(cz));
    const float length = static_cast<float>(
        std::sqrt(static_cast<double>(length_sq)));

    HorizontalPerpendicularResult result{};
    result.cross = {
        static_cast<double>(cx),
        static_cast<double>(cy),
        static_cast<double>(cz),
    };
    result.length = static_cast<double>(length);

    if (kNormalizeThreshold < length) {
        const float inverse = static_cast<float>(
            1.0 / static_cast<double>(length));
        const float rx = static_cast<float>(
            static_cast<double>(cx) * static_cast<double>(inverse));
        const float ry = static_cast<float>(
            static_cast<double>(cy) * static_cast<double>(inverse));
        const float rz = static_cast<float>(
            static_cast<double>(cz) * static_cast<double>(inverse));
        result.direction = {
            static_cast<double>(rx),
            static_cast<double>(ry),
            static_cast<double>(rz),
        };
        result.normalized = true;
    } else {
        result.direction = {1.0, 0.0, 0.0};
        result.normalized = false;
    }
    return result;
}

SurfaceProbeResult execute_fun_00759210_surface_probe(
    const SurfaceProbeVector3d& point,
    const SurfaceProbeNode& node) {

    require_finite(point, "FUN_00759210 query point");
    require_node(node);

    const auto relative = subtract(point, node.point);
    const double projection = dot(relative, node.normal);
    require_finite_value(projection, "FUN_00759210 projection");

    if (projection < 0.0 && node.parent != nullptr) {
        auto parent_result =
            execute_fun_00759210_surface_probe(point, *node.parent);
        parent_result.used_parent = true;
        return parent_result;
    }

    const auto direction =
        execute_fun_007ade70_horizontal_perpendicular(node.normal).direction;
    const auto candidate = add(node.point, scale(direction, node.radius));
    const auto point_delta = subtract(point, candidate);
    const double denominator = std::abs(dot(relative, point_delta));
    require_finite_value(denominator, "FUN_00759210 denominator");

    if (denominator == 0.0 || node.radius == 0.0 || node.distance == 0.0) {
        throw std::invalid_argument(
            "FUN_00759210 denominator/radius/distance path is zero");
    }

    double blend =
        (projection / denominator) /
        (node.distance / std::abs(node.radius));
    require_finite_value(blend, "FUN_00759210 blend");
    blend = std::min(1.0, std::max(0.0, blend));

    if (node.child != nullptr) {
        require_node(*node.child);
        if (sign(node.child->radius) == sign(node.radius)) {
            const auto child_direction =
                execute_fun_007ade70_horizontal_perpendicular(
                    node.child->normal).direction;
            const auto child_candidate =
                add(
                    node.child->point,
                    scale(child_direction, node.child->radius));
            SurfaceProbeResult result{};
            result.point = add(
                scale(candidate, 1.0 - blend),
                scale(child_candidate, blend));
            result.scalar = std::abs(
                node.radius * (1.0 - blend) +
                node.child->radius * blend);
            require_finite(result.point, "FUN_00759210 blended point");
            require_finite_value(result.scalar, "FUN_00759210 blended scalar");
            return result;
        }
    }

    SurfaceProbeResult result{};
    result.point = candidate;
    result.scalar = std::abs(node.radius);
    require_finite(result.point, "FUN_00759210 candidate point");
    require_finite_value(result.scalar, "FUN_00759210 radius scalar");
    return result;
}

}  // namespace shift::runtime::physics
