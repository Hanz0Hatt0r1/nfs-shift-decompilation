#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <iostream>
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
        require(kFun00765c40SceneQueryProviderGlobal == 0x00c133acu,
                "FUN_00765c40 scene-query provider global drift");
        require(kFun00765c40SceneQueryVtableSlot == 0x1c0u,
                "FUN_00765c40 scene-query vtable slot drift");
        require(kFun00765c40SurfaceRecordStride == 0x58u,
                "FUN_00765c40 surface-record stride drift");

        require(kFun00765c40ResidualStageOrder.front() ==
                    Fun00765c40ResidualStage::WheelPlaneStateRefresh,
                "FUN_00765c40 first native stage drift");
        require(kFun00765c40ResidualStageOrder[2] ==
                    Fun00765c40ResidualStage::SceneQuery,
                "FUN_00765c40 scene-query stage order drift");
        require(kFun00765c40ResidualStageOrder[3] ==
                    Fun00765c40ResidualStage::QueryCacheAndScalarCommit,
                "FUN_00765c40 query commit order drift");
        require(kFun00765c40ResidualStageOrder[5] ==
                    Fun00765c40ResidualStage::WheelJobQueueExecution,
                "FUN_00765c40 wheel-job queue order drift");
        require(kFun00765c40ResidualStageOrder[6] ==
                    Fun00765c40ResidualStage::Fun007584f0PersistentMutation,
                "FUN_00765c40 FUN_007584f0 order drift");
        require(kFun00765c40ResidualStageOrder.back() ==
                    Fun00765c40ResidualStage::OptionalBodyAccumulatorSweep,
                "FUN_00765c40 final native stage drift");

        require(kFun00765c40WheelLoopAOffsets ==
                    std::array<std::size_t, 4>{0x0a70u, 0x14f0u, 0x1f70u, 0x29f0u},
                "FUN_00765c40 wheel loop-A offsets drift");
        require(kFun00765c40WheelPairLoopBOffsets ==
                    std::array<std::size_t, 8>{
                        0x0ba0u, 0x0ba8u,
                        0x1620u, 0x1628u,
                        0x20a0u, 0x20a8u,
                        0x2b20u, 0x2b28u},
                "FUN_00765c40 wheel pair loop-B offsets drift");
        require(kFun00765c40ContactRecordPointerArrayOffset == 0x35c8u &&
                    kFun00765c40ContactRecordPointerCount == 12u &&
                    kFun00765c40ContactRecordPointerStride == 0x04u,
                "FUN_00765c40 contact record pointer geometry drift");
        require(kFun00765c40ContactScalarArrayOffset == 0x35f8u &&
                    kFun00765c40ContactScalarCount == 12u &&
                    kFun00765c40ContactScalarStride == 0x08u,
                "FUN_00765c40 contact scalar geometry drift");
        require(kFun007584f0PersistentWriteOffsets ==
                    std::array<std::size_t, 3>{0x0d40u, 0x17c0u, 0x3420u},
                "FUN_007584f0 persistent-write offsets drift");

        const auto wheel = materialize_fun_00752fa0_wheel_state_assignment(
            3u,
            0x0123456789abcdefULL);
        require(wheel.index == 3u &&
                    wheel.source_bits == 0x0123456789abcdefULL,
                "FUN_00752fa0 native assignment witness drift");

        const Fun00765c40LoadTerms loads = {-1.0, 0.0, 2.0, 3.5};
        require(fun_00765c40_positive_load_term_count(loads) == 2u,
                "FUN_00765c40 +0x407c positive-count witness drift");

        Fun00765c40SceneQueryBoundary scene{};
        scene.query_input.world_position = {1.0, 2.0, 3.0};
        scene.query_input.miss_fallback = 4.0;
        scene.query_input.cached_handle = 17u;
        validate_fun_00765c40_scene_query_boundary(scene);

        const Fun00765c40SceneQueryProvider scene_query = [](
            const Fun00765c40SceneQueryBoundary& boundary) {
            const auto query = build_fun_00765c40_query_record(
                boundary.query_input);
            return apply_fun_007b0710_collision_query_result(
                query,
                std::nullopt);
        };
        const auto query_commit = execute_fun_00765c40_scene_query_stage(
            scene,
            scene_query);
        require(!query_commit.output.hit,
                "FUN_00765c40 scene-query miss witness drift");
        require(!query_commit.cache_handle.has_value(),
                "FUN_00765c40 miss must clear +0x38dc cache handle");
        require(query_commit.projected_scalar == 4.0,
                "FUN_00765c40 miss must commit +0x38e8 fallback into +0x38e0");

        std::cout
            << "{\"format\":\"" << kFun00765c40ResidualPassContractFormat << "\","
            << "\"ready\":true,"
            << "\"retail_stage_count\":11,"
            << "\"scene_query_provider_global\":\"0x00c133ac\","
            << "\"scene_query_vtable_slot\":\"0x1c0\","
            << "\"query_commit_internalized\":true,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
