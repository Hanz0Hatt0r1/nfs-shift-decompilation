#pragma once

#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ContactArraySweepStageFormat =
    "SHIFT.Fun00765c40ContactArraySweepStage/1";

inline constexpr std::size_t kFun00765c40ContactArraySlotCount =
    kFun00765c40ContactRecordPointerCount;

static_assert(
    kFun00765c40ContactRecordPointerCount == kFun00765c40ContactScalarCount);

inline constexpr std::array<std::size_t, kFun00765c40ContactArraySlotCount>
make_fun_00765c40_contact_record_pointer_offsets() {
    std::array<std::size_t, kFun00765c40ContactArraySlotCount> offsets{};
    for (std::size_t slot = 0; slot < offsets.size(); ++slot) {
        offsets[slot] = kFun00765c40ContactRecordPointerArrayOffset +
                        slot * kFun00765c40ContactRecordPointerStride;
    }
    return offsets;
}

inline constexpr std::array<std::size_t, kFun00765c40ContactArraySlotCount>
make_fun_00765c40_contact_scalar_offsets() {
    std::array<std::size_t, kFun00765c40ContactArraySlotCount> offsets{};
    for (std::size_t slot = 0; slot < offsets.size(); ++slot) {
        offsets[slot] = kFun00765c40ContactScalarArrayOffset +
                        slot * kFun00765c40ContactScalarStride;
    }
    return offsets;
}

inline constexpr auto kFun00765c40ContactRecordPointerOffsets =
    make_fun_00765c40_contact_record_pointer_offsets();
inline constexpr auto kFun00765c40ContactScalarOffsets =
    make_fun_00765c40_contact_scalar_offsets();

// The source-visible stores are proven, but the per-slot producer arithmetic
// is not yet closed for native reconstruction. Keep both payload families
// opaque and exact-width: dword record/result token plus qword scalar bits.
struct Fun00765c40ContactArrayComputedInputs {
    std::array<std::uint32_t, kFun00765c40ContactArraySlotCount>
        record_pointer_tokens{};
    std::array<std::uint64_t, kFun00765c40ContactArraySlotCount>
        scalar_qword_bits{};
};

struct Fun00765c40ContactArraySweepState {
    std::array<std::uint32_t, kFun00765c40ContactArraySlotCount>
        record_pointer_tokens{};
    std::array<std::uint64_t, kFun00765c40ContactArraySlotCount>
        scalar_qword_bits{};
};

inline Fun00765c40ContactArraySweepState
materialize_fun_00765c40_contact_array_sweep_stage(
    const Fun00765c40ContactArrayComputedInputs& computed) {
    return {computed.record_pointer_tokens, computed.scalar_qword_bits};
}

inline constexpr bool fun_00765c40_contact_sweep_follows_wheel_pair_refresh() {
    return kFun00765c40ResidualStageOrder[8] ==
               Fun00765c40ResidualStage::WheelPairStateRefresh &&
           kFun00765c40ResidualStageOrder[9] ==
               Fun00765c40ResidualStage::ContactArraySweep;
}

static_assert(fun_00765c40_contact_sweep_follows_wheel_pair_refresh());
static_assert(kFun00765c40ContactRecordPointerOffsets.front() == 0x35c8u);
static_assert(kFun00765c40ContactRecordPointerOffsets.back() == 0x35f4u);
static_assert(kFun00765c40ContactScalarOffsets.front() == 0x35f8u);
static_assert(kFun00765c40ContactScalarOffsets.back() == 0x3650u);

}  // namespace shift::runtime::physics
