#include "runtime_loop_policy.hpp"

#include <chrono>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    using shift::runtime::RuntimeSchedulerAuthority;
    using shift::runtime::make_retail_outer_scheduler_contract;
    using shift::runtime::make_runtime_loop_policy;

    const auto bounded =
        make_runtime_loop_policy(false, false, 120, false, 0);
    if (bounded.continuous || !bounded.frame_limit_enabled ||
        bounded.continuous_wall_clock_pacing || bounded.frame_limit != 120 ||
        !bounded.uses_host_development_scheduler() ||
        bounded.retail_cadence_admitted ||
        bounded.uses_admitted_retail_scheduler() ||
        !bounded.should_continue(false, 119) ||
        bounded.should_continue(false, 120)) {
        std::cerr << "bounded loop policy mismatch\n";
        return 1;
    }

    const auto continuous =
        make_runtime_loop_policy(true, false, 120, false, 0);
    if (!continuous.continuous || continuous.frame_limit_enabled ||
        !continuous.continuous_wall_clock_pacing ||
        continuous.fixed_tick_seconds != shift::runtime::kHostDevelopmentFixedDt ||
        continuous.fixed_tick_seconds != shift::runtime::kNativeContinuousFixedDt ||
        !continuous.uses_host_development_scheduler() ||
        continuous.retail_cadence_admitted ||
        continuous.uses_admitted_retail_scheduler() ||
        !continuous.should_continue(false, 0) ||
        !continuous.should_continue(false, 2000000000) ||
        continuous.should_continue(true, 0)) {
        std::cerr << "continuous loop policy mismatch\n";
        return 1;
    }

    const auto capped =
        make_runtime_loop_policy(true, true, 3, false, 0);
    if (!capped.continuous || !capped.frame_limit_enabled ||
        !capped.continuous_wall_clock_pacing || capped.frame_limit != 3 ||
        !capped.uses_host_development_scheduler() ||
        capped.retail_cadence_admitted ||
        !capped.should_continue(false, 2) || capped.should_continue(false, 3)) {
        std::cerr << "continuous safety-cap policy mismatch\n";
        return 1;
    }

    const auto paced =
        make_runtime_loop_policy(true, true, 3, false, 0);
    const auto pacing_start = std::chrono::steady_clock::now();
    if (!paced.should_continue(false, 0) ||
        !paced.should_continue(false, 1) ||
        !paced.should_continue(false, 2) ||
        paced.should_continue(false, 3)) {
        std::cerr << "continuous pacing iteration mismatch\n";
        return 1;
    }
    const double pacing_elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - pacing_start).count();
    if (pacing_elapsed < 0.020) {
        std::cerr << "continuous pacing did not honor the fixed host tick\n";
        return 1;
    }

    auto forbidden_retail_fallback =
        make_runtime_loop_policy(true, false, 120, false, 0);
    forbidden_retail_fallback.scheduler_authority =
        RuntimeSchedulerAuthority::RetailEvidence;
    forbidden_retail_fallback.retail_cadence_admitted = true;
    bool rejected_retail_host_fallback = false;
    try {
        (void)forbidden_retail_fallback.should_continue(false, 0);
    } catch (const std::logic_error&) {
        rejected_retail_host_fallback = true;
    }
    if (!rejected_retail_host_fallback) {
        std::cerr << "retail cadence silently fell back to host 1/60 pacing\n";
        return 1;
    }

    auto retail_outer = make_retail_outer_scheduler_contract(
        true,
        shift::runtime::kRetailOuterNominalFrequencyHz,
        shift::runtime::kRetailOuterGatePeriodMs,
        shift::runtime::kRetailNormalOuterIncrementSeconds,
        shift::runtime::kRetailSteadySchedulerInvocationsPerDispatch);
    if (!retail_outer.uses_admitted_retail_outer_scheduler() ||
        retail_outer.inner_rate_ready()) {
        std::cerr << "retail outer authority admission mismatch\n";
        return 1;
    }

    bool rejected_missing_loaded_rate = false;
    try {
        (void)retail_outer.inner_substep_seconds();
    } catch (const std::logic_error&) {
        rejected_missing_loaded_rate = true;
    }
    bool rejected_missing_loaded_rate_count = false;
    try {
        (void)retail_outer.ready_inner_substep_count();
    } catch (const std::logic_error&) {
        rejected_missing_loaded_rate_count = true;
    }
    if (!rejected_missing_loaded_rate ||
        !rejected_missing_loaded_rate_count) {
        std::cerr << "constructor/default rate leaked into loaded inner rate\n";
        return 1;
    }

    retail_outer.admit_outer_dispatch();
    if (std::abs(
            retail_outer.pending_accumulator_seconds -
            shift::runtime::kRetailNormalOuterIncrementSeconds) > 1e-12) {
        std::cerr << "retail outer accumulator contribution mismatch\n";
        return 1;
    }

    // Deliberately use an arbitrary explicit loaded rate rather than the retail
    // constructor default. The seam must not infer a selected-session rate.
    retail_outer.admit_loaded_inner_rate(240.0);
    if (!retail_outer.inner_rate_ready() ||
        std::abs(retail_outer.inner_substep_seconds() - (1.0 / 240.0)) > 1e-12) {
        std::cerr << "loaded retail inner-rate admission mismatch\n";
        return 1;
    }
    if (retail_outer.ready_inner_substep_count() != 8) {
        std::cerr << "recovered retail inner substep count mismatch\n";
        return 1;
    }

    const double expected_first_residual =
        shift::runtime::kRetailNormalOuterIncrementSeconds - (8.0 / 240.0);
    retail_outer.commit_ready_inner_substeps(8);
    if (std::abs(
            retail_outer.pending_accumulator_seconds -
            expected_first_residual) > 1e-15 ||
        retail_outer.ready_inner_substep_count() != 0) {
        std::cerr << "retail inner substep commit mismatch\n";
        return 1;
    }

    retail_outer.admit_outer_dispatch();
    const std::size_t second_batch = retail_outer.ready_inner_substep_count();
    bool rejected_partial_batch_commit = false;
    try {
        retail_outer.commit_ready_inner_substeps(second_batch + 1);
    } catch (const std::invalid_argument&) {
        rejected_partial_batch_commit = true;
    }
    if (!rejected_partial_batch_commit) {
        std::cerr << "retail inner scheduler accepted a non-recovered batch count\n";
        return 1;
    }
    retail_outer.commit_ready_inner_substeps(second_batch);

    // A non-30-divisible explicit rate exercises the recovered nearest-step
    // rule and proves that a negative accumulator residual must be preserved.
    auto signed_residual = make_retail_outer_scheduler_contract(
        true,
        shift::runtime::kRetailOuterNominalFrequencyHz,
        shift::runtime::kRetailOuterGatePeriodMs,
        shift::runtime::kRetailNormalOuterIncrementSeconds,
        shift::runtime::kRetailSteadySchedulerInvocationsPerDispatch);
    signed_residual.admit_loaded_inner_rate(50.0);
    signed_residual.admit_outer_dispatch();
    if (signed_residual.ready_inner_substep_count() != 2) {
        std::cerr << "retail nearest-step batch rule mismatch\n";
        return 1;
    }
    signed_residual.commit_ready_inner_substeps(2);
    if (!(signed_residual.pending_accumulator_seconds < 0.0) ||
        signed_residual.ready_inner_substep_count() != 0) {
        std::cerr << "retail signed accumulator residual was clamped or miscounted\n";
        return 1;
    }
    signed_residual.admit_outer_dispatch();
    if (signed_residual.ready_inner_substep_count() != 1) {
        std::cerr << "retail signed residual did not feed the next outer dispatch\n";
        return 1;
    }

    auto expect_bad_rate = [](double rate_hz) {
        auto scheduler = make_retail_outer_scheduler_contract(
            true,
            shift::runtime::kRetailOuterNominalFrequencyHz,
            shift::runtime::kRetailOuterGatePeriodMs,
            shift::runtime::kRetailNormalOuterIncrementSeconds,
            shift::runtime::kRetailSteadySchedulerInvocationsPerDispatch);
        try {
            scheduler.admit_loaded_inner_rate(rate_hz);
        } catch (const std::invalid_argument&) {
            return true;
        }
        return false;
    };
    if (!expect_bad_rate(0.0) ||
        !expect_bad_rate(-1.0) ||
        !expect_bad_rate(240.5) ||
        !expect_bad_rate(65536.0) ||
        !expect_bad_rate(std::numeric_limits<double>::infinity())) {
        std::cerr << "loaded retail inner rate accepted unsupported uint16 semantics\n";
        return 1;
    }

    auto expect_bad_outer = [](bool ready, double hz, int gate_ms,
                               double increment, int multiplicity) {
        try {
            (void)make_retail_outer_scheduler_contract(
                ready, hz, gate_ms, increment, multiplicity);
        } catch (const std::invalid_argument&) {
            return true;
        }
        return false;
    };
    if (!expect_bad_outer(false, 30.0, 33,
                          shift::runtime::kRetailNormalOuterIncrementSeconds, 1) ||
        !expect_bad_outer(true, 60.0, 33,
                          shift::runtime::kRetailNormalOuterIncrementSeconds, 1) ||
        !expect_bad_outer(true, 30.0, 10,
                          shift::runtime::kRetailNormalOuterIncrementSeconds, 1) ||
        !expect_bad_outer(true, 30.0, 33, 1.0 / 60.0, 1) ||
        !expect_bad_outer(true, 30.0, 33,
                          shift::runtime::kRetailNormalOuterIncrementSeconds, 4)) {
        std::cerr << "retail outer handoff accepted unsupported timing semantics\n";
        return 1;
    }

    const auto scripted =
        make_runtime_loop_policy(false, false, 120, true, 5);
    if (scripted.continuous || !scripted.frame_limit_enabled ||
        scripted.continuous_wall_clock_pacing || scripted.frame_limit != 5 ||
        !scripted.uses_host_development_scheduler() ||
        scripted.retail_cadence_admitted ||
        scripted.uses_admitted_retail_scheduler()) {
        std::cerr << "scripted loop policy mismatch\n";
        return 1;
    }

    bool rejected_continuous_script = false;
    try {
        (void)make_runtime_loop_policy(true, false, 120, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_continuous_script = true;
    }
    if (!rejected_continuous_script) {
        std::cerr << "continuous input script was not rejected\n";
        return 1;
    }

    bool rejected_script_mismatch = false;
    try {
        (void)make_runtime_loop_policy(false, true, 4, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_script_mismatch = true;
    }
    if (!rejected_script_mismatch) {
        std::cerr << "script/frame mismatch was not rejected\n";
        return 1;
    }

    std::cout
        << "{\"format\":\"SHIFT.NativeRuntimeLoopPolicyRegression/2\","
        << "\"bounded\":true,\"continuous\":true,"
        << "\"continuous_safety_cap\":true,"
        << "\"steady_clock_pacing\":true,"
        << "\"host_scheduler_authority\":\"host-development\","
        << "\"retail_outer_authority_seam\":true,"
        << "\"retail_outer_cadence_admitted\":true,"
        << "\"loaded_inner_rate_required\":true,"
        << "\"retail_inner_substep_batch_semantics\":true,"
        << "\"retail_signed_accumulator_residual\":true,"
        << "\"retail_host_fallback_rejected\":true,"
        << "\"host_fixed_tick_seconds\":"
        << shift::runtime::kHostDevelopmentFixedDt << ","
        << "\"script_fail_closed\":true}\n";
    return 0;
}
