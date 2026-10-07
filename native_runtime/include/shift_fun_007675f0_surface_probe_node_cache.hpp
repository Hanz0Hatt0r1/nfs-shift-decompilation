#pragma once

#include "shift_surface_probe.hpp"

#include <array>
#include <cmath>
#include <functional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0SurfaceProbeNodeCacheFormat =
    "SHIFT.Fun007675f0SurfaceProbeNodeCache/1";
inline constexpr std::size_t kFun007675f0SurfaceProbeNodeOffset = 0x120u;
inline constexpr std::size_t kFun007675f0SurfaceProbeLastPositionXOffset = 0x128u;
inline constexpr std::size_t kFun007675f0SurfaceProbeLastPositionYOffset = 0x130u;
inline constexpr std::size_t kFun007675f0SurfaceProbeLastPositionZOffset = 0x138u;
inline constexpr double kFun007675f0SurfaceProbeRefreshDistanceSquared = 0.01;

using Fun00717cd0SurfaceProbeNodeLookupProvider =
    std::function<const SurfaceProbeNode*(
        const SurfaceProbeVector3d& query_position,
        const SurfaceProbeNode* previous_node)>;

struct Fun007675f0SurfaceProbeNodeCache {
    const SurfaceProbeNode* node = nullptr;
    SurfaceProbeVector3d last_body_position{};
    bool last_body_position_valid = false;
};

inline void validate_fun_007675f0_surface_probe_position(
    const SurfaceProbeVector3d& position,
    const char* label) {
    for (double value : position) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(label);
        }
    }
}

inline double fun_007675f0_surface_probe_cache_distance_squared(
    const SurfaceProbeVector3d& current_body_position,
    const SurfaceProbeVector3d& last_body_position) {
    validate_fun_007675f0_surface_probe_position(
        current_body_position,
        "FUN_007675f0 current BODY0 position must be finite");
    validate_fun_007675f0_surface_probe_position(
        last_body_position,
        "FUN_007675f0 cached BODY0 position must be finite");

    const double dx = current_body_position[0] - last_body_position[0];
    const double dy = current_body_position[1] - last_body_position[1];
    const double dz = current_body_position[2] - last_body_position[2];
    const double distance_squared = dx * dx + dy * dy + dz * dz;
    if (!std::isfinite(distance_squared)) {
        throw std::invalid_argument(
            "FUN_007675f0 node-cache distance squared must be finite");
    }
    return distance_squared;
}

inline bool should_refresh_fun_007675f0_surface_probe_node_cache(
    const Fun007675f0SurfaceProbeNodeCache& cache,
    const SurfaceProbeVector3d& current_body_position) {
    validate_fun_007675f0_surface_probe_position(
        current_body_position,
        "FUN_007675f0 current BODY0 position must be finite");

    // PC retail initializes HDVehicle+0x120 to null. A null cached node always
    // forces FUN_00717cd0 regardless of the last-position fields. Once a node is
    // present, the refresh test is strict: squared 3D displacement > 0.01.
    if (cache.node == nullptr || !cache.last_body_position_valid) {
        return true;
    }
    return fun_007675f0_surface_probe_cache_distance_squared(
               current_body_position,
               cache.last_body_position) >
        kFun007675f0SurfaceProbeRefreshDistanceSquared;
}

inline const SurfaceProbeNode* resolve_fun_007675f0_surface_probe_node_cache(
    Fun007675f0SurfaceProbeNodeCache& cache,
    const SurfaceProbeVector3d& current_body_position,
    const SurfaceProbeVector3d& query_position,
    const Fun00717cd0SurfaceProbeNodeLookupProvider& lookup_provider) {
    validate_fun_007675f0_surface_probe_position(
        current_body_position,
        "FUN_007675f0 current BODY0 position must be finite");
    validate_fun_007675f0_surface_probe_position(
        query_position,
        "FUN_00717cd0 query position must be finite");
    if (!lookup_provider) {
        throw std::invalid_argument(
            "FUN_007675f0 node-cache refresh requires FUN_00717cd0 lookup provider");
    }

    if (should_refresh_fun_007675f0_surface_probe_node_cache(
            cache,
            current_body_position)) {
        const SurfaceProbeNode* previous_node = cache.node;
        cache.node = lookup_provider(query_position, previous_node);
        // PC stores the exact f64 BODY0 origin to HDVehicle+0x128/+0x130/+0x138
        // after every lookup call, even when the returned node is null.
        cache.last_body_position = current_body_position;
        cache.last_body_position_valid = true;
    }
    return cache.node;
}

}  // namespace shift::runtime::physics
