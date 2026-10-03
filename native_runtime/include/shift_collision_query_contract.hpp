#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeCollisionQueryContractFormat =
    "SHIFT.NativeCollisionQueryContract/1";
inline constexpr const char* kCollisionQueryFunction = "FUN_007b0710";
inline constexpr const char* kCollisionQueryCallerFunction = "FUN_00765c40";
inline constexpr const char* kCollisionQueryFallbackFunction = "FUN_0074f560";

inline constexpr std::size_t kCollisionQueryPositionOffset = 0x00u;
inline constexpr std::size_t kCollisionQueryYToleranceOffset = 0x18u;
inline constexpr std::size_t kCollisionQueryMaxAuxOffset = 0x20u;
inline constexpr std::size_t kCollisionQueryOutputHeightOffset = 0x28u;
inline constexpr std::size_t kCollisionQueryCacheHandleOffset = 0x30u;
inline constexpr std::size_t kCollisionQueryRecordDoubles = 7u;

inline constexpr double kCollisionQueryYBias = 0.15;
inline constexpr double kCollisionQueryYTolerance = 200.35;
inline constexpr double kCollisionQueryMaxAux = 9.999999933815813e36;
inline constexpr int kCollisionQueryCacheFlag = 1;

inline constexpr std::size_t kCollisionCacheRecordSize = 0x58u;
inline constexpr std::size_t kCollisionCacheQueryPointOffset = 0x04u;
inline constexpr std::size_t kCollisionCacheNormalOffset = 0x10u;
inline constexpr std::size_t kCollisionCacheContactHeightOffset = 0x1cu;
inline constexpr std::size_t kCollisionCacheTriangleAOffset = 0x20u;
inline constexpr std::size_t kCollisionCacheTriangleBOffset = 0x2cu;
inline constexpr std::size_t kCollisionCacheTriangleCOffset = 0x38u;
inline constexpr std::size_t kCollisionCacheValidOffset = 0x44u;
inline constexpr std::size_t kCollisionCacheAuxOffset = 0x48u;
inline constexpr std::size_t kCollisionCacheHitCountOffset = 0x50u;

inline constexpr std::size_t kCollisionCallerHandleOffset = 0x38dcu;
inline constexpr std::size_t kCollisionCallerScalarOffset = 0x38e0u;
inline constexpr std::size_t kCollisionCallerFallbackOffset = 0x38e8u;

using CollisionQueryVector3d = std::array<double, 3>;

struct CollisionQueryRecord {
    CollisionQueryVector3d query_position{};
    double y_tolerance = kCollisionQueryYTolerance;
    double max_aux = kCollisionQueryMaxAux;
    std::optional<double> output_height{};
    std::optional<std::uint64_t> cache_handle{};
    bool cache_enabled = true;

    int param3() const {
        return cache_enabled ? kCollisionQueryCacheFlag : 0;
    }
};

struct CollisionSurfaceRecord {
    std::uint64_t address_token = 0u;
    CollisionQueryVector3d query_point{};
    CollisionQueryVector3d normal{};
    double contact_height = 0.0;
    CollisionQueryVector3d triangle_a{};
    CollisionQueryVector3d triangle_b{};
    CollisionQueryVector3d triangle_c{};
    int valid = 1;
    std::optional<std::uint64_t> hit_count{};
};

struct CollisionQueryOutput {
    bool hit = false;
    CollisionQueryVector3d normal{0.0, 1.0, 0.0};
    std::optional<double> contact_height{};
    std::optional<std::uint64_t> returned_handle{};
    bool reused_cache = false;
};

CollisionQueryRecord build_fun_00765c40_collision_query_record(
    const CollisionQueryVector3d& world_position,
    std::optional<std::uint64_t> cached_handle = std::nullopt);

CollisionQueryOutput apply_fun_007b0710_collision_query_result(
    const CollisionQueryRecord& query,
    const std::optional<CollisionSurfaceRecord>& surface);

double project_fun_00765c40_query_scalar(
    double original_world_y,
    const CollisionQueryOutput& query_output,
    double fallback_value);

}  // namespace shift::runtime::physics
