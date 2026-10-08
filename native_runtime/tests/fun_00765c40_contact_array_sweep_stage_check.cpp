#include "shift_fun_00765c40_contact_array_sweep_stage.hpp"

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
        require(kFun00765c40ContactArraySlotCount == 12u,
                "FUN_00765c40 contact slot count drift");
        require(kFun00765c40ContactRecordPointerOffsets.front() == 0x35c8u &&
                    kFun00765c40ContactRecordPointerOffsets.back() == 0x35f4u,
                "FUN_00765c40 contact pointer range drift");
        require(kFun00765c40ContactScalarOffsets.front() == 0x35f8u &&
                    kFun00765c40ContactScalarOffsets.back() == 0x3650u,
                "FUN_00765c40 contact scalar range drift");
        require(fun_00765c40_contact_sweep_follows_wheel_pair_refresh(),
                "FUN_00765c40 contact sweep schedule drift");

        Fun00765c40ContactArrayComputedInputs computed{};
        for (std::size_t slot = 0; slot < kFun00765c40ContactArraySlotCount; ++slot) {
            computed.record_pointer_tokens[slot] =
                static_cast<std::uint32_t>(0x1000u + slot * 0x20u);
            computed.scalar_qword_bits[slot] =
                0x3ff0000000000000ULL + static_cast<std::uint64_t>(slot);
        }

        const auto state =
            materialize_fun_00765c40_contact_array_sweep_stage(computed);
        require(state.record_pointer_tokens == computed.record_pointer_tokens,
                "FUN_00765c40 contact pointer tokens must be preserved exactly");
        require(state.scalar_qword_bits == computed.scalar_qword_bits,
                "FUN_00765c40 contact scalar qwords must be preserved exactly");

        std::cout
            << "{\"format\":\"" << kFun00765c40ContactArraySweepStageFormat << "\","
            << "\"ready\":true,"
            << "\"slot_count\":12,"
            << "\"pointer_payloads_bit_preserved\":true,"
            << "\"scalar_payloads_bit_preserved\":true,"
            << "\"producer_arithmetic_internalized\":false,"
            << "\"bounded_state_tail_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
