#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00769640TrigSourceWriterFormat =
    "SHIFT.Fun00769640TrigSourceWriter/1";

inline constexpr std::uintptr_t kFun00769640TrigWriterSpanStart = 0x00769c05u;
inline constexpr std::uintptr_t kFun00769640TrigWriterSpanEnd = 0x00769c2du;
inline constexpr std::size_t kFun00769640TableRootOffset = 0x4330u;
inline constexpr std::size_t kFun00769640TableRecordBaseOffset = 0x0dc8u;
inline constexpr std::size_t kFun00769640TableCoefficientOffset = 0x0ddcu;
inline constexpr std::size_t kFun00769640TableRecordStride = 0x0050u;
inline constexpr std::array<std::size_t, 2> kFun00769640SelectedRecordIndices{
    12u,
    13u,
};
inline constexpr std::array<std::size_t, 2> kFun00769640TrigDestinationOffsets{
    0x0738u,
    0x11b8u,
};
inline constexpr std::array<std::size_t, 2> kFun00769640TableBaseValueOffsets{
    0x54b8u,
    0x5508u,
};
inline constexpr std::array<std::size_t, 2> kFun00769640TableSlopeValueOffsets{
    0x54c0u,
    0x5510u,
};
inline constexpr std::array<std::size_t, 2> kFun00769640TableCoefficientAbsoluteOffsets{
    0x54ccu,
    0x551cu,
};

struct Fun00769640TrigSourceWriterInput {
    double base_value = 0.0;
    double slope_value = 0.0;
    std::int32_t coefficient = 0;
};

inline double execute_fun_00769640_trig_source_writer(
    const Fun00769640TrigSourceWriterInput& input) {
    if (!std::isfinite(input.base_value) || !std::isfinite(input.slope_value)) {
        throw std::invalid_argument(
            "FUN_00769640 trig source writer requires finite qword inputs");
    }

    // Retail 0x00769c14..0x00769c27 performs FILD int32, FMUL qword,
    // FADD qword and FST qword. Preserve the proven mathematical order while
    // leaving exact ambient-x87 excess-precision parity outside this contract.
    const double result =
        static_cast<double>(input.coefficient) * input.slope_value +
        input.base_value;
    if (!std::isfinite(result)) {
        throw std::invalid_argument(
            "FUN_00769640 trig source writer result must be finite");
    }
    return result;
}

inline constexpr std::size_t fun_00769640_record_base_value_offset(
    std::size_t loop_index) {
    return kFun00769640TableRootOffset + kFun00769640TableRecordBaseOffset +
           kFun00769640SelectedRecordIndices[loop_index] *
               kFun00769640TableRecordStride;
}

inline constexpr std::size_t fun_00769640_record_slope_value_offset(
    std::size_t loop_index) {
    return fun_00769640_record_base_value_offset(loop_index) + 0x08u;
}

inline constexpr std::size_t fun_00769640_record_coefficient_offset(
    std::size_t loop_index) {
    return kFun00769640TableRootOffset + kFun00769640TableCoefficientOffset +
           kFun00769640SelectedRecordIndices[loop_index] *
               kFun00769640TableRecordStride;
}

static_assert(kFun00769640TrigWriterSpanStart == 0x00769c05u);
static_assert(kFun00769640TrigWriterSpanEnd == 0x00769c2du);
static_assert(fun_00769640_record_base_value_offset(0u) == 0x54b8u);
static_assert(fun_00769640_record_base_value_offset(1u) == 0x5508u);
static_assert(fun_00769640_record_slope_value_offset(0u) == 0x54c0u);
static_assert(fun_00769640_record_slope_value_offset(1u) == 0x5510u);
static_assert(fun_00769640_record_coefficient_offset(0u) == 0x54ccu);
static_assert(fun_00769640_record_coefficient_offset(1u) == 0x551cu);

}  // namespace shift::runtime::physics
