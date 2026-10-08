#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <cstddef>
#include <functional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40WheelJobSchedulingFormat =
    "SHIFT.Fun00765c40WheelJobScheduling/1";
inline constexpr std::size_t kFun00765c40WheelJobQueueOffset = 0x6730u;
inline constexpr std::uintptr_t kFun00765c40WheelJobEntry = 0x0075cfb0u;
inline constexpr std::size_t kFun00765c40WheelJobVirtualSlot = 0x04u;

using Fun00765c40WheelJobQueueExecutor = std::function<void()>;
using Fun00765c40LoadTermReader = std::function<double(std::size_t)>;

struct Fun00765c40WheelJobSchedulingResult {
    Fun00765c40LoadTerms load_terms{};
    bool queue_executed = false;
    std::size_t load_term_read_count = 0u;
};

// Process 1 proves that the registered wheel-job queue at HDVehicle+0x6730
// executes before FUN_00765c40 consumes the four +0x738 load terms. The
// internals of FUN_0075cfb0 and the scheduler argument semantics remain
// outside the current native proof. Keep queue execution and post-queue field
// access as explicit seams while owning their retail order here.
inline Fun00765c40WheelJobSchedulingResult
execute_fun_00765c40_wheel_job_scheduling(
    const Fun00765c40WheelJobQueueExecutor& execute_queue,
    const Fun00765c40LoadTermReader& read_load_term) {
    if (!execute_queue) {
        throw std::invalid_argument(
            "FUN_00765c40 wheel-job scheduling requires an explicit queue executor");
    }
    if (!read_load_term) {
        throw std::invalid_argument(
            "FUN_00765c40 wheel-job scheduling requires an explicit load-term reader");
    }

    Fun00765c40WheelJobSchedulingResult result{};
    execute_queue();
    result.queue_executed = true;

    for (std::size_t wheel = 0; wheel < kFun00765c40WheelCount; ++wheel) {
        result.load_terms[wheel] = read_load_term(wheel);
        ++result.load_term_read_count;
    }
    validate_fun_00765c40_load_terms(result.load_terms);
    return result;
}

inline constexpr bool fun_00765c40_wheel_job_stage_precedes_persistent_mutation() {
    return kFun00765c40ResidualStageOrder[5] ==
               Fun00765c40ResidualStage::WheelJobQueueExecution &&
           kFun00765c40ResidualStageOrder[6] ==
               Fun00765c40ResidualStage::Fun007584f0PersistentMutation;
}

static_assert(kFun00765c40WheelCount == 4u);
static_assert(kFun00765c40WheelJobQueueOffset == 0x6730u);
static_assert(kFun00765c40WheelJobEntry == 0x0075cfb0u);
static_assert(kFun00765c40WheelJobVirtualSlot == 0x04u);
static_assert(fun_00765c40_wheel_job_stage_precedes_persistent_mutation());

}  // namespace shift::runtime::physics
