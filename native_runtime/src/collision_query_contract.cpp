#include "shift_collision_query_contract.hpp"

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

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
}

void require_surface(const CollisionSurfaceRecord& surface) {
    require_finite(surface.query_point, "FUN_007b0710 cached query point");
    require_finite(surface.normal, "FUN_007b0710 returned normal");
    require_finite_value(surface.contact_height, "FUN_007b0710 contact height");
    require_finite(surface.triangle_a, "FUN_007b0710 triangle A");
    require_finite(surface.triangle_b, "FUN_007b0710 triangle B");
    require_finite(surface.triangle_c, "FUN_007b0710 triangle C");
    if (surface.valid != 0 && surface.valid != 1) {
        throw std::invalid_argument("FUN_007b0710 valid flag must be 0 or 1");
    }
}

}  // namespace

CollisionQueryRecord build_fun_00765c40_collision_query_record(
    const CollisionQueryVector3d& world_position,
    std::optional<std::uint64_t> cached_handle) {

    require_finite(world_position, "FUN_00765c40 query world position");

    CollisionQueryRecord result{};
    result.query_position = {
        world_position[0],
        world_position[1] + kCollisionQueryYBias,
        world_position[2],
    };
    require_finite(result.query_position, "FUN_00765c40 biased query position");
    result.y_tolerance = kCollisionQueryYTolerance;
    result.max_aux = kCollisionQueryMaxAux;
    result.output_height.reset();
    result.cache_handle = cached_handle;
    result.cache_enabled = true;
    return result;
}

CollisionQueryOutput apply_fun_007b0710_collision_query_result(
    const CollisionQueryRecord& query,
    const std::optional<CollisionSurfaceRecord>& surface) {

    require_finite(query.query_position, "FUN_007b0710 query position");
    require_finite_value(query.y_tolerance, "FUN_007b0710 query y tolerance");
    require_finite_value(query.max_aux, "FUN_007b0710 query max auxiliary");
    if (query.output_height.has_value()) {
        require_finite_value(
            *query.output_height,
            "FUN_007b0710 incoming query output height");
    }

    CollisionQueryOutput result{};
    result.query_record = query;
    if (!surface.has_value()) {
        result.hit = false;
        result.normal = {0.0, 1.0, 0.0};
        result.contact_height.reset();
        result.returned_handle.reset();
        result.reused_cache = false;
        return result;
    }

    require_surface(*surface);
    result.hit = true;
    result.normal = surface->normal;
    result.contact_height = surface->contact_height;
    result.returned_handle = surface->address_token;
    result.reused_cache =
        query.cache_handle.has_value() &&
        *query.cache_handle == surface->address_token;
    result.query_record.output_height = surface->contact_height;
    result.query_record.cache_handle = surface->address_token;
    return result;
}

double project_fun_00765c40_query_scalar(
    double original_world_y,
    const CollisionQueryOutput& query_output,
    double fallback_value) {

    require_finite_value(original_world_y, "FUN_00765c40 original world Y");
    require_finite_value(fallback_value, "FUN_00765c40 fallback value");

    if (!query_output.hit) {
        return fallback_value;
    }
    if (!query_output.contact_height.has_value()) {
        throw std::invalid_argument(
            "FUN_00765c40 hit result is missing contact height");
    }
    require_finite_value(
        *query_output.contact_height,
        "FUN_00765c40 returned contact height");
    const double result = original_world_y - *query_output.contact_height;
    require_finite_value(result, "FUN_00765c40 projected query scalar");
    return result;
}

}  // namespace shift::runtime::physics
