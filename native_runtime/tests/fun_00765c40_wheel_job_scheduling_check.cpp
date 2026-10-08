#include "shift_fun_0075cfb0_load_store_surface.hpp"
#include "shift_fun_00765c40_wheel_job_scheduling.hpp"

#include <array>
#include <cmath>
#include <cstdint>
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

        constexpr std::array<std::uint64_t, 4> opaque_payloads = {
            0x7ff8000000000001ull,
            0x0000000000000000ull,
            0x3ff0000000000000ull,
            0xffffffffffffffffull,
        };
        constexpr std::array<Fun0075cfb0LoadStoreSite, 3> store_sites = {
            Fun0075cfb0LoadStoreSite::EntryInitialization,
            Fun0075cfb0LoadStoreSite::RuntimePrimary,
            Fun0075cfb0LoadStoreSite::RuntimeAlternate,
        };
        for (std::size_t wheel = 0u; wheel < opaque_payloads.size(); ++wheel) {
            for (const auto site : store_sites) {
                const auto commit = materialize_fun_0075cfb0_load_store_commit(
                    site,
                    wheel,
                    Fun0075cfb0LoadStoreComputedInput{opaque_payloads[wheel]});
                require(commit.wheel_index == wheel &&
                            commit.wheel_relative_offset == 0x738u &&
                            commit.hdvehicle_offset ==
                                kFun0075cfb0WheelLoadHDVehicleOffsets[wheel],
                        "FUN_0075cfb0 load-store destination drift");
                require(commit.qword_bits == opaque_payloads[wheel],
                        "FUN_0075cfb0 opaque payload was not preserved bit-for-bit");
                require(fun_0075cfb0_load_store_site_address(site) ==
                            kFun0075cfb0LoadStoreSites[static_cast<std::size_t>(site)],
                        "FUN_0075cfb0 store-site address drift");
            }
        }

        bool rejected_bad_wheel = false;
        try {
            (void)materialize_fun_0075cfb0_load_store_commit(
                Fun0075cfb0LoadStoreSite::RuntimePrimary,
                4u,
                Fun0075cfb0LoadStoreComputedInput{});
        } catch (const std::out_of_range&) {
            rejected_bad_wheel = true;
        }
        require(rejected_bad_wheel,
                "FUN_0075cfb0 invalid load-store wheel failed open");

        bool rejected_bad_store_site = false;
        try {
            (void)materialize_fun_0075cfb0_load_store_commit(
                static_cast<Fun0075cfb0LoadStoreSite>(3u),
                0u,
                Fun0075cfb0LoadStoreComputedInput{});
        } catch (const std::out_of_range&) {
            rejected_bad_store_site = true;
        }
        require(rejected_bad_store_site,
                "FUN_0075cfb0 invalid load-store site failed open");

        std::cout
            << "{\"format\":\"" << kFun00765c40WheelJobSchedulingFormat << "\","
            << "\"ready\":true,"
            << "\"queue_executes_before_reads\":true,"
            << "\"queue_call_count\":1,"
            << "\"load_term_read_count\":4,"
            << "\"load_store_surface_format\":\""
            << kFun0075cfb0LoadStoreSurfaceFormat << "\","
            << "\"load_store_site_count\":3,"
            << "\"load_store_payload_bit_preserved\":true,"
            << "\"wheel_job_formula_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
