#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40LoadTermsFormat =
    "SHIFT.Fun00765c40LoadTerms/1";
inline constexpr std::size_t kFun00765c40WheelCount = 4u;
inline constexpr std::size_t kFun00765c40WheelArrayOffset = 0x400u;
inline constexpr std::size_t kFun00765c40WheelStride = 0xa80u;
inline constexpr std::size_t kFun00765c40WheelLoadFieldOffset = 0x738u;
inline constexpr std::array<std::size_t, kFun00765c40WheelCount>
    kFun00765c40HDVehicleLoadTermOffsets{
        0xb38u,
        0x15b8u,
        0x2038u,
        0x2ab8u,
    };

using Fun00765c40LoadTerms =
    std::array<double, kFun00765c40WheelCount>;

inline void validate_fun_00765c40_load_terms(
    const Fun00765c40LoadTerms& load_terms) {
    for (double value : load_terms) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00765c40 load-term provider returned a non-finite value");
        }
    }
}

}  // namespace shift::runtime::physics
