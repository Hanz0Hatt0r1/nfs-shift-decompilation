#include "shift_fun_00765c40_external_pass_result.hpp"
#include "shift_fun_00766510_query_scalar_handoff.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
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

CollisionSurfaceRecord make_surface(
    const CollisionQueryRecord& query,
    std::uint64_t token,
    double contact_height) {
    CollisionSurfaceRecord surface{};
    surface.address_token = token;
    surface.query_point = query.query_position;
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = contact_height;
    surface.triangle_a = {0.0, 0.0, 0.0};
    surface.triangle_b = {1.0, 0.0, 0.0};
    surface.triangle_c = {0.0, 0.0, 1.0};
    return surface;
}

}  // namespace

int main() {
    try {
        Fun00765c40ExternalPassInput request{};
        request.world_position = CollisionQueryVector3d{10.0, 20.0, 30.0};
        request.cached_handle = std::uint64_t{1234u};
        const auto fallback = request.selected_bmw_miss_fallback();
        require(fallback.has_value(),
                "selected BMW request did not expose +0x38e8 fallback");

        Fun00765c40QueryInputBoundary input{};
        input.world_position = *request.world_position;
        input.cached_handle = request.cached_handle;
        input.miss_fallback = *fallback;
        const auto query = build_fun_00765c40_query_record(input);

        const auto reused_hit = apply_fun_007b0710_collision_query_result(
            query,
            make_surface(query, 1234u, 19.95));
        require(reused_hit.hit && reused_hit.reused_cache &&
                    reused_hit.returned_handle == 1234u,
                "FUN_007b0710 reused-cache hit handoff drift");
        validate_fun_00765c40_collision_output_handoff(input, reused_hit);
        const auto reused_handoff =
            execute_fun_00765c40_to_00766510_query_scalar_handoff(
                input,
                reused_hit);
        require_close(reused_handoff.query_scalar, 0.05, 1e-12,
                      "FUN_00765c40 hit scalar projection drift");
        require_close(reused_handoff.clamped_query_scalar, 0.05, 1e-12,
                      "FUN_00766510 in-range clamp drift");

        const auto high_hit = apply_fun_007b0710_collision_query_result(
            query,
            make_surface(query, 5678u, 19.5));
        validate_fun_00765c40_collision_output_handoff(input, high_hit);
        const auto high_handoff =
            execute_fun_00765c40_to_00766510_query_scalar_handoff(
                input,
                high_hit);
        require_close(high_handoff.query_scalar, 0.5, 1e-15,
                      "FUN_00765c40 high hit scalar drift");
        require_close(high_handoff.clamped_query_scalar, *fallback, 0.0,
                      "FUN_00766510 upper clamp did not reuse +0x38e8");

        const auto negative_hit = apply_fun_007b0710_collision_query_result(
            query,
            make_surface(query, 9012u, 20.5));
        const auto negative_handoff =
            execute_fun_00765c40_to_00766510_query_scalar_handoff(
                input,
                negative_hit);
        require_close(negative_handoff.query_scalar, -0.5, 1e-15,
                      "FUN_00765c40 negative hit scalar drift");
        require_close(negative_handoff.clamped_query_scalar, 0.0, 0.0,
                      "FUN_00766510 lower clamp drift");

        const auto miss =
            apply_fun_007b0710_collision_query_result(query, std::nullopt);
        validate_fun_00765c40_collision_output_handoff(input, miss);
        const auto miss_handoff =
            execute_fun_00765c40_to_00766510_query_scalar_handoff(input, miss);
        require(!miss.hit && !miss.returned_handle.has_value(),
                "FUN_007b0710 miss unexpectedly returned cache handle");
        require_close(miss_handoff.query_scalar, *fallback, 0.0,
                      "FUN_00765c40 miss did not use +0x38e8 fallback");
        require_close(miss_handoff.clamped_query_scalar, *fallback, 0.0,
                      "FUN_00766510 miss clamp changed +0x38e8 fallback");

        const Fun00765c40ExternalPassResult selected_result{
            Fun00765c40LoadTerms{1.0, 2.0, 3.0, 4.0},
            input,
            high_hit.returned_handle,
            high_hit};
        validate_fun_00765c40_external_pass_result(request, selected_result);

        bool hidden_output_rejected = false;
        try {
            auto hidden = selected_result;
            hidden.query_output.reset();
            validate_fun_00765c40_external_pass_result(request, hidden);
        } catch (const std::invalid_argument&) {
            hidden_output_rejected = true;
        }
        require(hidden_output_rejected,
                "selected BMW residual provider hid collision output");

        bool wrong_record_rejected = false;
        try {
            auto wrong = selected_result;
            wrong.query_output->query_record.query_position[0] += 1.0;
            validate_fun_00765c40_external_pass_result(request, wrong);
        } catch (const std::invalid_argument&) {
            wrong_record_rejected = true;
        }
        require(wrong_record_rejected,
                "collision output accepted query record from another request");

        std::cout
            << "{\"format\":\"SHIFT.Fun00765c40CollisionOutputHandoff/1\","
            << "\"ready\":true,"
            << "\"external_result_format\":\"" << kFun00765c40ExternalPassResultFormat << "\","
            << "\"scalar_handoff_format\":\"" << kFun00766510QueryScalarHandoffFormat << "\","
            << "\"selected_collision_output_required\":true,"
            << "\"hit_projected\":true,"
            << "\"miss_fallback_reused\":true,"
            << "\"upper_lower_clamp_native\":true,"
            << "\"contact_response_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
