#include "shift_collision_query.hpp"

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

void require_query(const CollisionQueryRecord& query) {
    require_finite(query.query_position, "FUN_007b0710 query position");
    require_finite_value(query.y_tolerance, "FUN_007b0710 query +0x18");
    require_finite_value(query.max_aux, "FUN_007b0710 query +0x20");
    if (query.output_height_valid) {
        require_finite_value(query.output_height, "FUN_007b0710 query +0x28");
    }
}

void require_surface(const CollisionSurfaceRecord& surface) {
    require_finite(surface.query_point, "FUN_007b0710 cache query point");
    require_finite(surface.normal, "FUN_007b0710 cache normal");
    require_finite_value(surface.contact_height, "FUN_007b0710 cache height");
    require_finite(surface.triangle_a, "FUN_007b0710 triangle A");
    require_finite(surface.triangle_b, "FUN_007b0710 triangle B");
    require_finite(surface.triangle_c, "FUN_007b0710 triangle C");
    if (surface.valid > 1u) {
        throw std::invalid_argument("FUN_007b0710 cache +0x44 must be 0 or 1");
    }
}

}  // namespace

CollisionQueryRecord build_fun_00765c40_collision_query_record(
    const CollisionQueryVector3d& world_position,
    std::optional<CollisionQueryAddressToken> cached_handle) {

    require_finite(world_position, "FUN_00765c40 world position");

    CollisionQueryRecord query{};
    query.query_position = {
        world_position[0],
        world_position[1] + kCollisionQueryYBias,
        world_position[2],
    };
    query.y_tolerance = kCollisionQueryYTolerance;
    query.max_aux = kCollisionQueryMaxAux;
    query.output_height = 0.0;
    query.output_height_valid = false;
    query.cache_handle = cached_handle;
    query.cache_enabled = true;
    require_query(query);
    return query;
}

CollisionQueryVisibleResult apply_fun_007b0710_visible_result(
    const CollisionQueryRecord& query,
    const std::optional<CollisionSurfaceRecord>& surface) {

    require_query(query);

    CollisionQueryVisibleResult result{};
    result.query_after = query;
    if (!surface.has_value()) {
        result.hit = false;
        result.normal = {0.0, 1.0, 0.0};
        result.returned_handle = std::nullopt;
        result.reused_cache = false;
        return result;
    }

    require_surface(*surface);
    result.hit = true;
    result.normal = surface->normal;
    result.returned_handle = surface->address_token;
    result.reused_cache =
        query.cache_handle.has_value() &&
        *query.cache_handle == surface->address_token;
    result.query_after.output_height = surface->contact_height;
    result.query_after.output_height_valid = true;
    result.query_after.cache_handle = surface->address_token;
    return result;
}

WheelCollisionQueryStateUpdate apply_fun_00765c40_post_query_state(
    double original_world_y,
    double fallback_value,
    const CollisionQueryVisibleResult& query_result) {

    require_finite_value(original_world_y, "FUN_00765c40 original world Y");
    require_finite_value(fallback_value, "FUN_00765c40 +0x38e8 fallback");
    require_finite(query_result.normal, "FUN_00765c40 query normal");

    WheelCollisionQueryStateUpdate result{};
    result.state_0x38dc = query_result.returned_handle;
    if (!query_result.hit) {
        result.state_0x38e0 = fallback_value;
        return result;
    }

    if (!query_result.returned_handle.has_value() ||
        !query_result.query_after.output_height_valid) {
        throw std::invalid_argument(
            "FUN_00765c40 hit result lacks handle or +0x28 height");
    }
    require_finite_value(
        query_result.query_after.output_height,
        "FUN_00765c40 returned contact height");
    result.state_0x38e0 =
        original_world_y - query_result.query_after.output_height;
    require_finite_value(result.state_0x38e0, "FUN_00765c40 +0x38e0 result");
    return result;
}

}  // namespace shift::runtime::physics
