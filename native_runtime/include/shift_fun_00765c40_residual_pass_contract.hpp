#pragma once

#include "shift_fun_00765c40_external_pass_result.hpp"
#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ResidualPassContractFormat =
    "SHIFT.Fun00765c40ResidualPassContract/1";

// P1.2 proves that the lower collision implementation remains external at the
// global provider pointer 0x00c133ac and vtable slot +0x1c0.  P2.4 must not
// replace that boundary with a guessed track/scene query.
inline constexpr std::uintptr_t kFun00765c40SceneQueryProviderGlobal =
    0x00c133acu;
inline constexpr std::size_t kFun00765c40SceneQueryVtableSlot = 0x1c0u;
inline constexpr std::size_t kFun00765c40SurfaceRecordStride = 0x58u;

inline constexpr std::size_t kFun00765c40WheelStateIndexOffset = 0x9f8u;
inline constexpr std::size_t kFun00765c40WheelStateSourceOffset = 0xa00u;
inline constexpr std::size_t kFun00765c40WheelStateSourceHDVehicleOffset = 0x98u;
inline constexpr std::size_t kFun00765c40LoadPositiveCountOffset = 0x407cu;

inline constexpr std::array<std::size_t, 4>
    kFun00765c40WheelLoopAOffsets = {
        0x0a70u, 0x14f0u, 0x1f70u, 0x29f0u,
    };
inline constexpr std::array<std::size_t, 8>
    kFun00765c40WheelPairLoopBOffsets = {
        0x0ba0u, 0x0ba8u,
        0x1620u, 0x1628u,
        0x20a0u, 0x20a8u,
        0x2b20u, 0x2b28u,
    };
inline constexpr std::size_t kFun00765c40ContactRecordPointerArrayOffset = 0x35c8u;
inline constexpr std::size_t kFun00765c40ContactRecordPointerCount = 12u;
inline constexpr std::size_t kFun00765c40ContactRecordPointerStride = 0x04u;
inline constexpr std::size_t kFun00765c40ContactScalarArrayOffset = 0x35f8u;
inline constexpr std::size_t kFun00765c40ContactScalarCount = 12u;
inline constexpr std::size_t kFun00765c40ContactScalarStride = 0x08u;
inline constexpr std::size_t kFun00765c40ContactNegativeFlagOffset = 0x3660u;
inline constexpr std::size_t kFun00765c40PeakStateOffset = 0x3668u;
inline constexpr std::size_t kFun00765c40PeakAuxOffset = 0x3670u;
inline constexpr std::size_t kFun00765c40PeakTagOffset = 0x3678u;
inline constexpr std::array<std::size_t, 3>
    kFun007584f0PersistentWriteOffsets = {0x0d40u, 0x17c0u, 0x3420u};

enum class Fun00765c40ResidualStage : std::uint8_t {
    WheelPlaneStateRefresh = 0,
    SelectedWorldPositionTransform,
    SceneQuery,
    QueryCacheAndScalarCommit,
    WheelStateIndexSourceCommit,
    WheelJobQueueExecution,
    Fun007584f0PersistentMutation,
    PositiveLoadCountCommit,
    WheelPairStateRefresh,
    ContactArraySweep,
    OptionalBodyAccumulatorSweep,
};

inline constexpr std::array<Fun00765c40ResidualStage, 11>
    kFun00765c40ResidualStageOrder = {
        Fun00765c40ResidualStage::WheelPlaneStateRefresh,
        Fun00765c40ResidualStage::SelectedWorldPositionTransform,
        Fun00765c40ResidualStage::SceneQuery,
        Fun00765c40ResidualStage::QueryCacheAndScalarCommit,
        Fun00765c40ResidualStage::WheelStateIndexSourceCommit,
        Fun00765c40ResidualStage::WheelJobQueueExecution,
        Fun00765c40ResidualStage::Fun007584f0PersistentMutation,
        Fun00765c40ResidualStage::PositiveLoadCountCommit,
        Fun00765c40ResidualStage::WheelPairStateRefresh,
        Fun00765c40ResidualStage::ContactArraySweep,
        Fun00765c40ResidualStage::OptionalBodyAccumulatorSweep,
    };

struct Fun00765c40WheelStateAssignment {
    std::uint32_t index = 0u;
    std::uint64_t source_bits = 0u;
};

inline Fun00765c40WheelStateAssignment
materialize_fun_00752fa0_wheel_state_assignment(
    std::size_t wheel_index,
    std::uint64_t hdvehicle_source_bits) {
    if (wheel_index >= kFun00765c40WheelCount) {
        throw std::invalid_argument(
            "FUN_00752fa0 wheel index exceeds recovered four-wheel domain");
    }
    return {
        static_cast<std::uint32_t>(wheel_index),
        hdvehicle_source_bits,
    };
}

inline std::uint32_t fun_00765c40_positive_load_term_count(
    const Fun00765c40LoadTerms& load_terms) {
    validate_fun_00765c40_load_terms(load_terms);
    std::uint32_t count = 0u;
    for (const double value : load_terms) {
        if (value > 0.0) {
            ++count;
        }
    }
    return count;
}

struct Fun00765c40SceneQueryBoundary {
    static constexpr std::uintptr_t provider_global =
        kFun00765c40SceneQueryProviderGlobal;
    static constexpr std::size_t virtual_slot =
        kFun00765c40SceneQueryVtableSlot;
    static constexpr std::size_t returned_record_stride =
        kFun00765c40SurfaceRecordStride;

    Fun00765c40QueryInputBoundary query_input{};
};

inline void validate_fun_00765c40_scene_query_boundary(
    const Fun00765c40SceneQueryBoundary& boundary) {
    validate_fun_00765c40_query_input_boundary(boundary.query_input);
    static_assert(
        Fun00765c40SceneQueryBoundary::provider_global == 0x00c133acu);
    static_assert(
        Fun00765c40SceneQueryBoundary::virtual_slot == 0x1c0u);
    static_assert(
        Fun00765c40SceneQueryBoundary::returned_record_stride == 0x58u);
}

using Fun00765c40SceneQueryProvider =
    std::function<CollisionQueryOutput(const Fun00765c40SceneQueryBoundary&)>;

struct Fun00765c40QueryCommit {
    CollisionQueryOutput output{};
    std::optional<std::uint64_t> cache_handle{};  // HDVehicle+0x38dc
    double projected_scalar = 0.0;                // HDVehicle+0x38e0
};

inline Fun00765c40QueryCommit execute_fun_00765c40_scene_query_stage(
    const Fun00765c40SceneQueryBoundary& boundary,
    const Fun00765c40SceneQueryProvider& provider) {
    validate_fun_00765c40_scene_query_boundary(boundary);
    if (!provider) {
        throw std::invalid_argument(
            "FUN_00765c40 requires the explicit 0x00c133ac/+0x1c0 scene-query boundary");
    }

    auto output = provider(boundary);
    validate_fun_00765c40_collision_output_handoff(
        boundary.query_input,
        output);

    Fun00765c40QueryCommit commit{};
    commit.cache_handle = output.returned_handle;
    commit.projected_scalar = project_fun_00765c40_query_input_scalar(
        boundary.query_input,
        output);
    commit.output = std::move(output);
    return commit;
}

}  // namespace shift::runtime::physics
