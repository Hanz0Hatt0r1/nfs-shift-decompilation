#include "shift_fun_00765c40_external_pass_result.hpp"

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

CollisionQueryOutput make_hit_output(
    const Fun00765c40QueryInputBoundary& input,
    std::uint64_t returned_handle) {
    const auto record = build_fun_00765c40_query_record(input);
    CollisionSurfaceRecord surface{};
    surface.address_token = returned_handle;
    surface.query_point = record.query_position;
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = input.world_position[1] - 0.05;
    surface.triangle_a = {0.0, 0.0, 0.0};
    surface.triangle_b = {1.0, 0.0, 0.0};
    surface.triangle_c = {0.0, 0.0, 1.0};
    return apply_fun_007b0710_collision_query_result(record, surface);
}

}  // namespace

int main() {
    try {
        Fun00765c40ExternalPassInput input{};
        input.world_position = CollisionQueryVector3d{10.0, 20.0, 30.0};
        input.cached_handle = 1234u;
        const auto selected_fallback = input.selected_bmw_miss_fallback();
        require(selected_fallback.has_value(),
                "selected BMW request did not expose native +0x38e8 fallback");
        const auto native_query = input.selected_bmw_query_input();
        require(native_query.has_value(),
                "selected BMW request did not materialize native query input");
        require(native_query->world_position == *input.world_position &&
                    native_query->cached_handle == input.cached_handle &&
                    native_query->miss_fallback == *selected_fallback,
                "selected BMW native query input ownership drift");

        const auto query_output = make_hit_output(*native_query, 5678u);
        const Fun00765c40ExternalPassResult valid{
            Fun00765c40LoadTerms{10.0, 20.0, 30.0, 40.0},
            *native_query,
            5678u,
            query_output};
        validate_fun_00765c40_external_pass_result(input, valid);
        require(valid.load_terms[0] == 10.0 && valid.load_terms[3] == 40.0,
                "FUN_00765c40 external pass result changed typed load terms");
        require(valid.returned_cache_handle == 5678u,
                "FUN_00765c40 external pass result lost returned cache handle");
        require(valid.query_output.has_value() && valid.query_output->hit &&
                    valid.query_output->returned_handle == 5678u,
                "FUN_00765c40 external pass result lost collision output");

        bool missing_output_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.query_output.reset();
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            missing_output_rejected = true;
        }
        require(missing_output_rejected,
                "selected BMW provider hid FUN_007b0710 output");

        bool cache_mismatch_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.query_input.cached_handle = 9999u;
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            cache_mismatch_rejected = true;
        }
        require(cache_mismatch_rejected,
                "FUN_00765c40 residual provider accepted wrong native cache input");

        bool world_position_mismatch_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.query_input.world_position[0] += 1.0;
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            world_position_mismatch_rejected = true;
        }
        require(world_position_mismatch_rejected,
                "FUN_00765c40 residual provider accepted wrong selected world position");

        bool fallback_mismatch_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.query_input.miss_fallback = 7.0;
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            fallback_mismatch_rejected = true;
        }
        require(fallback_mismatch_rejected,
                "FUN_00765c40 residual provider accepted wrong selected +0x38e8 fallback");

        bool returned_handle_mismatch_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.returned_cache_handle = 9999u;
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            returned_handle_mismatch_rejected = true;
        }
        require(returned_handle_mismatch_rejected,
                "FUN_00765c40 accepted cache write different from collision output");

        bool nonfinite_load_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.load_terms[2] = std::numeric_limits<double>::quiet_NaN();
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_load_rejected = true;
        }
        require(nonfinite_load_rejected,
                "FUN_00765c40 external pass result accepted non-finite load term");

        bool nonfinite_query_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.query_input.world_position[1] =
                std::numeric_limits<double>::infinity();
            validate_fun_00765c40_external_pass_result(input, invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_query_rejected = true;
        }
        require(nonfinite_query_rejected,
                "FUN_00765c40 external pass result accepted non-finite query input");

        Fun00765c40ExternalPassInput generic_input{};
        generic_input.cached_handle = std::nullopt;
        require(!generic_input.selected_bmw_query_input().has_value(),
                "generic request incorrectly materialized selected BMW query input");
        Fun00765c40ExternalPassResult generic_result = valid;
        generic_result.query_input.cached_handle = std::nullopt;
        generic_result.query_output.reset();
        generic_result.returned_cache_handle = 5678u;
        validate_fun_00765c40_external_pass_result(generic_input, generic_result);

        std::cout
            << "{\"format\":\"" << kFun00765c40ExternalPassResultFormat << "\","
            << "\"ready\":true,"
            << "\"load_term_count\":4,"
            << "\"query_input_boundary_typed\":true,"
            << "\"selected_query_input_native_owned\":true,"
            << "\"selected_collision_output_required\":true,"
            << "\"returned_cache_handle_typed\":true,"
            << "\"complete_fun_00765c40_internalized\":false,"
            << "\"collision_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
