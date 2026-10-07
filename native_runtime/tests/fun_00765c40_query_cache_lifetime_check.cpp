#include "shift_collision_query_contract.hpp"
#include "shift_fun_00765c40_external_pass_result.hpp"

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

}  // namespace

int main() {
    try {
        require(kCollisionCallerHandleOffset == 0x38dcu,
                "FUN_00765c40 caller cache offset drift");

        Fun00765c40ExternalPassInput first_input{};
        require(!first_input.cached_handle.has_value(),
                "FUN_00765c40 cache input did not default to retail zero seed");

        Fun00765c40QueryInputBoundary first_query{};
        first_query.world_position = {1.0, 2.0, 3.0};
        first_query.cached_handle = first_input.cached_handle;
        first_query.miss_fallback = 4.0;
        const Fun00765c40ExternalPassResult first_result{
            Fun00765c40LoadTerms{10.0, 20.0, 30.0, 40.0},
            first_query,
            std::uint64_t{0x1234u}};
        validate_fun_00765c40_external_pass_result(first_input, first_result);
        require(first_result.returned_cache_handle == 0x1234u,
                "FUN_00765c40 returned cache handle was not preserved");

        Fun00765c40ExternalPassInput second_input{};
        second_input.cached_handle = first_result.returned_cache_handle;
        Fun00765c40QueryInputBoundary second_query{};
        second_query.world_position = {5.0, 6.0, 7.0};
        second_query.cached_handle = second_input.cached_handle;
        second_query.miss_fallback = 8.0;
        const Fun00765c40ExternalPassResult second_result{
            Fun00765c40LoadTerms{11.0, 21.0, 31.0, 41.0},
            second_query,
            std::uint64_t{0x5678u}};
        validate_fun_00765c40_external_pass_result(second_input, second_result);
        require(second_input.cached_handle == 0x1234u &&
                    second_result.returned_cache_handle == 0x5678u,
                "FUN_00765c40 pass-to-pass cache handoff drift");

        bool wrong_cache_rejected = false;
        try {
            auto invalid = second_result;
            invalid.query_input.cached_handle = 0x9999u;
            validate_fun_00765c40_external_pass_result(second_input, invalid);
        } catch (const std::invalid_argument&) {
            wrong_cache_rejected = true;
        }
        require(wrong_cache_rejected,
                "FUN_00765c40 residual provider accepted a non-owned cached handle");

        bool wrong_world_position_rejected = false;
        try {
            auto owned_input = second_input;
            owned_input.world_position = CollisionQueryVector3d{5.0, 6.0, 7.0};
            auto invalid = second_result;
            invalid.query_input.world_position = {5.0, 6.0, 8.0};
            validate_fun_00765c40_external_pass_result(owned_input, invalid);
        } catch (const std::invalid_argument&) {
            wrong_world_position_rejected = true;
        }
        require(wrong_world_position_rejected,
                "FUN_00765c40 residual provider accepted a non-owned BMW world position");

        std::cout
            << "{\"format\":\"SHIFT.Fun00765c40QueryCacheLifetime/1\","
            << "\"ready\":true,"
            << "\"caller_offset\":\"0x38dc\","
            << "\"zero_seed\":true,"
            << "\"pass_to_pass_handoff\":true,"
            << "\"provider_must_consume_owned_cache\":true,"
            << "\"collision_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
