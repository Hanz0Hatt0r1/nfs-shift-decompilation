#include "shift_collision_query.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <optional>
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

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const auto query =
            build_fun_00765c40_collision_query_record(
                {1.0, 2.0, 3.0},
                CollisionQueryAddressToken{0x1234u});
        require_close(query.query_position[0], 1.0, 0.0, "query X", max_error);
        require_close(query.query_position[1], 2.15, 1e-15, "query Y bias", max_error);
        require_close(query.query_position[2], 3.0, 0.0, "query Z", max_error);
        require_close(query.y_tolerance, 200.35, 0.0, "query +0x18", max_error);
        require_close(
            query.max_aux,
            9.999999933815813e36,
            0.0,
            "query +0x20",
            max_error);
        if (query.output_height_valid || !query.cache_enabled ||
            !query.cache_handle.has_value() ||
            *query.cache_handle != 0x1234u) {
            throw std::runtime_error("query record topology mismatch");
        }

        const CollisionSurfaceRecord surface = {
            0x1234u,
            {1.0, 2.15, 3.0},
            {0.0, 0.8, 0.6},
            1.25,
            {0.0, 0.0, 0.0},
            {1.0, 0.0, 0.0},
            {0.0, 0.0, 1.0},
            1u,
            7u,
        };

        const auto hit =
            apply_fun_007b0710_visible_result(query, surface);
        if (!hit.hit || !hit.returned_handle.has_value() ||
            *hit.returned_handle != 0x1234u || !hit.reused_cache ||
            !hit.query_after.output_height_valid ||
            !hit.query_after.cache_handle.has_value() ||
            *hit.query_after.cache_handle != 0x1234u) {
            throw std::runtime_error("hit/cache result mismatch");
        }
        require_close(hit.normal[0], 0.0, 0.0, "hit normal X", max_error);
        require_close(hit.normal[1], 0.8, 0.0, "hit normal Y", max_error);
        require_close(hit.normal[2], 0.6, 0.0, "hit normal Z", max_error);
        require_close(
            hit.query_after.output_height,
            1.25,
            0.0,
            "hit +0x28 height",
            max_error);

        const auto hit_state =
            apply_fun_00765c40_post_query_state(4.0, 9.0, hit);
        if (!hit_state.state_0x38dc.has_value() ||
            *hit_state.state_0x38dc != 0x1234u) {
            throw std::runtime_error("hit +0x38dc mismatch");
        }
        require_close(
            hit_state.state_0x38e0,
            2.75,
            0.0,
            "hit +0x38e0 mismatch",
            max_error);

        const auto miss =
            apply_fun_007b0710_visible_result(query, std::nullopt);
        if (miss.hit || miss.returned_handle.has_value() || miss.reused_cache) {
            throw std::runtime_error("miss result mismatch");
        }
        require_close(miss.normal[0], 0.0, 0.0, "miss normal X", max_error);
        require_close(miss.normal[1], 1.0, 0.0, "miss normal Y", max_error);
        require_close(miss.normal[2], 0.0, 0.0, "miss normal Z", max_error);
        const auto miss_state =
            apply_fun_00765c40_post_query_state(4.0, 7.5, miss);
        if (miss_state.state_0x38dc.has_value()) {
            throw std::runtime_error("miss +0x38dc should be null");
        }
        require_close(
            miss_state.state_0x38e0,
            7.5,
            0.0,
            "miss +0x38e0 fallback mismatch",
            max_error);

        auto different_surface = surface;
        different_surface.address_token = 0x5678u;
        const auto different_hit =
            apply_fun_007b0710_visible_result(query, different_surface);
        if (!different_hit.hit || different_hit.reused_cache) {
            throw std::runtime_error("different cache token was treated as reused");
        }

        bool invalid_flag_rejected = false;
        try {
            auto invalid_surface = surface;
            invalid_surface.valid = 2u;
            (void)apply_fun_007b0710_visible_result(query, invalid_surface);
        } catch (const std::invalid_argument&) {
            invalid_flag_rejected = true;
        }
        if (!invalid_flag_rejected) {
            throw std::runtime_error("invalid +0x44 flag was accepted");
        }

        bool non_finite_rejected = false;
        try {
            (void)build_fun_00765c40_collision_query_record(
                {0.0, std::numeric_limits<double>::infinity(), 0.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite query input was accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeCollisionQuery/1\","
            << "\"ready\":true,"
            << "\"query_function\":\"FUN_007b0710\","
            << "\"caller\":\"FUN_00765c40\","
            << "\"query_record_doubles\":7,"
            << "\"surface_record_size\":88,"
            << "\"cache_reuse_visible\":true,"
            << "\"hit_miss_normal_proven\":true,"
            << "\"caller_state_38dc_38e0_proven\":true,"
            << "\"collision_backend_proven\":false,"
            << "\"world_position_transform_proven\":false,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
