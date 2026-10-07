#include "shift_fun_00765c40_query_input_boundary.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(double actual, double expected, double tolerance, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(message);
    }
}

CollisionSurfaceRecord make_surface() {
    CollisionSurfaceRecord surface{};
    surface.address_token = 1234u;
    surface.query_point = {10.0, 20.15, 30.0};
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = 19.75;
    surface.triangle_a = {9.0, 19.0, 29.0};
    surface.triangle_b = {11.0, 19.0, 29.0};
    surface.triangle_c = {10.0, 19.0, 31.0};
    surface.valid = 1;
    return surface;
}

}  // namespace

int main() {
    try {
        Fun00765c40QueryInputBoundary input{};
        input.world_position = {10.0, 20.0, 30.0};
        input.cached_handle = 1234u;
        input.miss_fallback = 7.0;
        validate_fun_00765c40_query_input_boundary(input);

        const auto query = build_fun_00765c40_query_record(input);
        require_close(query.query_position[0], 10.0, 0.0, "query X mismatch");
        require_close(query.query_position[1], 20.15, 1e-14, "query Y bias mismatch");
        require_close(query.query_position[2], 30.0, 0.0, "query Z mismatch");
        require(query.cache_handle == 1234u, "cached handle was not propagated");
        require(query.param3() == 1, "cache-aware query flag drift");

        const auto hit = apply_fun_007b0710_collision_query_result(query, make_surface());
        require_close(
            project_fun_00765c40_query_input_scalar(input, hit),
            0.25,
            1e-15,
            "query-input hit scalar mismatch");

        const auto miss = apply_fun_007b0710_collision_query_result(query, std::nullopt);
        require_close(
            project_fun_00765c40_query_input_scalar(input, miss),
            7.0,
            0.0,
            "query-input miss fallback mismatch");

        bool nonfinite_position_rejected = false;
        try {
            auto invalid = input;
            invalid.world_position[0] = std::numeric_limits<double>::infinity();
            validate_fun_00765c40_query_input_boundary(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_position_rejected = true;
        }
        require(nonfinite_position_rejected,
                "non-finite FUN_00765c40 world position failed open");

        bool nonfinite_fallback_rejected = false;
        try {
            auto invalid = input;
            invalid.miss_fallback = std::numeric_limits<double>::quiet_NaN();
            validate_fun_00765c40_query_input_boundary(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_fallback_rejected = true;
        }
        require(nonfinite_fallback_rejected,
                "non-finite FUN_00765c40 miss fallback failed open");

        std::cout
            << "{\"format\":\"" << kFun00765c40QueryInputBoundaryFormat << "\","
            << "\"ready\":true,"
            << "\"query_y_bias\":0.15,"
            << "\"cache_handle_propagated\":true,"
            << "\"caller_world_y_reused_for_hit_scalar\":true,"
            << "\"miss_fallback_reused\":true,"
            << "\"world_position_producer_internalized\":false,"
            << "\"collision_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
