#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40SelectedBmwQueryFallbackFormat =
    "SHIFT.Fun00765c40SelectedBMWQueryFallback/1";

inline constexpr std::size_t kFun00756bb0CallerCacheOffset = 0x38dcu;
inline constexpr std::size_t kFun00756bb0CallerFallbackOffset = 0x38e8u;
inline constexpr std::size_t kFun00756bb0FrontWingRecordOffset = 0x6a0u;
inline constexpr std::size_t kFun00756bb0FWMaxHeightBaseOffset = 0x6a4u;
inline constexpr std::size_t kFun00756bb0FWMaxHeightEvaluatedOffset = 0x6a8u;

// BMW M3 E36 retail CDF FRONTWING.FWMaxHeight=(0.10). The ordinary text
// parser stores the scalar as f32 at VehicleLoadData+0x6a4. FUN_00756bb0 calls
// FUN_007a6be0, explicitly spills the result to f32 at +0x6a8, then widens that
// exact f32 into the caller f64 slot +0x38e8.
inline constexpr std::uint32_t kBmwM3E36FWMaxHeightF32Bits = 0x3dcccccdu;
inline constexpr std::uint64_t kBmwM3E36QueryFallbackF64Bits =
    0x3fb99999a0000000ull;

inline double selected_bmw_m3_e36_fun_00765c40_query_fallback() {
    float parsed = 0.0f;
    const std::uint32_t source_bits = kBmwM3E36FWMaxHeightF32Bits;
    std::memcpy(&parsed, &source_bits, sizeof(parsed));
    const double widened = static_cast<double>(parsed);

    std::uint64_t widened_bits = 0u;
    std::memcpy(&widened_bits, &widened, sizeof(widened_bits));
    if (widened_bits != kBmwM3E36QueryFallbackF64Bits) {
        throw std::logic_error(
            "BMW M3 E36 FUN_00765c40 query fallback precision drift");
    }
    return widened;
}

}  // namespace shift::runtime::physics
