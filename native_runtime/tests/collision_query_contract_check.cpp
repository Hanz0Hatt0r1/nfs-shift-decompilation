#include "shift_collision_query_contract.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

shift::runtime::physics::CollisionSurfaceRecord sample_surface(
    std::uint64_t address_token = 1234u) {
    using namespace shift::runtime::physics;
    CollisionSurfaceRecord surface{};
    surface.address_token = address_token;
    surface.query_point = {10.0, 20.15, 30.0};
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = 19.75;
    surface.triangle_a = {9.0, 19.0, 29.0};
    surface.triangle_b = {11.0, 19.0, 29.0};
    surface.triangle_c = {10.0, 19.0, 31.0};
    surface.valid = 1;
    surface.hit_count = 4u;
    return surface;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        if (kCollisionQueryCacheHandleOffset != 0x30u ||
            kCollisionQueryRecordDoubles != 7u ||
            kCollisionQueryCacheFlag != 1 ||
            kCollisionCacheRecordSize != 0x58u ||
            kCollisionCacheNormalOffset != 0x10u ||
            kCollisionCacheContactHeightOffset != 0x1cu ||
            kCollisionCacheTriangleAOffset != 0x20u ||
            kCollisionCacheTriangleBOffset != 0x2cu ||
            kCollisionCacheTriangleCOffset != 0x38u) {
            throw std::runtime_error("collision-query layout constant mismatch");
        }

        const auto query = build_fun_00765c40_collision_query_record(
            {10.0, 20.0, 30.0},
            1234u);
        require_close(query.query_position[0], 10.0, 0.0, "query X mismatch", max_error);
        require_close(query.query_position[1], 20.15, 1e-14, "query Y bias mismatch", max_error);
        require_close(query.query_position[2], 30.0, 0.0, "query Z mismatch", max_error);
        require_close(query.y_tolerance, 200.35, 0.0, "query tolerance mismatch", max_error);
        require_close(
            query.max_aux,
            9.999999933815813e36,
            0.0,
            "query max auxiliary mismatch",
            max_error);
        if (!query.cache_handle.has_value() || *query.cache_handle != 1234u ||
            query.param3() != 1 || query.output_height.has_value()) {
            throw std::runtime_error("query cache/input boundary mismatch");
        }

        const auto hit = apply_fun_007b0710_collision_query_result(
            query,
            sample_surface());
        if (!hit.hit || !hit.reused_cache ||
            !hit.returned_handle.has_value() || *hit.returned_handle != 1234u ||
            !hit.contact_height.has_value() ||
            !hit.query_record.output_height.has_value() ||
            !hit.query_record.cache_handle.has_value()) {
            throw std::runtime_error("collision-query hit projection mismatch");
        }
        require_close(hit.normal[0], 0.0, 0.0, "hit normal X mismatch", max_error);
        require_close(hit.normal[1], 1.0, 0.0, "hit normal Y mismatch", max_error);
        require_close(hit.normal[2], 0.0, 0.0, "hit normal Z mismatch", max_error);
        require_close(*hit.contact_height, 19.75, 0.0, "hit contact height mismatch", max_error);
        require_close(
            *hit.query_record.output_height,
            19.75,
            0.0,
            "query +0x28 output-height update mismatch",
            max_error);
        if (*hit.query_record.cache_handle != 1234u) {
            throw std::runtime_error("query +0x30 cache-handle update mismatch");
        }

        const auto miss = apply_fun_007b0710_collision_query_result(
            build_fun_00765c40_collision_query_record({0.0, 1.0, 2.0}),
            std::nullopt);
        if (miss.hit || miss.reused_cache || miss.contact_height.has_value() ||
            miss.returned_handle.has_value()) {
            throw std::runtime_error("collision-query miss projection mismatch");
        }
        require_close(miss.normal[0], 0.0, 0.0, "miss normal X mismatch", max_error);
        require_close(miss.normal[1], 1.0, 0.0, "miss normal Y mismatch", max_error);
        require_close(miss.normal[2], 0.0, 0.0, "miss normal Z mismatch", max_error);

        CollisionSurfaceRecord scalar_surface{};
        scalar_surface.address_token = 1u;
        scalar_surface.query_point = {0.0, 1.15, 0.0};
        scalar_surface.normal = {0.0, 1.0, 0.0};
        scalar_surface.contact_height = 0.8;
        scalar_surface.triangle_a = {0.0, 0.0, 0.0};
        scalar_surface.triangle_b = {1.0, 0.0, 0.0};
        scalar_surface.triangle_c = {0.0, 0.0, 1.0};
        const auto scalar_hit = apply_fun_007b0710_collision_query_result(
            build_fun_00765c40_collision_query_record({0.0, 1.0, 0.0}),
            scalar_surface);
        require_close(
            project_fun_00765c40_query_scalar(1.0, scalar_hit, 7.0),
            0.2,
            1e-15,
            "caller hit scalar mismatch",
            max_error);
        require_close(
            project_fun_00765c40_query_scalar(1.0, miss, 7.0),
            7.0,
            0.0,
            "caller miss fallback mismatch",
            max_error);

        const auto replaced_cache = apply_fun_007b0710_collision_query_result(
            query,
            sample_surface(5678u));
        if (replaced_cache.reused_cache ||
            !replaced_cache.query_record.cache_handle.has_value() ||
            *replaced_cache.query_record.cache_handle != 5678u) {
            throw std::runtime_error("cache replacement boundary mismatch");
        }

        bool non_finite_rejected = false;
        try {
            (void)build_fun_00765c40_collision_query_record(
                {0.0, std::numeric_limits<double>::infinity(), 0.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite query position was accepted");
        }

        bool invalid_flag_rejected = false;
        try {
            auto invalid_surface = sample_surface();
            invalid_surface.valid = 2;
            (void)apply_fun_007b0710_collision_query_result(
                query,
                invalid_surface);
        } catch (const std::invalid_argument&) {
            invalid_flag_rejected = true;
        }
        if (!invalid_flag_rejected) {
            throw std::runtime_error("invalid cache-record flag was accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeCollisionQueryContract/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_007b0710\","
            << "\"caller\":\"FUN_00765c40\","
            << "\"fallback_query\":\"FUN_0074f560\","
            << "\"query_record_doubles\":7,"
            << "\"cache_record_size\":\"0x58\","
            << "\"query_y_bias_proven\":true,"
            << "\"hit_normal_height_cache_writes_proven\":true,"
            << "\"miss_up_normal_proven\":true,"
            << "\"caller_hit_miss_scalar_proven\":true,"
            << "\"collision_provider_implemented\":false,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
