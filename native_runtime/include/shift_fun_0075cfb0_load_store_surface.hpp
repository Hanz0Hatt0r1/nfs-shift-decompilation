#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun0075cfb0LoadStoreSurfaceFormat =
    "SHIFT.Fun0075cfb0LoadStoreSurface/1";

inline constexpr std::uintptr_t kFun0075cfb0Entry = 0x0075cfb0u;
inline constexpr std::size_t kFun0075cfb0WheelCount = 4u;
inline constexpr std::size_t kFun0075cfb0WheelArrayBaseOffset = 0x0400u;
inline constexpr std::size_t kFun0075cfb0WheelStride = 0x0a80u;
inline constexpr std::size_t kFun0075cfb0WheelLoadFieldOffset = 0x0738u;

inline constexpr std::array<std::size_t, kFun0075cfb0WheelCount>
    kFun0075cfb0WheelLoadHDVehicleOffsets = {
        0x0b38u,
        0x15b8u,
        0x2038u,
        0x2ab8u,
    };

enum class Fun0075cfb0LoadStoreSite : std::uint8_t {
    EntryInitialization = 0,
    RuntimePrimary,
    RuntimeAlternate,
};

inline constexpr std::array<std::uintptr_t, 3>
    kFun0075cfb0LoadStoreSites = {
        0x0075d001u,
        0x0075ff25u,
        0x0075ff3eu,
    };

struct Fun0075cfb0LoadStoreComputedInput {
    // Source arithmetic is not yet internalized. Keep the computed f64 payload
    // as exact qword bits so Process 2 does not invent numeric semantics.
    std::uint64_t qword_bits = 0u;
};

struct Fun0075cfb0LoadStoreCommit {
    Fun0075cfb0LoadStoreSite site = Fun0075cfb0LoadStoreSite::EntryInitialization;
    std::size_t wheel_index = 0u;
    std::size_t wheel_relative_offset = kFun0075cfb0WheelLoadFieldOffset;
    std::size_t hdvehicle_offset = kFun0075cfb0WheelLoadHDVehicleOffsets[0];
    std::uint64_t qword_bits = 0u;
};

inline constexpr std::uintptr_t fun_0075cfb0_load_store_site_address(
    Fun0075cfb0LoadStoreSite site) {
    return kFun0075cfb0LoadStoreSites[static_cast<std::size_t>(site)];
}

inline Fun0075cfb0LoadStoreCommit materialize_fun_0075cfb0_load_store_commit(
    Fun0075cfb0LoadStoreSite site,
    std::size_t wheel_index,
    const Fun0075cfb0LoadStoreComputedInput& computed) {
    const std::size_t site_index = static_cast<std::size_t>(site);
    if (site_index >= kFun0075cfb0LoadStoreSites.size()) {
        throw std::out_of_range("FUN_0075cfb0 load-store site is outside recovered store surface");
    }
    if (wheel_index >= kFun0075cfb0WheelCount) {
        throw std::out_of_range("FUN_0075cfb0 wheel index exceeds recovered four-wheel domain");
    }

    return {
        site,
        wheel_index,
        kFun0075cfb0WheelLoadFieldOffset,
        kFun0075cfb0WheelLoadHDVehicleOffsets[wheel_index],
        computed.qword_bits,
    };
}

static_assert(kFun0075cfb0Entry == 0x0075cfb0u);
static_assert(kFun0075cfb0WheelLoadHDVehicleOffsets[0] == 0x0b38u);
static_assert(kFun0075cfb0WheelLoadHDVehicleOffsets[3] == 0x2ab8u);
static_assert(kFun0075cfb0LoadStoreSites[0] == 0x0075d001u);
static_assert(kFun0075cfb0LoadStoreSites[1] == 0x0075ff25u);
static_assert(kFun0075cfb0LoadStoreSites[2] == 0x0075ff3eu);

}  // namespace shift::runtime::physics
