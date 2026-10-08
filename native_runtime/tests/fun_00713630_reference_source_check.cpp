#include "shift_fun_00713630_reference_source.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

}  // namespace

int main() {
    try {
        require(kFun00713630ManagerArrayOffset == 0x140u,
                "FUN_00713630 manager array offset drift");
        require(kFun00713630ManagerCountOffset == 0x144u,
                "FUN_00713630 manager count offset drift");
        require(kFun007144a0CadenceCounterOffset == 0x158u,
                "FUN_007144a0 cadence counter offset drift");
        require(kFun00713630ManagerRecordStride == 0x1fa0u,
                "FUN_00713630 manager record stride drift");
        require(kFun00713630ManagerRecordActiveOffset == 0x4eu,
                "FUN_00713630 manager active-byte offset drift");
        require(kFun00713630ParticipantSampleBaseOffset == 0x2b10u &&
                    kFun00713630ParticipantSampleStride == 0x0cu &&
                    kFun00713630ParticipantSampleCount == 3u,
                "FUN_00713630 participant sample geometry drift");
        require(kFun00713630ParticipantAngleOffset == 0x4b0u,
                "FUN_00713630 participant angle offset drift");
        require(kFun00766510ParticipantReferenceSourceOffsets[0] == 0x16b4u &&
                    kFun00766510ParticipantReferenceSourceOffsets[1] == 0x16b8u &&
                    kFun00766510ParticipantReferenceSourceOffsets[2] == 0x16bcu,
                "FUN_00713630/FUN_00766510 source handoff offsets drift");
        require(kFun00713630ParticipantPrimaryOutputOffset == 0x2128u &&
                    kFun00713630ParticipantSecondaryOutputOffset == 0x212cu,
                "FUN_00713630 aggregate output offsets drift");

        Fun00713630ReferenceSourceInput input{};
        input.samples = {{
            Fun00712940ReferenceRecord{2.0f, 0.5f, 5.0f},
            Fun00712940ReferenceRecord{4.0f, 0.2f, 8.0f},
            Fun00712940ReferenceRecord{20.0f, 0.0f, 5.0f},
        }};
        input.participant_angle = 0.25f;
        input.config.record_0_limit = 10.0f;
        input.config.record_0_scale = 2.0f;
        input.config.record_0_offset = 1.0f;
        input.config.record_2_ramp_begin = 0.0f;
        input.config.record_2_ramp_end = 10.0f;
        input.config.record_2_divisor = 10.0f;
        input.config.final_output_scale = 3.0f;

        const auto result = execute_fun_00713630_reference_source(input);
        require(f32_bits(result.aggregate.primary) == 0x3f07318du,
                "FUN_00712940 primary f32 witness drift");
        require(f32_bits(result.aggregate.secondary) == 0x3eb0e682u,
                "FUN_00712940 secondary f32 witness drift");
        require(f32_bits(result.final_scale) == 0x3f84ace2u,
                "FUN_00713630 final-scale f32 witness drift");
        require(f32_bits(result.sin_angle) == 0x3e7d5777u,
                "FUN_00713630 FSIN f32 witness drift");
        require(f32_bits(result.cos_angle) == 0x3f780aa5u,
                "FUN_00713630 FCOS f32 witness drift");
        require(f32_bits(result.participant_source[0]) == 0xbe834c30u &&
                    f32_bits(result.participant_source[1]) == 0x00000000u &&
                    f32_bits(result.participant_source[2]) == 0xbf808cffu,
                "FUN_00713630 participant reference-source witness drift");

        require(fun_007144a0_should_refresh_reference_source(0),
                "FUN_007144a0 counter 0 should refresh");
        require(!fun_007144a0_should_refresh_reference_source(1) &&
                    !fun_007144a0_should_refresh_reference_source(2),
                "FUN_007144a0 non-third counters incorrectly refresh");
        require(fun_007144a0_should_refresh_reference_source(3),
                "FUN_007144a0 counter 3 should refresh");

        bool zero_divisor_rejected = false;
        try {
            auto bad = input;
            bad.config.record_2_divisor = 0.0f;
            (void)execute_fun_00713630_reference_source(bad);
        } catch (const std::invalid_argument&) {
            zero_divisor_rejected = true;
        }
        require(zero_divisor_rejected,
                "FUN_00713630 accepted zero source divisor");

        std::cout
            << "{\"format\":\"" << kFun00713630ReferenceSourceFormat << "\","
            << "\"ready\":true,"
            << "\"sample_count\":3,"
            << "\"sample_stride\":\"0x0c\","
            << "\"manager_record_stride\":\"0x1fa0\","
            << "\"cadence_modulus\":3,"
            << "\"sin_wrapper\":\"FSIN\","
            << "\"cos_wrapper\":\"FCOS\","
            << "\"participant_source_offsets\":[\"0x16b4\",\"0x16b8\",\"0x16bc\"],"
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
