#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeCollisionQueryFormat =
    "SHIFT.NativeCollisionQuery/1";
inline constexpr const char* kCollisionQueryFunction = "FUN_007b0710";
inline constexpr const char* kCollisionQueryCallerFunction = "FUN_00765c40";
inline constexpr const char* kCollisionQueryFallbackFunction = "FUN_0074f560";

inline constexpr std::size_t kCollisionQueryRecordDoubleCount = 7u;
inline constexpr std::size_t kCollisionSurfaceRecordSize = 0x58u;
inline constexpr double kCollisionQueryYBias = 0.15;
inline constexpr double kCollisionQueryYTolerance = 200.35;
inline constexpr double kCollisionQueryMaxAux = 9.999999933815813e36;
inline constexpr unsigned int kCollisionQueryCacheFlag = 1u;

using CollisionQueryVector3d = std::array<double, 3>;
using CollisionQueryAddressToken = std::uint64_t;

struct CollisionQueryRecord {
    CollisionQueryVector3d query_position{};
    double y_tolerance = kCollisionQueryYTolerance;
    double max_aux = kCollisionQueryMaxAux;
    double output_height = 0.0;
    bool output_height_valid = false;
    std::optional<CollisionQueryAddressToken> cache_handle{};
    bool cache_enabled = true;
};

struct CollisionSurfaceRecord {
    CollisionQueryAddressToken address_token = 0u;
    CollisionQueryVector3d query_point{};
    CollisionQueryVector3d normal{};
    double contact_height = 0.0;
    CollisionQueryVector3d triangle_a{};
    CollisionQueryVector3d triangle_b{};
    CollisionQueryVector3d triangle_c{};
    unsigned int valid = 1u;
    std::optional<unsigned int> hit_count{};
};

struct CollisionQueryVisibleResult {
    bool hit = false;
    CollisionQueryRecord query_after{};
    CollisionQueryVector3d normal{};
    std::optional<CollisionQueryAddressToken> returned_handle{};
    bool reused_cache = false;
};

struct WheelCollisionQueryStateUpdate {
    std::optional<CollisionQueryAddressToken> state_0x38dc{};
    double state_0x38e0 = 0.0;
};

CollisionQueryRecord build_fun_00765c40_collision_query_record(
    const CollisionQueryVector3d& world_position,
    std::optional<CollisionQueryAddressToken> cached_handle = std::nullopt);

CollisionQueryVisibleResult apply_fun_007b0710_visible_result(
    const CollisionQueryRecord& query,
    const std::optional<CollisionSurfaceRecord>& surface);

WheelCollisionQueryStateUpdate apply_fun_00765c40_post_query_state(
    double original_world_y,
    double fallback_value,
    const CollisionQueryVisibleResult& query_result);

}  // namespace shift::runtime::physics
