#include "shift_fun_00765c40_bounded_state_tail.hpp"

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
        Fun00765c40BoundedStateTailComputedInputs skipped{};
        require(!materialize_fun_00765c40_bounded_state_tail(skipped).has_value(),
                "FUN_00765c40 bounded state tail must preserve skipped branch");

        Fun00765c40BoundedStateTailComputedInputs executed{};
        executed.write_block_executed = true;
        executed.state_3668_bits = 0x0123456789abcdefULL;
        executed.state_3670_bits = 0xfedcba9876543210ULL;
        executed.state_3678_bits = 0x89abcdefU;

        const auto commit = materialize_fun_00765c40_bounded_state_tail(executed);
        require(commit.has_value(),
                "FUN_00765c40 bounded state tail must materialize executed branch");
        require(commit->flag_3660 == 1u,
                "FUN_00765c40 +0x3660 literal flag drift");
        require(commit->state_3668_bits == executed.state_3668_bits,
                "FUN_00765c40 +0x3668 qword payload drift");
        require(commit->state_3670_bits == executed.state_3670_bits,
                "FUN_00765c40 +0x3670 qword payload drift");
        require(commit->state_3678_bits == executed.state_3678_bits,
                "FUN_00765c40 +0x3678 dword payload drift");

        std::cout
            << "{\"format\":\"" << kFun00765c40BoundedStateTailFormat << "\","
            << "\"ready\":true,"
            << "\"skipped_branch_preserved\":true,"
            << "\"flag_literal\":1,"
            << "\"computed_payloads_bit_preserved\":true,"
            << "\"branch_predicate_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
