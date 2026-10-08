#include "shift_fun_00765c40_wheel_job_scheduling.hpp"

#include <cmath>
#include <iostream>
#include <limits>
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
        require(kFun00765c40WheelJobQueueOffset == 0x6730u,
                "FUN_00765c40 wheel-job queue offset drift");
        require(kFun00765c40WheelJobEntry == 0x0075cfb0u,
                "FUN_00765c40 wheel-job entry drift");
        require(kFun00765c40WheelJobVirtualSlot == 0x04u,
                "FUN_00765c40 wheel-job virtual slot drift");
        require(fun_00765c40_wheel_job_stage_precedes_persistent_mutation(),
                "FUN_00765c40 wheel-job ordering drift");

        bool queue_executed = false;
        std::size_t queue_call_count = 0u;
        std::size_t read_call_count = 0u;
        const Fun00765c40LoadTerms expected{1.0, -2.0, 3.5, 0.0};

        const auto result = execute_fun_00765c40_wheel_job_scheduling(
            [&]() {
                require(!queue_executed,
                        "FUN_00765c40 queue executor called more than once");
                queue_executed = true;
                ++queue_call_count;
            },
            [&](std::size_t wheel) {
                require(queue_executed,
                        "FUN_00765c40 load term read before queue execution");
                require(wheel == read_call_count,
                        "FUN_00765c40 load terms not read in wheel-index order");
                ++read_call_count;
                return expected[wheel];
            });

        require(result.queue_executed && queue_call_count == 1u,
                "FUN_00765c40 wheel-job queue execution count drift");
        require(result.load_term_read_count == 4u && read_call_count == 4u,
                "FUN_00765c40 load-term read count drift");
        require(result.load_terms == expected,
                "FUN_00765c40 load terms changed across scheduling seam");

        bool rejected_missing_queue = false;
        try {
            execute_fun_00765c40_wheel_job_scheduling(
                {}, [](std::size_t) { return 0.0; });
        } catch (const std::invalid_argument&) {
            rejected_missing_queue = true;
        }
        require(rejected_missing_queue,
                "FUN_00765c40 accepted a missing wheel-job queue executor");

        bool rejected_missing_reader = false;
        try {
            execute_fun_00765c40_wheel_job_scheduling([]() {}, {});
        } catch (const std::invalid_argument&) {
            rejected_missing_reader = true;
        }
        require(rejected_missing_reader,
                "FUN_00765c40 accepted a missing load-term reader");

        bool rejected_non_finite = false;
        try {
            execute_fun_00765c40_wheel_job_scheduling(
                []() {},
                [](std::size_t wheel) {
                    return wheel == 2u
                        ? std::numeric_limits<double>::infinity()
                        : 0.0;
                });
        } catch (const std::invalid_argument&) {
            rejected_non_finite = true;
        }
        require(rejected_non_finite,
                "FUN_00765c40 accepted a non-finite post-queue load term");

        std::cout
            << "{\"format\":\"" << kFun00765c40WheelJobSchedulingFormat << "\","
            << "\"ready\":true,"
            << "\"queue_executes_before_reads\":true,"
            << "\"queue_call_count\":1,"
            << "\"load_term_read_count\":4,"
            << "\"wheel_job_formula_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
