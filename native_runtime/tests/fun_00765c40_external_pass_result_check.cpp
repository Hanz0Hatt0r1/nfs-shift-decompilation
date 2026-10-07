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

}  // namespace

int main() {
    try {
        Fun00765c40ExternalPassInput input{};
        input.world_position = CollisionQueryVector3d{10.0, 20.0, 30.0};
        input.cached_handle = 1234u;

        Fun00765c40QueryInputBoundary query_input{};
        query_input.world_position = *input.world_position;
        query_input.cached_handle = input.cached_handle;
        query_input.miss_fallback = 7.0;

        const Fun00765c40ExternalPassResult valid{
            Fun00765c40LoadTerms{10.0, 20.0, 30.0, 40.0},
            query_input,
            5678u};
        validate_fun_00765c40_external_pass_result(input, valid);
        require(valid.load_terms[0] == 10.0 && valid.load_terms[3] == 40.0,
                "FUN_00765c40 external pass result changed typed load terms");
        require(valid.returned_cache_handle == 5678u,
                "FUN_00765c40 external pass result lost returned cache handle");
        const auto record = build_fun_00765c40_query_record(valid.query_input);
        require(record.query_position[0] == 10.0 &&
                    record.query_position[1] == 20.15 &&
                    record.query_position[2] == 30.0 &&
                    record.cache_handle == 1234u,
                "FUN_00765c40 external pass result did not preserve query input");

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
        Fun00765c40ExternalPassResult generic_result = valid;
        generic_result.query_input.cached_handle = std::nullopt;
        validate_fun_00765c40_external_pass_result(generic_input, generic_result);

        std::cout
            << "{\"format\":\"" << kFun00765c40ExternalPassResultFormat << "\","
            << "\"ready\":true,"
            << "\"load_term_count\":4,"
            << "\"query_input_boundary_typed\":true,"
            << "\"native_cache_input_required\":true,"
            << "\"selected_world_position_pre_call_required\":true,"
            << "\"returned_cache_handle_typed\":true,"
            << "\"complete_fun_00765c40_internalized\":false,"
            << "\"collision_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
