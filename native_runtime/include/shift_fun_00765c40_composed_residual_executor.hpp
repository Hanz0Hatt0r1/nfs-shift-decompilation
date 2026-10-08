#pragma once

#include "shift_fun_007584f0_persistent_write_stage.hpp"
#include "shift_fun_00765c40_bounded_state_tail.hpp"
#include "shift_fun_00765c40_contact_array_sweep_stage.hpp"
#include "shift_fun_00765c40_contact_body_accumulation.hpp"
#include "shift_fun_00765c40_optional_body_accumulator_sweep.hpp"
#include "shift_fun_00765c40_residual_pass_contract.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"
#include "shift_fun_00765c40_selected_bmw_world_position.hpp"
#include "shift_fun_00765c40_wheel_job_scheduling.hpp"
#include "shift_fun_00765c40_wheel_pair_refresh_stage.hpp"
#include "shift_fun_00765c40_wheel_plane_refresh_stage.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ComposedResidualExecutorFormat =
    "SHIFT.Fun00765c40ComposedResidualExecutor/1";

struct Fun00765c40ComposedResidualInputs {
    Fun00765c40WheelPlaneRefreshComputedInputs wheel_plane{};
    std::vector<std::uint8_t> current_body_bytes{};
    std::optional<std::uint64_t> cached_query_handle{};
    std::uint64_t wheel_state_source_bits = 0u;
    Fun00765c40WheelJobQueueExecutor execute_wheel_job_queue{};
    Fun00765c40LoadTermReader read_load_term{};
    Fun007584f0ComputedInputs persistent_write{};
    Fun00765c40WheelPairComputedInputs wheel_pair{};
    Fun00765c40ContactArrayComputedInputs contact_array{};
    BodyAccumulatorState initial_body{};
    Fun00765c40ContactBodyAccumulationEntries contact_body_entries{};
    Fun00765c40BoundedStateTailComputedInputs bounded_state_tail{};
    Fun00765c40OptionalBodyAccumulatorSweepInput optional_body_sweep{};
};

struct Fun00765c40ComposedResidualResult {
    Fun00765c40WheelPlaneRefreshState wheel_plane{};
    Fun00765c40SelectedBmwWorldPositionResult selected_world_position{};
    Fun00765c40QueryCommit query_commit{};
    std::array<Fun00765c40WheelStateAssignment, kFun00765c40WheelCount>
        wheel_state_assignments{};
    Fun00765c40WheelJobSchedulingResult wheel_job{};
    Fun007584f0PersistentWriteState persistent_write{};
    std::uint32_t positive_load_count = 0u;
    Fun00765c40WheelPairRefreshState wheel_pair{};
    Fun00765c40ContactArraySweepState contact_array{};
    Fun00765c40ContactBodyAccumulationResult contact_body{};
    std::optional<Fun00765c40BoundedStateTailCommit> bounded_state_tail{};
    Fun00765c40OptionalBodyAccumulatorSweepResult optional_body_sweep{};
    std::array<Fun00765c40ResidualStage, 11> executed_stage_order{};
};

inline Fun00765c40ComposedResidualResult
execute_fun_00765c40_composed_residual_pass(
    const Fun00765c40ComposedResidualInputs& inputs,
    const Fun00765c40SceneQueryProvider& scene_query_provider) {
    Fun00765c40ComposedResidualResult result{};
    result.executed_stage_order = kFun00765c40ResidualStageOrder;
    result.wheel_plane = materialize_fun_00765c40_wheel_plane_refresh_stage(inputs.wheel_plane);
    result.selected_world_position = execute_fun_00765c40_selected_bmw_world_position(inputs.current_body_bytes);

    Fun00765c40SceneQueryBoundary query_boundary{};
    query_boundary.query_input.world_position = result.selected_world_position.world_transform.world_position;
    query_boundary.query_input.cached_handle = inputs.cached_query_handle;
    query_boundary.query_input.miss_fallback = selected_bmw_m3_e36_fun_00765c40_query_fallback();
    result.query_commit = execute_fun_00765c40_scene_query_stage(query_boundary, scene_query_provider);

    for (std::size_t wheel = 0; wheel < kFun00765c40WheelCount; ++wheel) {
        result.wheel_state_assignments[wheel] = materialize_fun_00752fa0_wheel_state_assignment(wheel, inputs.wheel_state_source_bits);
    }
    result.wheel_job = execute_fun_00765c40_wheel_job_scheduling(inputs.execute_wheel_job_queue, inputs.read_load_term);
    result.persistent_write = materialize_fun_007584f0_persistent_write_stage(result.wheel_job.load_terms, inputs.persistent_write);
    result.positive_load_count = fun_00765c40_positive_load_term_count(result.wheel_job.load_terms);
    result.wheel_pair = materialize_fun_00765c40_wheel_pair_refresh_stage(inputs.wheel_pair);
    result.contact_array = materialize_fun_00765c40_contact_array_sweep_stage(inputs.contact_array);
    result.contact_body = execute_fun_00765c40_contact_body_accumulation(inputs.initial_body, inputs.contact_body_entries);
    result.bounded_state_tail = materialize_fun_00765c40_bounded_state_tail(inputs.bounded_state_tail);
    result.optional_body_sweep = execute_fun_00765c40_optional_body_accumulator_sweep(result.contact_body.body, inputs.optional_body_sweep);
    return result;
}

inline constexpr bool fun_00765c40_composed_executor_matches_residual_order() {
    return kFun00765c40ResidualStageOrder.size() == 11u &&
           kFun00765c40ResidualStageOrder.front() == Fun00765c40ResidualStage::WheelPlaneStateRefresh &&
           kFun00765c40ResidualStageOrder.back() == Fun00765c40ResidualStage::OptionalBodyAccumulatorSweep;
}

static_assert(fun_00765c40_composed_executor_matches_residual_order());

}  // namespace shift::runtime::physics
