#include "shift_xbox_draw_input.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

const uint8_t kCapturedPacket[] = {
    0xC0, 0x03, 0x22, 0x01,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04,
    0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

uint32_t read_be32(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

void write_be32(uint8_t* bytes, uint32_t value) {
    bytes[0] = static_cast<uint8_t>(value >> 24);
    bytes[1] = static_cast<uint8_t>(value >> 16);
    bytes[2] = static_cast<uint8_t>(value >> 8);
    bytes[3] = static_cast<uint8_t>(value);
}

}  // namespace

int main() {
    const uint8_t shader_control_flow[] = {
        0x00, 0x01, 0x10, 0x02, 0x00, 0x02, 0x10, 0x00, 0xC4, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x10, 0x02, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    std::vector<shift::xbox::CapturedShaderControlFlow> control_flow;
    std::string error;
    require(shift::xbox::decode_captured_shader_control_flow(
                shader_control_flow, sizeof(shader_control_flow), &control_flow, &error),
            "bounded shader control-flow prefix was rejected");
    require(control_flow.size() == 4, "shader control-flow slot count changed");
    require(control_flow[0].instruction_index == 0 &&
                control_flow[0].opcode == shift::xbox::ShaderControlFlowOpcode::Exec &&
                control_flow[0].address == 2 && control_flow[0].instruction_count == 1 &&
                control_flow[0].sequence == 1,
            "shader exec scheduling fields changed");
    require(control_flow[1].instruction_index == 1 &&
                control_flow[1].opcode == shift::xbox::ShaderControlFlowOpcode::Allocate &&
                control_flow[1].allocation_size == 2 &&
                control_flow[1].allocation_type == 2,
            "shader export allocation fields changed");
    require(control_flow[2].opcode == shift::xbox::ShaderControlFlowOpcode::ExecEnd &&
                control_flow[2].address == 2 && control_flow[2].instruction_count == 1,
            "shader exec-end fields changed");
    require(control_flow[3].opcode == shift::xbox::ShaderControlFlowOpcode::Nop,
            "shader control-flow NOP changed");

    uint8_t conditional_exec_shader[sizeof(shader_control_flow)];
    std::copy(shader_control_flow, shader_control_flow + sizeof(shader_control_flow),
              conditional_exec_shader);
    conditional_exec_shader[6] = 0x36;
    conditional_exec_shader[7] = 0x00;
    require(shift::xbox::decode_captured_shader_control_flow(
                conditional_exec_shader, sizeof(conditional_exec_shader),
                &control_flow, &error) &&
                control_flow[0].opcode ==
                    shift::xbox::ShaderControlFlowOpcode::ConditionalExec &&
                control_flow[0].bool_constant == 128 && control_flow[0].condition,
            "conditional shader exec fields changed");

    const uint8_t shader_branch_control_flow[] = {
        0x00, 0x00, 0x10, 0x04, 0x00, 0x02, 0x10, 0x00, 0xB6, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x20, 0x03, 0x10, 0x04, 0xB0, 0x00, 0x20, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    std::vector<shift::xbox::CapturedShaderControlFlow> branch_control_flow;
    require(shift::xbox::decode_captured_shader_control_flow(
                shader_branch_control_flow, sizeof(shader_branch_control_flow),
                &branch_control_flow, &error),
            "shader control-flow branches were rejected");
    require(branch_control_flow.size() == 8 &&
                branch_control_flow[1].opcode ==
                    shift::xbox::ShaderControlFlowOpcode::ConditionalJump &&
                branch_control_flow[1].address == 2 &&
                branch_control_flow[1].bool_constant == 128 &&
                branch_control_flow[1].condition &&
                !branch_control_flow[1].unconditional &&
                branch_control_flow[2].opcode ==
                    shift::xbox::ShaderControlFlowOpcode::ConditionalJump &&
                branch_control_flow[2].address == 3 &&
                branch_control_flow[2].unconditional,
            "shader conditional and unconditional jump fields changed");

    shift::xbox::CapturedShaderControlFlow fetch_clause{};
    fetch_clause.instruction_index = 4;
    fetch_clause.opcode = shift::xbox::ShaderControlFlowOpcode::Exec;
    fetch_clause.address = 2;
    fetch_clause.instruction_count = 2;
    fetch_clause.sequence = 9;
    shift::xbox::CapturedShaderControlFlow branch_clause{};
    branch_clause.instruction_index = 5;
    branch_clause.opcode = shift::xbox::ShaderControlFlowOpcode::ConditionalJump;
    shift::xbox::CapturedShaderControlFlow end_clause{};
    end_clause.instruction_index = 6;
    end_clause.opcode = shift::xbox::ShaderControlFlowOpcode::ExecEnd;
    end_clause.address = 4;
    end_clause.instruction_count = 1;
    end_clause.sequence = 2;
    const std::vector<shift::xbox::CapturedShaderControlFlow> scheduled_control_flow = {
        fetch_clause, branch_clause, end_clause,
    };
    std::vector<shift::xbox::CapturedShaderInstructionSchedule> instruction_schedule;
    require(shift::xbox::schedule_captured_shader_instructions(
                scheduled_control_flow, 6 * 12, &instruction_schedule, &error),
            "shader exec clauses did not produce an instruction schedule");
    require(instruction_schedule.size() == 3 && instruction_schedule[0].address == 2 &&
                instruction_schedule[0].kind ==
                    shift::xbox::ShaderScheduledInstructionKind::Fetch &&
                instruction_schedule[0].control_flow_index == 4 &&
                instruction_schedule[1].address == 3 &&
                instruction_schedule[1].kind ==
                    shift::xbox::ShaderScheduledInstructionKind::Alu &&
                instruction_schedule[1].serialized && instruction_schedule[2].address == 4 &&
                instruction_schedule[2].serialized,
            "shader sequence kind/serialization fields changed");
    const auto unchanged_schedule = instruction_schedule;
    require(!shift::xbox::schedule_captured_shader_instructions(
                scheduled_control_flow, 4 * 12, &instruction_schedule, &error) &&
                instruction_schedule.size() == unchanged_schedule.size() &&
                instruction_schedule[0].address == unchanged_schedule[0].address,
            "out-of-range shader schedule was accepted or changed its output");

    uint8_t vertex_shader_fetch_bytes[12];
    write_be32(vertex_shader_fetch_bytes, 0x82343840u);
    write_be32(vertex_shader_fetch_bytes + 4, 0x00070123u);
    write_be32(vertex_shader_fetch_bytes + 8, 0x7FFFFE05u);
    uint8_t texture_shader_fetch_bytes[12];
    write_be32(texture_shader_fetch_bytes, 0x0C702081u);
    write_be32(texture_shader_fetch_bytes + 4, 0x00000555u);
    write_be32(texture_shader_fetch_bytes + 8, 0x80004000u);
    shift::xbox::CapturedShaderFetchInstruction fetch{};
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_fetch_bytes, sizeof(vertex_shader_fetch_bytes), &fetch, &error),
            "captured vfetch_full instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::VertexFull &&
                fetch.fetch_constant_index == 10 && fetch.source_register == 2 &&
                fetch.destination_register == 3 && fetch.source_swizzle == 2 &&
                fetch.destination_swizzle == 0x123 && fetch.vertex_format == 7 &&
                fetch.vertex_stride == 5 && fetch.vertex_offset == -2 &&
                fetch.source_relative && fetch.destination_relative,
            "vfetch_full fields changed");
    const shift::xbox::CapturedShaderFetchInstruction full_fetch = fetch;
    uint8_t vertex_shader_mini_fetch_bytes[12];
    write_be32(vertex_shader_mini_fetch_bytes, 0x42604060u);
    write_be32(vertex_shader_mini_fetch_bytes + 4, 0x40070123u);
    write_be32(vertex_shader_mini_fetch_bytes + 8, 0x7FFFFF00u);
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_mini_fetch_bytes,
                sizeof(vertex_shader_mini_fetch_bytes), &fetch, &error),
            "captured vfetch_mini instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::VertexMini &&
                fetch.fetch_constant_index == 19 && fetch.source_register == 3 &&
                fetch.destination_register == 4 && fetch.source_swizzle == 1 &&
                fetch.destination_swizzle == 0x123 && fetch.vertex_format == 7 &&
                fetch.vertex_stride == 0 && fetch.vertex_offset == -1 &&
                !fetch.source_relative && !fetch.destination_relative,
            "vfetch_mini fields changed");
    shift::xbox::CapturedShaderFetchInstruction effective_mini_fetch{};
    require(shift::xbox::inherit_captured_vertex_fetch_fields(
                fetch, &full_fetch, &effective_mini_fetch, &error) &&
                effective_mini_fetch.kind ==
                    shift::xbox::CapturedShaderFetchKind::VertexMini &&
                effective_mini_fetch.fetch_constant_index == 10 &&
                effective_mini_fetch.source_register == 2 &&
                effective_mini_fetch.source_swizzle == 2 &&
                effective_mini_fetch.vertex_stride == 5 &&
                effective_mini_fetch.vertex_format == 7 &&
                effective_mini_fetch.vertex_offset == -1 &&
                effective_mini_fetch.destination_register == 4 &&
                effective_mini_fetch.source_relative &&
                !effective_mini_fetch.destination_relative,
            "vfetch_mini did not inherit the full-fetch addressing fields");
    require(!shift::xbox::inherit_captured_vertex_fetch_fields(
                fetch, nullptr, &effective_mini_fetch, &error) &&
                error == "captured mini vertex fetch has no preceding full fetch",
            "mini vertex fetch without a full fetch was accepted");
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                texture_shader_fetch_bytes, sizeof(texture_shader_fetch_bytes), &fetch, &error),
            "captured tfetch2D instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::Texture2D &&
                fetch.fetch_constant_index == 7 && fetch.texture_dimension == 1 &&
                fetch.source_register == 4 && fetch.destination_register == 2 &&
                fetch.source_swizzle == 3 && fetch.destination_swizzle == 0x555 &&
                fetch.predicate_condition,
            "tfetch2D fields changed");
    require(!shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_fetch_bytes, sizeof(vertex_shader_fetch_bytes) - 1,
                &fetch, &error),
            "truncated shader fetch instruction was accepted");
    uint8_t unsupported_shader_fetch[sizeof(vertex_shader_fetch_bytes)];
    std::copy(vertex_shader_fetch_bytes,
              vertex_shader_fetch_bytes + sizeof(vertex_shader_fetch_bytes),
              unsupported_shader_fetch);
    unsupported_shader_fetch[3] = 0x42;
    require(!shift::xbox::decode_captured_shader_fetch_instruction(
                unsupported_shader_fetch, sizeof(unsupported_shader_fetch), &fetch, &error),
            "unsupported shader fetch opcode was accepted");

    uint8_t alu_instruction_bytes[12];
    const uint32_t alu_word0 =
        1u | (1u << 6) | (1u << 7) | (2u << 8) | (1u << 14) | (1u << 15) |
        (0xAu << 16) | (5u << 20) | (1u << 24) | (37u << 26);
    const uint32_t alu_word1 = 0xFF563412u;
    const uint32_t alu_word2 = 0xBCC18243u;
    write_be32(alu_instruction_bytes, alu_word0);
    write_be32(alu_instruction_bytes + 4, alu_word1);
    write_be32(alu_instruction_bytes + 8, alu_word2);
    shift::xbox::CapturedShaderAluInstruction alu{};
    require(shift::xbox::decode_captured_shader_alu_instruction(
                alu_instruction_bytes, sizeof(alu_instruction_bytes), &alu, &error),
            "96-bit shader ALU instruction was rejected");
    require(alu.vector_opcode == 28 && alu.scalar_opcode == 37 &&
                alu.vector_destination == 1 && alu.scalar_destination == 2 &&
                alu.vector_write_mask == 0xA && alu.scalar_write_mask == 5 &&
                alu.export_data && alu.vector_destination_relative &&
                alu.scalar_destination_relative && alu.absolute_constants &&
                alu.vector_clamp && !alu.scalar_clamp && alu.predicated &&
                alu.predicate_condition && alu.const0_relative && alu.const1_relative &&
                alu.const_address_register_relative &&
                alu.source_registers[0] == 0xC1 && alu.source_registers[1] == 0x82 &&
                alu.source_registers[2] == 0x43 && alu.source_temporary_registers[0] == 1 &&
                alu.source_temporary_registers[1] == 2 && alu.source_temporary_registers[2] == 3 &&
                alu.source_temporary_relative[0] && !alu.source_temporary_relative[1] &&
                alu.source_temporary_relative[2] && alu.source_temporary_absolute[0] &&
                !alu.source_temporary_absolute[1] && !alu.source_temporary_absolute[2] &&
                alu.scalar_temporary_register == 19 &&
                alu.scalar_temporary_component == 2 &&
                alu.scalar_constant_component == 3 && alu.source_swizzles[0] == 0x56 &&
                alu.source_swizzles[1] == 0x34 && alu.source_swizzles[2] == 0x12 &&
                alu.source_is_temporary[0] && !alu.source_is_temporary[1] &&
                alu.source_is_temporary[2] && alu.source_negate[0] &&
                alu.source_negate[1] && alu.source_negate[2],
            "shader ALU bit fields changed");
    require(shift::xbox::captured_alu_source_component(0x1Bu, 0) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 1) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 2) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 3) == 3 &&
                shift::xbox::captured_alu_source_component(0xAAu, 0) == 2 &&
                shift::xbox::captured_alu_source_component(0xAAu, 1) == 3 &&
                shift::xbox::captured_alu_source_component(0xAAu, 2) == 0 &&
                shift::xbox::captured_alu_source_component(0xAAu, 3) == 1,
            "component-relative ALU swizzles changed");
    require(!shift::xbox::decode_captured_shader_alu_instruction(
                alu_instruction_bytes, sizeof(alu_instruction_bytes) - 1, &alu, &error),
            "truncated shader ALU instruction was accepted");

    std::vector<shift::xbox::CapturedShaderControlFlow> unchanged_control_flow = control_flow;
    require(!shift::xbox::decode_captured_shader_control_flow(
                shader_control_flow, sizeof(shader_control_flow) - 4,
                &control_flow, &error),
            "truncated shader control-flow input was accepted");
    require(control_flow.size() == unchanged_control_flow.size(),
            "failed shader decode partially replaced its output");
    uint8_t unsupported_shader_control_flow[sizeof(shader_control_flow)];
    std::copy(shader_control_flow, shader_control_flow + sizeof(shader_control_flow),
              unsupported_shader_control_flow);
    unsupported_shader_control_flow[6] = 0xF0;
    require(!shift::xbox::decode_captured_shader_control_flow(
                unsupported_shader_control_flow, sizeof(unsupported_shader_control_flow),
                &control_flow, &error),
            "unsupported shader control-flow opcode was accepted");
    require(error.find("opcode 15 at instruction 0") != std::string::npos,
            "unsupported shader control-flow diagnostic lost opcode and slot");
    require(control_flow.size() == unchanged_control_flow.size(),
            "unsupported shader decode partially replaced its output");

    const uint8_t framed_stream[] = {
        0x00, 0x01, 0x12, 0x34, 0xAA, 0xBB, 0xCC, 0xDD, // type 0, base 0x1234
        0x01, 0x02, 0x03, 0x04,
        0x40, 0x1A, 0xA8, 0x21, 0x11, 0x22, 0x33, 0x44, // type 1, regs 0x21/0x355
        0x55, 0x66, 0x77, 0x88,
        0x80, 0x00, 0x00, 0x00,                         // type 2
        0x00, 0x00, 0x00, 0x00,                         // single-dword zero NOP
        0xC0, 0x03, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x06, 0x00, 0x04, 0x09, 0x75, 0xD7, 0xB0,
        0x40, 0x00, 0x00, 0x06,                         // type 3 DRAW_INDX
    };
    std::vector<shift::xbox::PacketSpan> packet_spans;
    require(shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream), &packet_spans, &error),
            "well-formed PM4 packet stream was rejected");
    require(packet_spans.size() == 5, "PM4 packet scanner returned the wrong packet count");
    require(packet_spans[0].type == shift::xbox::PacketType::Type0 &&
                packet_spans[0].byte_offset == 0 && packet_spans[0].byte_length == 12,
            "type-0 framing changed");
    require(packet_spans[1].type == shift::xbox::PacketType::Type1 &&
                packet_spans[1].byte_offset == 12 && packet_spans[1].byte_length == 12,
            "type-1 framing changed");
    require(packet_spans[2].type == shift::xbox::PacketType::Type2 &&
                packet_spans[2].byte_offset == 24 && packet_spans[2].byte_length == 4,
            "type-2 framing changed");
    require(packet_spans[3].type == shift::xbox::PacketType::ZeroNop &&
                packet_spans[3].byte_offset == 28 && packet_spans[3].byte_length == 4,
            "zero-dword NOP framing changed");
    require(packet_spans[4].type == shift::xbox::PacketType::Type3 &&
                packet_spans[4].byte_offset == 32 && packet_spans[4].byte_length == 20 &&
                packet_spans[4].opcode == 0x22,
            "type-3 DRAW_INDX framing changed");
    const uint8_t captured_indirect_buffer[] = {
        0xC0, 0x01, 0x3F, 0x00, 0x09, 0x75, 0xB6, 0x60,
        0x00, 0x00, 0x00, 0x4A,
    };
    shift::xbox::CapturedIndirectBuffer indirect_buffer{};
    require(shift::xbox::decode_captured_indirect_buffer(
                captured_indirect_buffer, sizeof(captured_indirect_buffer),
                &indirect_buffer, &error) &&
                indirect_buffer.guest_address == 0x0975B660u &&
                indirect_buffer.dword_count == 74u,
            "captured PM4_INDIRECT_BUFFER span decoded incorrectly");
    auto invalid_indirect_buffer = std::vector<uint8_t>(
        captured_indirect_buffer,
        captured_indirect_buffer + sizeof(captured_indirect_buffer));
    invalid_indirect_buffer[11] = 0x00;
    const auto unchanged_indirect_buffer = indirect_buffer;
    require(!shift::xbox::decode_captured_indirect_buffer(
                invalid_indirect_buffer.data(), invalid_indirect_buffer.size(),
                &indirect_buffer, &error) &&
                indirect_buffer.guest_address == unchanged_indirect_buffer.guest_address &&
                indirect_buffer.dword_count == unchanged_indirect_buffer.dword_count,
            "invalid PM4_INDIRECT_BUFFER changed decoded output");
    std::vector<shift::xbox::GuestRegisterWrite> register_writes;
    require(shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[0].byte_offset,
                packet_spans[0].byte_length, &register_writes, &error) &&
                register_writes.size() == 2 &&
                register_writes[0].register_index == 0x1234u &&
                register_writes[0].value == 0xAABBCCDDu &&
                register_writes[1].register_index == 0x1235u &&
                register_writes[1].value == 0x01020304u,
            "type-0 PM4 register writes decoded incorrectly");
    require(shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[1].byte_offset,
                packet_spans[1].byte_length, &register_writes, &error) &&
                register_writes.size() == 2 &&
                register_writes[0].register_index == 0x21u &&
                register_writes[0].value == 0x11223344u &&
                register_writes[1].register_index == 0x355u &&
                register_writes[1].value == 0x55667788u,
            "type-1 PM4 register writes decoded incorrectly");
    const uint8_t repeated_register_packet[] = {
        0x00, 0x01, 0x80, 0x12, 0x11, 0x11, 0x11, 0x11,
        0x22, 0x22, 0x22, 0x22,
    };
    require(shift::xbox::decode_guest_register_writes(
                repeated_register_packet, sizeof(repeated_register_packet),
                &register_writes, &error) && register_writes.size() == 2 &&
                register_writes[0].register_index == 0x12u &&
                register_writes[1].register_index == 0x12u,
            "type-0 write-one-register mode decoded incorrectly");
    const auto unchanged_writes = register_writes;
    require(!shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[2].byte_offset,
                packet_spans[2].byte_length, &register_writes, &error) &&
                register_writes.size() == unchanged_writes.size() &&
                register_writes[0].register_index == unchanged_writes[0].register_index &&
                register_writes[0].value == unchanged_writes[0].value &&
                register_writes[1].register_index == unchanged_writes[1].register_index &&
                register_writes[1].value == unchanged_writes[1].value,
            "unsupported PM4 packet changed register-write output");
    require(!shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[0].byte_offset, 8u,
                &register_writes, &error) &&
                register_writes.size() == unchanged_writes.size(),
            "truncated type-0 PM4 packet changed register-write output");
    const uint8_t captured_vertex_im_load[] = {
        0xC0, 0x01, 0x27, 0x00, 0x09, 0xD5, 0x68, 0xE0, 0x00, 0x00, 0x00, 0x69,
    };
    const uint8_t captured_pixel_im_load[] = {
        0xC0, 0x01, 0x27, 0x00, 0x09, 0xD5, 0x04, 0x61, 0x00, 0x00, 0x00, 0x1E,
    };
    shift::xbox::CapturedShaderProgramLoad shader_load{};
    require(shift::xbox::decode_captured_shader_program_load(
                captured_vertex_im_load, sizeof(captured_vertex_im_load),
                &shader_load, &error) &&
                shader_load.stage == shift::xbox::GuestShaderStage::Vertex &&
                shader_load.guest_address == 0x09D568E0u &&
                shader_load.dword_count == 105u && shader_load.byte_length == 420u,
            "captured vertex PM4_IM_LOAD span decoded incorrectly");
    require(shift::xbox::decode_captured_shader_program_load(
                captured_pixel_im_load, sizeof(captured_pixel_im_load),
                &shader_load, &error) &&
                shader_load.stage == shift::xbox::GuestShaderStage::Pixel &&
                shader_load.guest_address == 0x09D50460u &&
                shader_load.dword_count == 30u && shader_load.byte_length == 120u,
            "captured pixel PM4_IM_LOAD span decoded incorrectly");
    const auto unchanged_shader_load = shader_load;
    uint8_t invalid_shader_load[sizeof(captured_pixel_im_load)];
    std::copy_n(captured_pixel_im_load, sizeof(captured_pixel_im_load),
                invalid_shader_load);
    invalid_shader_load[7] = 0x62;
    require(!shift::xbox::decode_captured_shader_program_load(
                invalid_shader_load, sizeof(invalid_shader_load), &shader_load, &error) &&
                shader_load.stage == unchanged_shader_load.stage &&
                shader_load.guest_address == unchanged_shader_load.guest_address &&
                shader_load.byte_length == unchanged_shader_load.byte_length,
            "unsupported shader stage changed decoded output");
    const uint8_t captured_inline_shader_load[] = {
        0xC0, 0x05, 0x2B, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x03,
        0x11, 0x22, 0x33, 0x44,
        0x55, 0x66, 0x77, 0x88,
        0x99, 0xAA, 0xBB, 0xCC,
        0xDE, 0xAD, 0xBE, 0xEF,
    };
    shift::xbox::CapturedImmediateShaderProgramLoad immediate_shader_load{};
    require(shift::xbox::decode_captured_immediate_shader_program_load(
                captured_inline_shader_load, sizeof(captured_inline_shader_load),
                &immediate_shader_load, &error) &&
                immediate_shader_load.stage == shift::xbox::GuestShaderStage::Vertex &&
                immediate_shader_load.dword_count == 3u &&
                immediate_shader_load.byte_length == 12u &&
                immediate_shader_load.code_offset == 12u &&
                read_be32(captured_inline_shader_load + immediate_shader_load.code_offset) ==
                    0x11223344u,
            "captured inline vertex shader payload decoded incorrectly");
    auto captured_pixel_inline_shader_load = std::vector<uint8_t>(
        captured_inline_shader_load,
        captured_inline_shader_load + sizeof(captured_inline_shader_load));
    captured_pixel_inline_shader_load[7] = 0x01;
    require(shift::xbox::decode_captured_immediate_shader_program_load(
                captured_pixel_inline_shader_load.data(),
                captured_pixel_inline_shader_load.size(), &immediate_shader_load, &error) &&
                immediate_shader_load.stage == shift::xbox::GuestShaderStage::Pixel &&
                immediate_shader_load.dword_count == 3u &&
                immediate_shader_load.code_offset == 12u,
            "captured inline pixel shader payload decoded incorrectly");
    const auto unchanged_immediate_shader_load = immediate_shader_load;
    auto invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[7] = 0x02;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error) &&
                immediate_shader_load.stage == unchanged_immediate_shader_load.stage &&
                immediate_shader_load.dword_count == unchanged_immediate_shader_load.dword_count &&
                immediate_shader_load.code_offset == unchanged_immediate_shader_load.code_offset,
            "unsupported inline shader stage changed decoded output");
    invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[9] = 0x01;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error),
            "nonzero inline shader start address was accepted");
    invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[11] = 0x05;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error),
            "inline shader code span larger than its PM4 payload was accepted");
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                captured_inline_shader_load, sizeof(captured_inline_shader_load) - 4u,
                &immediate_shader_load, &error),
            "truncated inline shader PM4 packet was accepted");
    const uint8_t captured_constant_load_packet[] = {
        0xC0, 0x02, 0x2F, 0x00, 0x09, 0xD5, 0x68, 0xA0,
        0x00, 0x00, 0x03, 0xF0, 0x00, 0x00, 0x00, 0x10,
    };
    shift::xbox::CapturedConstantLoad constant_load{};
    require(shift::xbox::decode_captured_constant_load(
                captured_constant_load_packet, sizeof(captured_constant_load_packet),
                &constant_load, &error) &&
                constant_load.bank == shift::xbox::CapturedConstantBank::Alu &&
                constant_load.guest_address == 0x09D568A0u &&
                constant_load.start_index == 0x3F0u &&
                constant_load.dword_count == 16u &&
                constant_load.destination_register == 0x43F0u &&
                constant_load.byte_length == 64u,
            "captured PM4_LOAD_ALU_CONSTANT span decoded incorrectly");
    uint8_t constant_load_data[64]{};
    for (uint32_t i = 0; i < 16; ++i) write_be32(constant_load_data + i * 4, 0xA0u + i);
    std::vector<shift::xbox::GuestRegisterWrite> loaded_constants;
    require(shift::xbox::decode_captured_constant_load_data(
                constant_load, constant_load_data, sizeof(constant_load_data),
                &loaded_constants, &error) && loaded_constants.size() == 16u &&
                loaded_constants.front().register_index == 0x43F0u &&
                loaded_constants.front().value == 0xA0u &&
                loaded_constants.back().register_index == 0x43FFu &&
                loaded_constants.back().value == 0xAFu,
            "captured constant-load bytes were not mapped as big-endian register values");
    const uint8_t captured_loop_constant_load_packet[] = {
        0xC0, 0x02, 0x2F, 0x00, 0x09, 0xD5, 0x68, 0xA0,
        0x00, 0x03, 0x00, 0x07, 0x00, 0x00, 0x00, 0x01,
    };
    shift::xbox::CapturedConstantLoad loop_constant_load{};
    require(shift::xbox::decode_captured_constant_load(
                captured_loop_constant_load_packet,
                sizeof(captured_loop_constant_load_packet),
                &loop_constant_load, &error) &&
                loop_constant_load.bank == shift::xbox::CapturedConstantBank::Loop &&
                loop_constant_load.start_index == 7u &&
                loop_constant_load.destination_register == 0x490Fu &&
                loop_constant_load.byte_length == 4u,
            "captured loop-constant load destination decoded incorrectly");
    const uint8_t loop_constant_bytes[] = {0x00, 0xFE, 0x05, 0x03};
    std::vector<shift::xbox::GuestRegisterWrite> loaded_loop_constants;
    require(shift::xbox::decode_captured_constant_load_data(
                loop_constant_load, loop_constant_bytes,
                sizeof(loop_constant_bytes), &loaded_loop_constants, &error) &&
                loaded_loop_constants.size() == 1u &&
                loaded_loop_constants.front().register_index == 0x490Fu &&
                loaded_loop_constants.front().value == 0x00FE0503u,
            "captured loop constant lost its big-endian register value");
    auto invalid_constant_load = std::vector<uint8_t>(
        captured_constant_load_packet,
        captured_constant_load_packet + sizeof(captured_constant_load_packet));
    invalid_constant_load[9] = 0x05;
    const auto unchanged_constant_load = constant_load;
    require(!shift::xbox::decode_captured_constant_load(
                invalid_constant_load.data(), invalid_constant_load.size(),
                &constant_load, &error) &&
                constant_load.guest_address == unchanged_constant_load.guest_address &&
                constant_load.destination_register == unchanged_constant_load.destination_register,
            "unsupported constant-load bank changed decoded output");
    shift::xbox::DecodedIndexedDraw framed_draw{};
    require(shift::xbox::decode_captured_draw_indx(
                framed_stream + packet_spans[4].byte_offset,
                packet_spans[4].byte_length, &framed_draw, &error),
            "framed DRAW_INDX did not reach the bounded draw decoder");

    std::vector<shift::xbox::PacketSpan> unchanged_spans = packet_spans;
    require(!shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream) - 1, &packet_spans, &error),
            "unaligned PM4 stream was accepted");
    require(packet_spans.size() == unchanged_spans.size(),
            "failed PM4 scan partially replaced its output");
    require(!shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream) - 4, &packet_spans, &error),
            "truncated PM4 packet stream was accepted");
    require(packet_spans.size() == unchanged_spans.size(),
            "truncated PM4 scan partially replaced its output");

    shift::xbox::DecodedIndexedDraw input{};
    require(shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), &input, &error),
            "captured retail packet was rejected");
    const uint8_t captured_draw_indx_2[] = {
        0xC0, 0x02, 0x36, 0x00,
        0x00, 0x06, 0x00, 0x04,
        0x09, 0x75, 0xD7, 0xB0,
        0x40, 0x00, 0x00, 0x06,
    };
    shift::xbox::DecodedIndexedDraw draw_indx_2{};
    require(shift::xbox::decode_captured_draw_indx(
                captured_draw_indx_2, sizeof(captured_draw_indx_2),
                &draw_indx_2, &error) &&
                draw_indx_2.topology == input.topology &&
                draw_indx_2.index_count == input.index_count &&
                draw_indx_2.index_guest_address == input.index_guest_address &&
                draw_indx_2.index_byte_length == input.index_byte_length,
            "captured PM4_DRAW_INDX_2 DMA form decoded differently from DRAW_INDX");
    const uint8_t live_autoindex_point[] = {
        0xC0, 0x00, 0x36, 0x00, 0x00, 0x01, 0x00, 0x81,
    };
    require(shift::xbox::decode_captured_draw_indx(
                live_autoindex_point, sizeof(live_autoindex_point),
                &draw_indx_2, &error) && draw_indx_2.auto_index &&
                draw_indx_2.topology == shift::xbox::PrimitiveTopology::PointList &&
                draw_indx_2.index_count == 1,
            "live AutoIndex point packet was not decoded");
    const uint8_t live_autoindex_rectangle_list[] = {
        0xC0, 0x00, 0x36, 0x01, 0x00, 0x03, 0x00, 0x88,
    };
    require(shift::xbox::decode_captured_draw_indx(
                live_autoindex_rectangle_list,
                sizeof(live_autoindex_rectangle_list), &draw_indx_2, &error) &&
                draw_indx_2.auto_index &&
                draw_indx_2.topology ==
                    shift::xbox::PrimitiveTopology::RectangleList &&
                draw_indx_2.index_count == 3,
            "live AutoIndex rectangle-list packet was not decoded");
    const uint8_t draw_indx_autoindex_rectangle_list[] = {
        0xC0, 0x01, 0x22, 0x01,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x03, 0x00, 0x88,
    };
    require(shift::xbox::decode_captured_draw_indx(
                draw_indx_autoindex_rectangle_list,
                sizeof(draw_indx_autoindex_rectangle_list), &draw_indx_2,
                &error) &&
                draw_indx_2.auto_index &&
                draw_indx_2.topology ==
                    shift::xbox::PrimitiveTopology::RectangleList &&
                draw_indx_2.index_count == 3,
            "DRAW_INDX AutoIndex packet with its visibility-query prefix was rejected");
    const uint8_t draw_indx_autoindex_triangle_list[] = {
        0xC0, 0x01, 0x22, 0x01,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x03, 0x00, 0x84,
    };
    require(shift::xbox::decode_captured_draw_indx(
                draw_indx_autoindex_triangle_list,
                sizeof(draw_indx_autoindex_triangle_list), &draw_indx_2,
                &error) &&
                draw_indx_2.auto_index &&
                draw_indx_2.topology == shift::xbox::PrimitiveTopology::TriangleList &&
                draw_indx_2.index_count == 3,
            "DRAW_INDX AutoIndex triangle-list packet was rejected");
    const uint8_t draw_indx_autoindex_triangle_strip[] = {
        0xC0, 0x01, 0x22, 0x01,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x04, 0x00, 0x86,
    };
    require(shift::xbox::decode_captured_draw_indx(
                draw_indx_autoindex_triangle_strip,
                sizeof(draw_indx_autoindex_triangle_strip), &draw_indx_2,
                &error) &&
                draw_indx_2.auto_index &&
                draw_indx_2.topology ==
                    shift::xbox::PrimitiveTopology::TriangleStrip &&
                draw_indx_2.index_count == 4,
            "captured AutoIndex triangle strip packet was rejected");
    const uint8_t draw_indx_autoindex_invalid_triangle_count[] = {
        0xC0, 0x01, 0x22, 0x01,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x02, 0x00, 0x84,
    };
    require(!shift::xbox::decode_captured_draw_indx(
                draw_indx_autoindex_invalid_triangle_count,
                sizeof(draw_indx_autoindex_invalid_triangle_count), &draw_indx_2,
                &error) && error == "unsupported AutoIndex primitive type 4 count 2",
            "invalid AutoIndex triangle count was accepted or lost its diagnostic");
    auto captured_auto_index_draw = std::vector<uint8_t>(
        captured_draw_indx_2,
        captured_draw_indx_2 + sizeof(captured_draw_indx_2));
    captured_auto_index_draw[7] = 0x84;
    require(!shift::xbox::decode_captured_draw_indx(
                captured_auto_index_draw.data(),
                captured_auto_index_draw.size(), &draw_indx_2, &error) &&
                error == "unsupported AutoIndex DRAW_INDX_2 form",
            "non-indexed DRAW_INDX_2 auto-index form was accepted as an "
            "indexed draw");
    require(!shift::xbox::decode_captured_draw_indx(
                captured_draw_indx_2, sizeof(captured_draw_indx_2) - 4u,
                &draw_indx_2, &error),
            "truncated PM4_DRAW_INDX_2 packet was accepted");
    require(input.topology == shift::xbox::PrimitiveTopology::TriangleList,
            "primitive topology changed");
    require(input.index_count == 6, "index count changed");
    require(input.index_guest_address == 0x0975D7B0u, "index base changed");
    require(input.index_type_bits == 16, "index type changed");
    require(input.index_endian_mode == 1, "index endian mode changed");
    require(input.index_byte_length == 12, "index range changed");

    const uint32_t captured_vertex_descriptor[] = {0x0975DFD3u, 0x10000032u};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    require(shift::xbox::decode_captured_vertex_fetch(
                captured_vertex_descriptor, &vertex_fetch, &error),
            "captured vertex-fetch descriptor was rejected");
    require(vertex_fetch.guest_address == 0x0975DFD0u,
            "captured vertex-fetch address changed");
    require(vertex_fetch.endian_mode == 2 && vertex_fetch.size_words == 12 &&
                vertex_fetch.byte_length == 48,
            "captured vertex-fetch shape changed");

    const uint32_t captured_texture_descriptor[] = {
        0x8800D8FEu, 0x09D57086u, 0x001FE3FFu,
        0x01280C14u, 0x00000003u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch texture_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_texture_descriptor, &texture_fetch, &error),
            "captured texture-fetch descriptor was rejected");
    require(texture_fetch.guest_address == 0x09D57000u && texture_fetch.format == 6 &&
                texture_fetch.endian_mode == 2,
            "captured texture resource identity changed");
    require(texture_fetch.width == 1024 && texture_fetch.height == 256 &&
                texture_fetch.pitch == 1024 &&
                texture_fetch.byte_length == 1024u * 256u * 4u && texture_fetch.tiled,
            "captured texture dimensions or layout changed");
    require(texture_fetch.dimension == 1 && texture_fetch.swizzle == 0x60Au &&
                texture_fetch.mag_filter == 1 && texture_fetch.min_filter == 1 &&
                texture_fetch.mip_filter == 2 && texture_fetch.aniso_filter == 0,
            "captured texture sampling fields changed");
    require(texture_fetch.sign_x == 3 && texture_fetch.sign_y == 3 &&
                texture_fetch.sign_z == 3 && texture_fetch.sign_w == 0 &&
                texture_fetch.clamp_x == 6 && texture_fetch.clamp_y == 6 &&
                texture_fetch.clamp_z == 0 && !texture_fetch.integer_format &&
                texture_fetch.border_color == 0 && !texture_fetch.border_size,
            "captured texture channel or clamp state changed");

    const uint32_t copied_format31_descriptor[] = {
        (8u << 22) | 2u,
        ((0x0CC87000u >> 12) << 12) | (2u << 6) | 31u,
        (242u << 13) | 255u,
        0u,
        0u,
        1u << 9,
    };
    shift::xbox::CapturedTextureFetch copied_format31_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                copied_format31_descriptor, &copied_format31_fetch, &error) &&
                copied_format31_fetch.guest_address == 0x0CC87000u &&
                copied_format31_fetch.format == 31u &&
                copied_format31_fetch.endian_mode == 2u &&
                copied_format31_fetch.width == 256u &&
                copied_format31_fetch.height == 243u &&
                copied_format31_fetch.pitch == 256u &&
                copied_format31_fetch.byte_length == 256u * 243u * 4u &&
                !copied_format31_fetch.tiled &&
                !copied_format31_fetch.packed_mips,
            "linear format-31 texture metadata for an exact Copy/Convert destination was rejected");
    std::vector<uint8_t> unsupported_format31_upload;
    require(!shift::xbox::untile_captured_texture_2d(
                copied_format31_fetch, nullptr, 0,
                &unsupported_format31_upload, &error),
            "format-31 texture upload accepted missing guest memory");

    const uint32_t copied_format26_descriptor[] = {
        0x8A024802u, 0x0BE1905Au, 0x0059E4FFu,
        0x0106AD11u, 0u, 0x00000210u,
    };
    shift::xbox::CapturedTextureFetch copied_format26_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                copied_format26_descriptor, &copied_format26_fetch, &error) &&
                copied_format26_fetch.guest_address == 0x0BE19000u &&
                copied_format26_fetch.format == 26u &&
                copied_format26_fetch.endian_mode == 1u &&
                copied_format26_fetch.integer_format &&
                copied_format26_fetch.width == 1280u &&
                copied_format26_fetch.height == 720u &&
                copied_format26_fetch.pitch == 1280u &&
                copied_format26_fetch.byte_length == 0x730000u &&
                copied_format26_fetch.tiled &&
                copied_format26_fetch.swizzle == 0x688u &&
                copied_format26_fetch.mag_filter == 0u &&
                copied_format26_fetch.min_filter == 0u,
            "captured 1280x720 format-26 Copy/Convert fetch was rejected or misdecoded");
    shift::xbox::CapturedCopyState retail_format26_copy{};
    retail_format26_copy.sample_select = 6;
    retail_format26_copy.destination_base = 0x0BE19000u;
    retail_format26_copy.destination_pitch = 1280;
    retail_format26_copy.destination_height = 720;
    retail_format26_copy.destination_format = 26;
    retail_format26_copy.destination_endian = 1;
    retail_format26_copy.destination_number_format = 2;
    retail_format26_copy.destination_exp_bias = 11;
    retail_format26_copy.color_clear_enable = true;
    retail_format26_copy.depth_clear_enable = true;
    shift::xbox::CapturedRasterState retail_format26_source{};
    retail_format26_source.width = 2560;
    retail_format26_source.height = 1440;
    retail_format26_source.surface_pitch = 1280;
    retail_format26_source.sample_count = 4;
    retail_format26_source.color_base_tiles = 0;
    retail_format26_source.guest_color_format = 12;
    retail_format26_source.depth_base_tiles = 1024;
    require(shift::xbox::captured_format26_copy_matches_texture_fetch(
                copied_format26_fetch, retail_format26_copy,
                retail_format26_source),
            "retail format-26 fetch did not match the captured 4x all-sample source layout");
    auto logical_format26_source = retail_format26_source;
    logical_format26_source.width = 1280;
    logical_format26_source.height = 720;
    require(!shift::xbox::captured_format26_copy_matches_texture_fetch(
                copied_format26_fetch, retail_format26_copy,
                logical_format26_source),
            "format-26 all-sample matching accepted a logical-size source raster");
    auto single_sample_format26_source = retail_format26_source;
    single_sample_format26_source.sample_count = 1;
    require(!shift::xbox::captured_format26_copy_matches_texture_fetch(
                copied_format26_fetch, retail_format26_copy,
                single_sample_format26_source),
            "format-26 all-sample matching accepted a single-sample source");
    uint32_t non_integer_format26_descriptor[6];
    std::copy(std::begin(copied_format26_descriptor),
              std::end(copied_format26_descriptor),
              std::begin(non_integer_format26_descriptor));
    non_integer_format26_descriptor[3] &= ~1u;
    require(!shift::xbox::decode_captured_texture_fetch(
                non_integer_format26_descriptor, &copied_format26_fetch,
                &error),
            "captured format-26 fetch accepted unverified fractional mode");

    const uint32_t retail_tiled_format31_descriptor[] = {
        0x80424956u, 0x0CD6409Fu, 0x00000000u,
        0x01281691u, 0x00000003u, 0x00000210u,
    };
    shift::xbox::CapturedTextureFetch retail_tiled_format31_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                retail_tiled_format31_descriptor,
                &retail_tiled_format31_fetch, &error) &&
                retail_tiled_format31_fetch.guest_address == 0x0CD64000u &&
                retail_tiled_format31_fetch.format == 31u &&
                retail_tiled_format31_fetch.endian_mode == 2u &&
                retail_tiled_format31_fetch.width == 1u &&
                retail_tiled_format31_fetch.height == 1u &&
                retail_tiled_format31_fetch.pitch == 32u &&
                retail_tiled_format31_fetch.byte_length == 4096u &&
                retail_tiled_format31_fetch.tiled &&
                !retail_tiled_format31_fetch.packed_mips,
            "captured retail draw-12 tiled format-31 descriptor was rejected");
    std::vector<uint8_t> retail_tiled_format31_bytes(4096u);
    retail_tiled_format31_bytes[0] = 0x34u;
    retail_tiled_format31_bytes[1] = 0x00u;
    retail_tiled_format31_bytes[2] = 0x38u;
    retail_tiled_format31_bytes[3] = 0x00u;
    std::vector<uint8_t> untiled_format31;
    require(shift::xbox::untile_captured_texture_2d(
                retail_tiled_format31_fetch,
                retail_tiled_format31_bytes.data(),
                retail_tiled_format31_bytes.size(), &untiled_format31,
                &error) &&
                untiled_format31 ==
                    std::vector<uint8_t>{0x00u, 0x38u, 0x00u, 0x34u},
            "captured tiled format-31 base texel did not untile to RG16F bytes");
    uint32_t mipmapped_format31_descriptor[6];
    std::copy(std::begin(copied_format31_descriptor),
              std::end(copied_format31_descriptor),
              std::begin(mipmapped_format31_descriptor));
    mipmapped_format31_descriptor[4] = 1u << 6;
    mipmapped_format31_descriptor[5] =
        (1u << 9) | ((0x0CC87000u >> 12) << 12);
    require(!shift::xbox::decode_captured_texture_fetch(
                mipmapped_format31_descriptor, &copied_format31_fetch, &error),
            "format-31 Copy/Convert cache descriptor unexpectedly accepted a mip range");

    const uint32_t captured_movie_r8_descriptor[] = {
        0x0A024802u, 0x05F60002u, 0x0059E4FFu,
        0x00A81400u, 0x00000003u, 0x00000210u,
    };
    shift::xbox::CapturedTextureFetch movie_r8_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_movie_r8_descriptor, &movie_r8_fetch, &error) &&
                movie_r8_fetch.guest_address == 0x05F60000u &&
                movie_r8_fetch.format == 2 && movie_r8_fetch.endian_mode == 0 &&
                movie_r8_fetch.width == 1280 && movie_r8_fetch.height == 720 &&
                movie_r8_fetch.pitch == 1280 &&
                movie_r8_fetch.byte_length == 1280u * 720u &&
                !movie_r8_fetch.tiled && movie_r8_fetch.swizzle == 0xA00u,
            "captured retail Bink R8 plane descriptor was rejected or misdecoded");
    shift::xbox::CapturedTextureSampling movie_r8_sampling{};
    require(shift::xbox::decode_captured_texture_sampling(
                movie_r8_fetch, &movie_r8_sampling, &error) &&
                movie_r8_sampling.swizzle ==
                    std::array<shift::xbox::TextureComponent, 4>{
                        shift::xbox::TextureComponent::X,
                        shift::xbox::TextureComponent::X,
                        shift::xbox::TextureComponent::X,
                        shift::xbox::TextureComponent::One},
            "captured retail Bink R8 plane does not replicate its red channel to RGB");
    uint32_t small_movie_r8_descriptor[6];
    std::copy(std::begin(captured_movie_r8_descriptor),
              std::end(captured_movie_r8_descriptor),
              std::begin(small_movie_r8_descriptor));
    small_movie_r8_descriptor[0] =
        (small_movie_r8_descriptor[0] & ~(0x1FFu << 22)) | (1u << 22);
    small_movie_r8_descriptor[2] = 1u | (1u << 13);
    shift::xbox::CapturedTextureFetch small_movie_r8_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                small_movie_r8_descriptor, &small_movie_r8_fetch, &error) &&
                small_movie_r8_fetch.width == 2 &&
                small_movie_r8_fetch.height == 2 &&
                small_movie_r8_fetch.pitch == 32 &&
                small_movie_r8_fetch.byte_length == 64,
            "captured linear R8 texture did not retain its padded row pitch");
    std::vector<uint8_t> movie_r8_bytes(64, 0);
    movie_r8_bytes[0] = 0x20;
    movie_r8_bytes[1] = 0x40;
    movie_r8_bytes[32] = 0x60;
    movie_r8_bytes[33] = 0x80;
    std::vector<uint8_t> movie_r8_rgba;
    require(shift::xbox::untile_captured_texture_2d(
                small_movie_r8_fetch, movie_r8_bytes.data(), movie_r8_bytes.size(),
                &movie_r8_rgba, &error) &&
                movie_r8_rgba == std::vector<uint8_t>{
                    0x20,0x20,0x20,0x20, 0x40,0x40,0x40,0x40,
                    0x60,0x60,0x60,0x60, 0x80,0x80,0x80,0x80},
            "captured linear R8 texture did not expand replicated Xenos channels");
    std::vector<uint8_t> movie_r8_native;
    require(shift::xbox::copy_captured_r8_texture_2d(
                small_movie_r8_fetch, movie_r8_bytes.data(), movie_r8_bytes.size(),
                &movie_r8_native, &error) &&
                movie_r8_native == std::vector<uint8_t>{0x20, 0x40, 0x60, 0x80},
            "captured retail Bink R8 plane did not preserve its native one-byte texels");
    const uint8_t tight_movie_r8_bytes[] = {0xA0, 0xB0, 0xC0, 0xD0};
    auto tight_movie_r8_fetch = small_movie_r8_fetch;
    tight_movie_r8_fetch.pitch = tight_movie_r8_fetch.width;
    tight_movie_r8_fetch.byte_length = sizeof(tight_movie_r8_bytes);
    uint8_t* reusable_movie_r8_buffer = movie_r8_native.data();
    require(shift::xbox::copy_captured_r8_texture_2d(
                tight_movie_r8_fetch, tight_movie_r8_bytes,
                sizeof(tight_movie_r8_bytes), &movie_r8_native, &error) &&
                movie_r8_native.data() == reusable_movie_r8_buffer &&
                movie_r8_native == std::vector<uint8_t>{0xA0, 0xB0, 0xC0, 0xD0},
            "captured tightly packed Bink R8 plane did not use its contiguous buffer");

    const uint32_t retail_narrow_rgba8_descriptor[] = {
        0x804048FEu, 0x0A079086u, 0x0007E003u,
        0x06A80C14u, 0x00000C03u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch retail_narrow_rgba8{};
    require(shift::xbox::decode_captured_texture_fetch(
                retail_narrow_rgba8_descriptor, &retail_narrow_rgba8, &error) &&
                retail_narrow_rgba8.guest_address == 0x0A079000u &&
                retail_narrow_rgba8.format == 6 &&
                retail_narrow_rgba8.width == 4 && retail_narrow_rgba8.height == 64 &&
                retail_narrow_rgba8.pitch == 32 &&
                retail_narrow_rgba8.byte_length == 32u * 64u * 4u,
            "captured retail draw-29 padded RGBA8 descriptor was rejected or mis-sized");
    std::vector<uint8_t> retail_narrow_tiled(retail_narrow_rgba8.byte_length);
    const auto retail_narrow_tiled_offset = [](uint32_t x, uint32_t y,
                                                uint32_t pitch) {
        const uint64_t outer_blocks =
            ((static_cast<uint64_t>(y >> 5) * (pitch >> 5)) + (x >> 5)) << 6;
        const uint64_t inner_blocks = (((y >> 1) & 0x7u) << 3) | (x & 0x7u);
        const uint64_t outer_inner_bytes = (outer_blocks | inner_blocks) << 2;
        const uint32_t bank = (y >> 4) & 1u;
        const uint32_t pipe = ((x >> 3) & 3u) ^ (((y >> 3) & 1u) << 1);
        return static_cast<size_t>(
            (static_cast<uint64_t>(y & 1u) << 4) |
            (static_cast<uint64_t>(pipe) << 6) |
            (static_cast<uint64_t>(bank) << 11) | (outer_inner_bytes & 0xFu) |
            (((outer_inner_bytes >> 4) & 1u) << 5) |
            (((outer_inner_bytes >> 5) & 7u) << 8) |
            (outer_inner_bytes >> 8 << 12));
    };
    const size_t retail_narrow_sample = retail_narrow_tiled_offset(16, 0, 32);
    retail_narrow_tiled[retail_narrow_sample] = 0x11;
    retail_narrow_tiled[retail_narrow_sample + 1] = 0x22;
    retail_narrow_tiled[retail_narrow_sample + 2] = 0x33;
    retail_narrow_tiled[retail_narrow_sample + 3] = 0x44;
    std::vector<uint8_t> retail_narrow_linear;
    require(shift::xbox::untile_captured_texture_2d(
                retail_narrow_rgba8, retail_narrow_tiled.data(),
                retail_narrow_tiled.size(), &retail_narrow_linear, &error) &&
                retail_narrow_linear.size() == 4u * 64u * 4u &&
                retail_narrow_linear[0] == 0x44 &&
                retail_narrow_linear[1] == 0x33 &&
                retail_narrow_linear[2] == 0x22 &&
                retail_narrow_linear[3] == 0x11,
            "captured retail draw-29 padded RGBA8 texels did not untile");

    const uint32_t captured_dxt2_3_descriptor[] = {
        0x8800D8FEu, 0x09E57053u, 0x003FE3FFu,
        0x01280D10u, 0x00000003u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch dxt2_3_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_dxt2_3_descriptor, &dxt2_3_fetch, &error) &&
                dxt2_3_fetch.guest_address == 0x09E57000u &&
                dxt2_3_fetch.format == 19 && dxt2_3_fetch.endian_mode == 1 &&
                dxt2_3_fetch.width == 1024 && dxt2_3_fetch.height == 512 &&
                dxt2_3_fetch.pitch == 1024 &&
                dxt2_3_fetch.byte_length == 1024u * 512u,
            "captured retail DXT2/3 fetch descriptor was rejected or misdecoded");
    uint32_t captured_linear_dxt2_3_descriptor[6];
    std::copy(std::begin(captured_dxt2_3_descriptor),
              std::end(captured_dxt2_3_descriptor),
              std::begin(captured_linear_dxt2_3_descriptor));
    captured_linear_dxt2_3_descriptor[0] &= ~0x80000000u;
    shift::xbox::CapturedTextureFetch linear_dxt2_3_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_linear_dxt2_3_descriptor, &linear_dxt2_3_fetch, &error) &&
                linear_dxt2_3_fetch.format == 19 &&
                linear_dxt2_3_fetch.endian_mode == 1 &&
                !linear_dxt2_3_fetch.tiled &&
                linear_dxt2_3_fetch.width == 1024 &&
                linear_dxt2_3_fetch.height == 512 &&
                linear_dxt2_3_fetch.pitch == 1024 &&
                linear_dxt2_3_fetch.byte_length == 1024u * 512u,
            "captured retail linear DXT2/3 fetch descriptor was rejected or misdecoded");
    shift::xbox::CapturedTextureSampling dxt2_3_sampling{};
    require(shift::xbox::decode_captured_texture_sampling(
                dxt2_3_fetch, &dxt2_3_sampling, &error),
            "captured retail DXT2/3 sampler state was rejected");

    shift::xbox::CapturedTextureSampling texture_sampling{};
    require(shift::xbox::decode_captured_texture_sampling(
                texture_fetch, &texture_sampling, &error),
            "captured texture sampling state was rejected");
    require(texture_sampling.swizzle == std::array<shift::xbox::TextureComponent, 4>{
                shift::xbox::TextureComponent::Z,
                shift::xbox::TextureComponent::Y,
                shift::xbox::TextureComponent::X,
                shift::xbox::TextureComponent::W},
            "captured texture swizzle selectors changed");
    require(texture_sampling.signs == std::array<shift::xbox::TextureSign, 4>{
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Unsigned},
            "captured texture channel encodings changed");
    require(texture_sampling.clamps == std::array<shift::xbox::TextureClamp, 3>{
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::Repeat},
            "captured texture clamp modes changed");
    require(texture_sampling.mag_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.min_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.mip_filter == shift::xbox::TextureFilter::BaseMap &&
                texture_sampling.anisotropy == shift::xbox::TextureAnisotropy::Disabled &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrBlack &&
                !texture_sampling.border_alpha_known,
            "captured texture sampler interpretation changed");

    const shift::xbox::CapturedRasterRegisters captured_raster_registers{
        0x14000500u, 0x00010000u, 0x000002D0u, 0x00000004u,
        0x00700770u, 0x0000000Fu, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x02D00500u, 0x07010706u,
    };
    shift::xbox::CapturedRasterState raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                captured_raster_registers, &raster_state, &error),
            "captured Xbox target and raster state was rejected");
    require(raster_state.width == 1280 && raster_state.height == 720 &&
                raster_state.surface_pitch == 1280 &&
                raster_state.sample_count == 1 && raster_state.color_base_tiles == 0 &&
                raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Gamma &&
                raster_state.depth_base_tiles == 720 &&
                raster_state.depth_format ==
                    shift::xbox::CapturedDepthTargetFormat::D24S8,
            "captured Xbox render target interpretation changed");
    require(raster_state.color_write_mask == 0xFu && raster_state.viewport_y_flipped &&
                !raster_state.depth_test_enabled && !raster_state.depth_write_enabled &&
                !raster_state.stencil_test_enabled &&
                raster_state.blend_control_0 == 0x07010706u,
            "captured Xbox depth or color write state changed");
    require(raster_state.scissor_x0 == 0 && raster_state.scissor_y0 == 0 &&
                raster_state.scissor_x1 == 1280 && raster_state.scissor_y1 == 720 &&
                raster_state.scissor_has_area,
            "captured Xbox scissor bounds changed");
    auto depth_only_registers = captured_raster_registers;
    depth_only_registers.surface_info = 0x0A020280u;
    depth_only_registers.color_info = 0u;
    depth_only_registers.depth_info = 0x000002D0u;
    depth_only_registers.mode_control = 5u;
    depth_only_registers.depth_control = 0x00008701u;
    depth_only_registers.color_mask = 0x0000000Fu;
    depth_only_registers.blend_control_0 = 0x07010706u;
    depth_only_registers.stencil_refmask = 0x00FF0000u;
    depth_only_registers.setup_mode_control = 0x00010000u;
    require(shift::xbox::decode_captured_raster_state(
                depth_only_registers, &raster_state, &error, 1280, 720) &&
                raster_state.depth_only && raster_state.width == 1280 &&
                raster_state.height == 720 && raster_state.surface_pitch == 640 &&
                raster_state.sample_count == 4 && raster_state.color_base_tiles == 0 &&
                raster_state.color_write_mask == 0 &&
                raster_state.depth_base_tiles == 720 &&
                !raster_state.depth_test_enabled && !raster_state.depth_write_enabled &&
                raster_state.stencil_test_enabled &&
                raster_state.stencil_refmask == 0x00FF0000u &&
                raster_state.scissor_has_area,
            "run-060 Xenos depth-only target was not normalized to no color writes");
    // Retail menu draws emit RB_BLENDCONTROL0 = 0x00010701 (ONE plus inverted
    // source alpha on both sub-blends, i.e. premultiplied alpha). The raster
    // decoder used to whitelist only three whole-register values and rejected
    // it, which failed the containing frame.
    auto premultiplied_blend_registers = captured_raster_registers;
    premultiplied_blend_registers.blend_control_0 = 0x00010701u;
    require(shift::xbox::decode_captured_raster_state(
                premultiplied_blend_registers, &raster_state, &error) &&
                raster_state.blend_control_0 == 0x00010701u,
            "retail premultiplied-alpha blend control was rejected");
    // A factor index outside the Xenos subset must still be rejected, so the
    // widened acceptance does not turn into "accept anything".
    auto unsupported_blend_registers = captured_raster_registers;
    unsupported_blend_registers.blend_control_0 = 0x00011F01u;
    require(!shift::xbox::decode_captured_raster_state(
                unsupported_blend_registers, &raster_state, &error) &&
                error == "unsupported captured target or raster state",
            "an unsupported blend factor was accepted");
    auto partial_viewport_registers = captured_raster_registers;
    partial_viewport_registers.viewport_x_scale = 0x43780000u;  // 248
    partial_viewport_registers.viewport_x_offset = 0x44200000u; // 640
    partial_viewport_registers.viewport_y_scale = 0xC0800000u;  // -4
    partial_viewport_registers.viewport_y_offset = 0x43F10000u; // 482
    partial_viewport_registers.screen_scissor_tl = 0x00000000u;
    partial_viewport_registers.screen_scissor_br = 0x20002000u;
    partial_viewport_registers.window_offset = 0x00000000u;
    partial_viewport_registers.window_scissor_tl = 0x01DE0188u;
    partial_viewport_registers.window_scissor_br = 0x01E60378u;
    require(!shift::xbox::decode_captured_raster_state(
                partial_viewport_registers, &raster_state, &error) &&
                error == "partial captured viewport requires a known target extent",
            "partial Xenos viewport was accepted without a target extent");
    require(shift::xbox::decode_captured_raster_state(
                partial_viewport_registers, &raster_state, &error, 1280, 720) &&
                raster_state.width == 1280 && raster_state.height == 720 &&
                raster_state.viewport_x == 392.0f &&
                raster_state.viewport_y == 486.0f &&
                raster_state.viewport_width == 496.0f &&
                raster_state.viewport_height == -8.0f &&
                raster_state.scissor_x0 == 392 && raster_state.scissor_y0 == 478 &&
                raster_state.scissor_x1 == 888 && raster_state.scissor_y1 == 486 &&
                raster_state.scissor_has_area,
            "run-058 partial Xenos viewport or scissor was decoded incorrectly");
    require(raster_state.cull_mode ==
                    shift::xbox::CapturedRasterState::CullMode::None &&
                raster_state.front_face_ccw && raster_state.setup_mode_control == 0,
            "captured Xenos default cull/front-face state changed");
    auto cull_raster = captured_raster_registers;
    cull_raster.setup_mode_control = 1u;
    require(shift::xbox::decode_captured_raster_state(
                cull_raster, &raster_state, &error) &&
                raster_state.cull_mode ==
                    shift::xbox::CapturedRasterState::CullMode::Front &&
                raster_state.front_face_ccw,
            "captured Xenos front-face culling was not decoded");
    cull_raster.setup_mode_control = 2u;
    require(shift::xbox::decode_captured_raster_state(
                cull_raster, &raster_state, &error) &&
                raster_state.cull_mode ==
                    shift::xbox::CapturedRasterState::CullMode::Back &&
                raster_state.front_face_ccw,
            "captured Xenos back-face culling was not decoded");
    cull_raster.setup_mode_control = 4u;
    require(shift::xbox::decode_captured_raster_state(
                cull_raster, &raster_state, &error) &&
                raster_state.cull_mode ==
                    shift::xbox::CapturedRasterState::CullMode::None &&
                !raster_state.front_face_ccw,
            "captured Xenos clockwise front-face state was not decoded");
    cull_raster.setup_mode_control = 3u;
    require(!shift::xbox::decode_captured_raster_state(
                cull_raster, &raster_state, &error) &&
                error == "unsupported captured front-and-back culling",
            "unsupported Xenos front-and-back culling was not rejected");
    require(shift::xbox::decode_captured_raster_state(
                captured_raster_registers, &raster_state, &error),
            "captured Xenos raster state could not be restored after cull cases");

    const shift::xbox::CapturedRasterRegisters captured_noop_registers{
        0x14000500u, 0x00000000u, 0x000002D0u, 0x00000004u,
        0x00000000u, 0x00000000u, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x00100010u, 0x07060706u,
    };
    shift::xbox::CapturedRasterState captured_noop_state{};
    require(shift::xbox::decode_captured_raster_state(
                captured_noop_registers, &captured_noop_state, &error) &&
                captured_noop_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Linear &&
                captured_noop_state.blend_control_0 == 0x07060706u &&
                !captured_noop_state.depth_test_enabled &&
                !captured_noop_state.depth_write_enabled &&
                !captured_noop_state.stencil_test_enabled &&
                captured_noop_state.scissor_x1 == 16 &&
                captured_noop_state.scissor_y1 == 16 &&
                shift::xbox::captured_draw_has_no_framebuffer_effects(
                    captured_noop_state),
            "captured zero-mask 0x07060706 Xenos raster state was not decoded as a no-op");

    shift::xbox::CapturedRasterRegisters live_raster_registers{
        0x0A020280u, 0x00010000u, 0x000002D0u, 0x00000004u,
        0x00008777u, 0x0000FFFFu, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x20002000u, 0x00010001u,
    };
    shift::xbox::CapturedRasterState live_raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.width == 1280 &&
                live_raster_state.height == 720 &&
                live_raster_state.surface_pitch == 640 &&
                live_raster_state.sample_count == 4 &&
                live_raster_state.color_write_mask == 0xFu &&
                live_raster_state.depth_test_enabled &&
                live_raster_state.depth_write_enabled &&
                live_raster_state.stencil_test_enabled &&
                live_raster_state.blend_control_0 == 0x00010001u,
            "live 4x-MSAA raster contract was rejected");

    auto no_effect_raster = live_raster_state;
    no_effect_raster.color_write_mask = 0;
    no_effect_raster.depth_test_enabled = false;
    no_effect_raster.depth_write_enabled = false;
    no_effect_raster.stencil_test_enabled = false;
    require(shift::xbox::captured_draw_has_no_framebuffer_effects(no_effect_raster),
            "zero-write captured raster state was not identified as a no-op");
    no_effect_raster.depth_write_enabled = true;
    require(!shift::xbox::captured_draw_has_no_framebuffer_effects(no_effect_raster),
            "depth-writing captured draw was incorrectly identified as a no-op");

    live_raster_registers.color_info = 0x00000000u;
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Linear,
            "captured linear RGBA8 Xenos color target was rejected");
    live_raster_registers.color_info = 0x00020000u;
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgb10A2Unorm,
            "captured Xenos 2_10_10_10 target format was rejected");
    live_raster_registers.color_info = 0x00030000u;
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgb10A2Float,
            "captured Xenos 2_10_10_10_FLOAT target format was rejected");
    live_raster_registers.color_info = 0x000C0000u;
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgb10A2Float,
            "captured Xenos 2_10_10_10_FLOAT_AS_16_16_16_16 target was rejected");
    auto captured_rg16_registers = live_raster_registers;
    captured_rg16_registers.surface_info = 0x04000140u;
    captured_rg16_registers.color_info = 0x00060000u;
    captured_rg16_registers.depth_info = 0x00000400u;
    captured_rg16_registers.mode_control = 0x00000004u;
    captured_rg16_registers.depth_control = 0x00700730u;
    captured_rg16_registers.color_mask = 0x0000000Fu;
    captured_rg16_registers.setup_mode_control = 0x00218006u;
    captured_rg16_registers.viewport_x_scale = 0x42F30000u;
    captured_rg16_registers.viewport_x_offset = 0x42F30000u;
    captured_rg16_registers.viewport_y_scale = 0xC2F30000u;
    captured_rg16_registers.viewport_y_offset = 0x42F30000u;
    captured_rg16_registers.window_scissor_br = 0x00F300F3u;
    captured_rg16_registers.blend_control_0 = 0x00010001u;
    uint32_t inferred_width = 0;
    uint32_t inferred_height = 0;
    require(shift::xbox::infer_captured_raster_extent(
                captured_rg16_registers, 1280, 720, &inferred_width,
                &inferred_height, &error) &&
                inferred_width == 320 && inferred_height == 243,
            "captured 320x243 offscreen extent used the presenter aspect ratio");
    require(shift::xbox::decode_captured_raster_state(
                captured_rg16_registers, &live_raster_state, &error, 320, 243) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rg16Float &&
                live_raster_state.surface_pitch == 320 &&
                live_raster_state.width == 320 && live_raster_state.height == 243 &&
                live_raster_state.sample_count == 1 &&
                live_raster_state.scissor_x1 == 243 &&
                live_raster_state.scissor_y1 == 243,
            "captured Redmi 16_16_FLOAT render target tuple was rejected or misdecoded");
    shift::xbox::CapturedEdramSampleAddress rg16_edram_address{};
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 0, 0, &rg16_edram_address,
                &error) &&
                rg16_edram_address.byte_offset == 0 &&
                rg16_edram_address.bytes_per_sample == 4,
            "captured 16_16_FLOAT target was not mapped as 32bpp EDRAM");
    const std::array<std::array<uint32_t, 4>, 6> captured_downsample_extents = {{
        {0x018000A0u, 0x42220000u, 0x00510051u, 81u},
        {0x00080050u, 0x41580000u, 0x001B001Bu, 27u},
        {0x00080050u, 0x40900000u, 0x00090009u, 9u},
        {0x00080050u, 0x3FC00000u, 0x00030003u, 3u},
        {0x00080050u, 0x3F000000u, 0x00010001u, 1u},
        {0x00080050u, 0x3F000000u, 0x00010001u, 1u},
    }};
    for (const auto& expected : captured_downsample_extents) {
        auto downsample_registers = captured_rg16_registers;
        downsample_registers.surface_info = expected[0];
        downsample_registers.viewport_x_scale = expected[1];
        downsample_registers.viewport_x_offset = expected[1];
        downsample_registers.viewport_y_scale = expected[1] | 0x80000000u;
        downsample_registers.viewport_y_offset = expected[1];
        downsample_registers.window_scissor_br = expected[2];
        require(shift::xbox::infer_captured_raster_extent(
                    downsample_registers, 1280, 720, &inferred_width,
                    &inferred_height, &error) &&
                    inferred_width == (expected[0] & 0x3FFFu) &&
                    inferred_height == expected[3],
                "captured downsample viewport/scissor extent was not preserved");
    }
    live_raster_registers.color_info = 0x00040000u;
    require(!shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error),
            "unsupported Xenos color target format was accepted");

    auto captured_float_target_registers = live_raster_registers;
    captured_float_target_registers.surface_info = 0x14020500u;
    captured_float_target_registers.color_info = 0x00030000u;
    captured_float_target_registers.depth_info = 0x00000400u;
    captured_float_target_registers.mode_control = 0x00000004u;
    captured_float_target_registers.depth_control = 0x00008777u;
    captured_float_target_registers.color_mask = 0x0000FFFFu;
    captured_float_target_registers.viewport_x_scale = 0x44200000u;
    captured_float_target_registers.viewport_x_offset = 0x44200000u;
    captured_float_target_registers.viewport_y_scale = 0xC3000000u;
    captured_float_target_registers.viewport_y_offset = 0x43000000u;
    captured_float_target_registers.screen_scissor_tl = 0x00000000u;
    captured_float_target_registers.screen_scissor_br = 0x20002000u;
    captured_float_target_registers.window_offset = 0x00000000u;
    captured_float_target_registers.window_scissor_tl = 0x00000000u;
    captured_float_target_registers.window_scissor_br = 0x20002000u;
    captured_float_target_registers.blend_control_0 = 0x00010001u;
    require(shift::xbox::decode_captured_raster_state(
                captured_float_target_registers, &live_raster_state, &error,
                2560, 1440) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgb10A2Float &&
                live_raster_state.surface_pitch == 1280 &&
                live_raster_state.sample_count == 4 &&
                live_raster_state.width == 2560 &&
                live_raster_state.height == 1440 &&
                live_raster_state.viewport_x == 0.0f &&
                live_raster_state.viewport_y == 256.0f &&
                live_raster_state.viewport_width == 1280.0f &&
                live_raster_state.viewport_height == -256.0f,
            "captured 4x float target/viewport from the Redmi draw was decoded incorrectly");
    require(live_raster_state.guest_color_format == 3u,
            "captured Xenos color format 3 was not retained separately from its Vulkan format");

    shift::xbox::CapturedEdramSampleAddress edram_address{};
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.sample_index_in_tile == 0 &&
                edram_address.byte_offset == 0 &&
                edram_address.bytes_per_sample == 4,
            "captured 4x Xenos color sample 0 did not map to EDRAM base");
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 0, 1, &edram_address, &error) &&
                edram_address.sample_index_in_tile == 1 &&
                edram_address.byte_offset == 4,
            "captured 4x Xenos color sample 1 did not map across X samples");
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 0, 2, &edram_address, &error) &&
                edram_address.sample_index_in_tile == 80 &&
                edram_address.byte_offset == 320,
            "captured 4x Xenos color sample 2 did not map across Y samples");
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 40, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 1 &&
                edram_address.sample_index_in_tile == 0 &&
                edram_address.byte_offset == 5120,
            "captured 4x Xenos color sample did not advance to the next EDRAM tile");
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 8, 0, &edram_address, &error) &&
                edram_address.tile_index == 32 &&
                edram_address.byte_offset == 32u * 5120u,
            "captured 4x Xenos color target did not advance by its tile-row pitch");
    require(shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, true, 0, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 1024 &&
                edram_address.sample_index_in_tile == 40 &&
                edram_address.byte_offset == (1024u * 1280u + 40u) * 4u,
            "captured Xenos depth sample did not apply its half-tile swap");
    auto wrapped_edram_target = live_raster_state;
    wrapped_edram_target.color_base_tiles = 2047;
    require(shift::xbox::captured_xenos_edram_sample_address(
                wrapped_edram_target, false, 40, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.byte_offset == 0,
            "captured Xenos EDRAM tile addressing did not wrap at tile 2048");
    auto single_sample_edram_target = live_raster_state;
    single_sample_edram_target.width = 1280;
    single_sample_edram_target.height = 720;
    single_sample_edram_target.surface_pitch = 1280;
    single_sample_edram_target.sample_count = 1;
    single_sample_edram_target.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
    require(shift::xbox::captured_xenos_edram_sample_address(
                single_sample_edram_target, false, 1, 0, 0,
                &edram_address, &error) &&
                edram_address.byte_offset == 4,
            "captured 1x Xenos pixel did not retain its linear EDRAM sample slot");

    auto retail_4x_edram_view = single_sample_edram_target;
    retail_4x_edram_view.surface_pitch = 640;
    retail_4x_edram_view.sample_count = 4;
    std::vector<shift::xbox::CapturedEdramTileAlias> edram_alias_tiles;
    require(shift::xbox::captured_xenos_edram_alias_tiles(
                retail_4x_edram_view, single_sample_edram_target, false,
                &edram_alias_tiles, &error) &&
                edram_alias_tiles.size() == 720 &&
                edram_alias_tiles.front().tile_index == 0 &&
                edram_alias_tiles.front().source_tile_x == 0 &&
                edram_alias_tiles.front().source_tile_y == 0 &&
                edram_alias_tiles.front().destination_tile_x == 0 &&
                edram_alias_tiles.front().destination_tile_y == 0 &&
                edram_alias_tiles[16].tile_index == 16 &&
                edram_alias_tiles[16].source_tile_x == 0 &&
                edram_alias_tiles[16].source_tile_y == 1 &&
                edram_alias_tiles[16].destination_tile_x == 0 &&
                edram_alias_tiles[16].destination_tile_y == 1,
            "captured 4x-to-1x EDRAM view did not map shared physical tiles");
    for (const bool depth_target : {false, true}) {
        for (uint32_t sample_in_tile = 0; sample_in_tile < 80u * 16u;
             ++sample_in_tile) {
            shift::xbox::CapturedEdramSampleCoordinates source_coordinates{};
            shift::xbox::CapturedEdramSampleCoordinates destination_coordinates{};
            shift::xbox::CapturedEdramSampleAddress source_address{};
            shift::xbox::CapturedEdramSampleAddress destination_address{};
            require(shift::xbox::captured_xenos_edram_sample_coordinates(
                        retail_4x_edram_view, depth_target, 0, 0,
                        sample_in_tile, &source_coordinates, &error) &&
                    shift::xbox::captured_xenos_edram_sample_coordinates(
                        single_sample_edram_target, depth_target, 0, 0,
                        sample_in_tile, &destination_coordinates, &error) &&
                    shift::xbox::captured_xenos_edram_sample_address(
                        retail_4x_edram_view, depth_target,
                        source_coordinates.x, source_coordinates.y,
                        source_coordinates.sample_index, &source_address,
                        &error) &&
                    shift::xbox::captured_xenos_edram_sample_address(
                        single_sample_edram_target, depth_target,
                        destination_coordinates.x, destination_coordinates.y,
                        destination_coordinates.sample_index,
                        &destination_address, &error) &&
                    source_address.byte_offset == destination_address.byte_offset,
                    "4x-to-1x alias sample did not preserve its physical EDRAM address");
        }
    }
    auto retail_oversized_4x_layout = retail_4x_edram_view;
    retail_oversized_4x_layout.width = 2560;
    retail_oversized_4x_layout.height = 1440;
    retail_oversized_4x_layout.surface_pitch = 1280;
    retail_oversized_4x_layout.color_base_tiles = 0;
    retail_oversized_4x_layout.depth_base_tiles = 1024;
    std::vector<shift::xbox::CapturedEdramRasterTile> raster_tiles;
    std::array<uint32_t, 2048> raster_tile_use_counts{};
    shift::xbox::CapturedEdramRasterTile first_tile_zero{};
    shift::xbox::CapturedEdramRasterTile second_tile_zero{};
    uint32_t tile_zero_count = 0;
    require(shift::xbox::captured_xenos_edram_raster_tiles(
                retail_oversized_4x_layout, false, &raster_tiles, &error) &&
                raster_tiles.size() == 2880,
            "retail 14-draw layout did not enumerate its 2880 wrapped raster tiles");
    for (const auto& raster_tile : raster_tiles) {
        ++raster_tile_use_counts[raster_tile.physical_tile_index];
        if (raster_tile.physical_tile_index == 0) {
            if (tile_zero_count == 0) first_tile_zero = raster_tile;
            if (tile_zero_count == 1) second_tile_zero = raster_tile;
            ++tile_zero_count;
        }
    }
    const uint32_t multiply_mapped_tile_count = static_cast<uint32_t>(
        std::count_if(raster_tile_use_counts.begin(), raster_tile_use_counts.end(),
                      [](uint32_t count) { return count > 1; }));
    require(tile_zero_count == 2 &&
                first_tile_zero.tile_x == 0 && first_tile_zero.tile_y == 0 &&
                second_tile_zero.tile_x == 0 && second_tile_zero.tile_y == 64 &&
                multiply_mapped_tile_count == 832 &&
                std::all_of(raster_tile_use_counts.begin(),
                            raster_tile_use_counts.end(),
                            [](uint32_t count) { return count == 1 || count == 2; }),
            "retail 14-draw raster grid did not preserve its 832 modulo-wrapped tile aliases");
    std::vector<shift::xbox::CapturedEdramRasterTile> depth_raster_tiles;
    std::array<uint32_t, 2048> depth_tile_use_counts{};
    shift::xbox::CapturedEdramRasterTile first_depth_tile{};
    shift::xbox::CapturedEdramRasterTile second_depth_tile{};
    uint32_t depth_tile_1024_count = 0;
    require(shift::xbox::captured_xenos_edram_raster_tiles(
                retail_oversized_4x_layout, true, &depth_raster_tiles, &error) &&
                depth_raster_tiles.size() == 2880,
            "retail draw-0 depth plane did not enumerate its wrapped raster tiles");
    for (const auto& raster_tile : depth_raster_tiles) {
        ++depth_tile_use_counts[raster_tile.physical_tile_index];
        if (raster_tile.physical_tile_index == 1024) {
            if (depth_tile_1024_count == 0) first_depth_tile = raster_tile;
            if (depth_tile_1024_count == 1) second_depth_tile = raster_tile;
            ++depth_tile_1024_count;
        }
    }
    const uint32_t multiply_mapped_depth_tile_count = static_cast<uint32_t>(
        std::count_if(depth_tile_use_counts.begin(), depth_tile_use_counts.end(),
                      [](uint32_t count) { return count > 1; }));
    require(depth_tile_1024_count == 2 &&
                first_depth_tile.tile_x == 0 && first_depth_tile.tile_y == 0 &&
                second_depth_tile.tile_x == 0 && second_depth_tile.tile_y == 64 &&
                multiply_mapped_depth_tile_count == 832 &&
                std::all_of(depth_tile_use_counts.begin(),
                            depth_tile_use_counts.end(),
                            [](uint32_t count) { return count == 1 || count == 2; }),
            "retail draw-0 depth plane modulo wrap diverged from its captured tile base");
    require(!shift::xbox::captured_xenos_edram_alias_tiles(
                retail_oversized_4x_layout, retail_4x_edram_view, false,
                &edram_alias_tiles, &error) &&
                error == "captured Xenos EDRAM alias layout wraps across the 2048-tile store",
            "oversized captured EDRAM view was mapped as a unique image layout");

    // The retail 14-draw capture's first 4x source extent wraps as a whole,
    // while the captured Copy/Convert scissor covers only 1280x256 logical
    // pixels. That bounded region has unique physical tile addresses and can
    // be mapped against the following 320x243 single-sample target.
    auto retail_transition_small_target = retail_oversized_4x_layout;
    retail_transition_small_target.width = 320;
    retail_transition_small_target.height = 243;
    retail_transition_small_target.surface_pitch = 320;
    retail_transition_small_target.sample_count = 1;
    retail_transition_small_target.color_format =
        shift::xbox::CapturedColorTargetFormat::Rg16Float;
    retail_transition_small_target.guest_color_format = 6;
    std::vector<shift::xbox::CapturedEdramRasterTile> transition_scissor_tiles;
    require(shift::xbox::captured_xenos_edram_rect_tiles(
                retail_oversized_4x_layout, false, 0, 0, 1280, 256,
                &transition_scissor_tiles, &error) &&
                transition_scissor_tiles.size() == 1024 &&
                transition_scissor_tiles.front().physical_tile_index == 0 &&
                transition_scissor_tiles.back().physical_tile_index == 1023,
            "captured transition scissor did not bound the wrapped 4x EDRAM layout");
    std::vector<shift::xbox::CapturedEdramTileAlias> transition_scissor_aliases;
    require(shift::xbox::captured_xenos_edram_rect_alias_tiles(
                retail_oversized_4x_layout, 0, 0, 1280, 256,
                retail_transition_small_target, 0, 0, 243, 243, false,
                &transition_scissor_aliases, &error) &&
                transition_scissor_aliases.size() == 64 &&
                transition_scissor_aliases.front().tile_index == 0 &&
                transition_scissor_aliases.front().source_tile_x == 0 &&
                transition_scissor_aliases.front().source_tile_y == 0 &&
                transition_scissor_aliases.front().destination_tile_x == 0 &&
                transition_scissor_aliases.front().destination_tile_y == 0 &&
                transition_scissor_aliases[4].tile_index == 4 &&
                transition_scissor_aliases[4].source_tile_x == 4 &&
                transition_scissor_aliases[4].source_tile_y == 0 &&
                transition_scissor_aliases[4].destination_tile_x == 0 &&
                transition_scissor_aliases[4].destination_tile_y == 1,
            "captured transition scissor did not map shared physical tiles between extents");
    require(shift::xbox::captured_xenos_edram_rect_alias_tiles(
                retail_oversized_4x_layout, 0, 0, 1280, 256,
                retail_transition_small_target, 0, 0, 243, 243, true,
                &transition_scissor_aliases, &error) &&
                transition_scissor_aliases.size() == 64 &&
                transition_scissor_aliases.front().tile_index == 1024,
            "captured transition depth scissor did not retain the EDRAM depth base");
    require(!shift::xbox::captured_xenos_edram_rect_tiles(
                retail_oversized_4x_layout, false, 0, 0, 1281, 256,
                &transition_scissor_tiles, &error) &&
                error == "captured Xenos EDRAM rectangle is empty or out of bounds",
            "out-of-range EDRAM scissor rectangle was accepted");

    auto small_edram_a = single_sample_edram_target;
    small_edram_a.width = 80;
    small_edram_a.height = 16;
    small_edram_a.surface_pitch = 80;
    small_edram_a.color_base_tiles = 10;
    small_edram_a.depth_base_tiles = 100;
    bool edram_layouts_disjoint = false;
    uint32_t edram_overlap_tile = 0;
    auto small_edram_same = small_edram_a;
    require(shift::xbox::captured_xenos_edram_layouts_are_tile_disjoint(
                small_edram_a, small_edram_same, &edram_layouts_disjoint,
                &edram_overlap_tile, &error) &&
                !edram_layouts_disjoint && edram_overlap_tile == 10,
            "identical Xenos EDRAM layouts were incorrectly classified as disjoint");
    auto small_edram_b = small_edram_a;
    small_edram_b.color_base_tiles = 12;
    small_edram_b.depth_base_tiles = 102;
    require(shift::xbox::captured_xenos_edram_layouts_are_tile_disjoint(
                small_edram_a, small_edram_b, &edram_layouts_disjoint,
                &edram_overlap_tile, &error) &&
                edram_layouts_disjoint && edram_overlap_tile == 2048,
            "non-overlapping Xenos color/depth tile layouts were rejected");
    auto wrapping_edram_a = small_edram_a;
    wrapping_edram_a.width = 160;
    wrapping_edram_a.surface_pitch = 160;
    wrapping_edram_a.color_base_tiles = 2047;
    auto wrapping_edram_b = small_edram_b;
    wrapping_edram_b.color_base_tiles = 0;
    require(shift::xbox::captured_xenos_edram_layouts_are_tile_disjoint(
                wrapping_edram_a, wrapping_edram_b, &edram_layouts_disjoint,
                &edram_overlap_tile, &error) &&
                !edram_layouts_disjoint && edram_overlap_tile == 0,
            "Xenos EDRAM wraparound alias was not detected");
    auto cross_plane_edram_b = small_edram_b;
    cross_plane_edram_b.color_base_tiles = 200;
    cross_plane_edram_b.depth_base_tiles = 10;
    require(shift::xbox::captured_xenos_edram_layouts_are_tile_disjoint(
                small_edram_a, cross_plane_edram_b, &edram_layouts_disjoint,
                &edram_overlap_tile, &error) &&
                !edram_layouts_disjoint && edram_overlap_tile == 10,
            "Xenos color-to-depth EDRAM alias was not detected");

    auto two_sample_edram_target = live_raster_state;
    two_sample_edram_target.width = 1280;
    two_sample_edram_target.height = 1440;
    two_sample_edram_target.surface_pitch = 1280;
    two_sample_edram_target.sample_count = 2;
    two_sample_edram_target.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    require(shift::xbox::captured_xenos_edram_sample_address(
                two_sample_edram_target, false, 0, 0, 1,
                &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.sample_index_in_tile == 80 &&
                edram_address.byte_offset == 320,
            "captured 2x Xenos sample did not map in the vertical sample lane");
    require(!shift::xbox::captured_xenos_edram_sample_address(
                live_raster_state, false, 0, 0, 4, &edram_address, &error) &&
                error == "captured Xenos EDRAM pixel or sample is out of bounds",
            "out-of-range Xenos MSAA sample was accepted");

    auto format12_registers = captured_float_target_registers;
    format12_registers.color_info = 0x000C0000u;
    shift::xbox::CapturedRasterState format12_target{};
    require(shift::xbox::decode_captured_raster_state(
                format12_registers, &format12_target, &error,
                2560, 1440) &&
                format12_target.guest_color_format == 12u &&
                format12_target.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgb10A2Float,
            "captured Xenos color format 12 lost its raw guest format");
    require(shift::xbox::captured_xenos_edram_sample_address(
                format12_target, false, 0, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.sample_index_in_tile == 0 &&
                edram_address.byte_offset == 0 &&
                edram_address.bytes_per_sample == 4,
            "captured format-12 sample 0 did not map to a 32bpp EDRAM sample");
    require(shift::xbox::captured_xenos_edram_sample_address(
                format12_target, false, 0, 0, 1, &edram_address, &error) &&
                edram_address.sample_index_in_tile == 1 &&
                edram_address.byte_offset == 4,
            "captured format-12 X sample did not advance by one 32bpp sample");
    require(shift::xbox::captured_xenos_edram_sample_address(
                format12_target, false, 0, 0, 2, &edram_address, &error) &&
                edram_address.sample_index_in_tile == 80 &&
                edram_address.byte_offset == 320,
            "captured format-12 Y sample did not advance in the 32bpp tile");
    require(shift::xbox::captured_xenos_edram_sample_address(
                format12_target, false, 40, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 1 &&
                edram_address.byte_offset == 5120,
            "captured format-12 target did not advance to the next 32bpp EDRAM tile");
    require(shift::xbox::captured_xenos_edram_sample_address(
                format12_target, false, 0, 8, 0, &edram_address, &error) &&
                edram_address.tile_index == 32 &&
                edram_address.byte_offset == 32u * 5120u,
            "captured format-12 target did not retain the 32bpp tile-row pitch");
    shift::xbox::CapturedEdramSampleCoordinates edram_coordinates{};
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                format12_target, false, 0, 0, 81, &edram_coordinates, &error) &&
                edram_coordinates.x == 0 && edram_coordinates.y == 0 &&
                edram_coordinates.sample_index == 3 &&
                shift::xbox::captured_xenos_edram_sample_address(
                    format12_target, false, edram_coordinates.x,
                    edram_coordinates.y, edram_coordinates.sample_index,
                    &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.sample_index_in_tile == 81,
            "4x color EDRAM reverse mapping did not round trip all sample lanes");
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                format12_target, false, 1, 0, 0, &edram_coordinates, &error) &&
                edram_coordinates.x == 40 && edram_coordinates.y == 0 &&
                edram_coordinates.sample_index == 0,
            "4x color EDRAM reverse mapping did not advance across tile columns");
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                format12_target, false, 31, 89, 1279,
                &edram_coordinates, &error) &&
                edram_coordinates.x == 1279 && edram_coordinates.y == 719 &&
                edram_coordinates.sample_index == 3 &&
                shift::xbox::captured_xenos_edram_sample_address(
                    format12_target, false, edram_coordinates.x,
                    edram_coordinates.y, edram_coordinates.sample_index,
                    &edram_address, &error) &&
                edram_address.tile_index == 831 &&
                edram_address.sample_index_in_tile == 1279,
            "4x EDRAM reverse mapping did not preserve the captured transition's wrapped tail tile");
    auto captured_next_target = format12_target;
    captured_next_target.width = 1280;
    captured_next_target.height = 720;
    captured_next_target.surface_pitch = 640;
    captured_next_target.color_base_tiles = 0;
    captured_next_target.depth_base_tiles = 720;
    captured_next_target.sample_count = 4;
    captured_next_target.guest_color_format = 0;
    captured_next_target.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    shift::xbox::CapturedEdramSampleCoordinates previous_layout_coordinates{};
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                format12_target, false, 16, 0, 0,
                &previous_layout_coordinates, &error) &&
                previous_layout_coordinates.x == 640 &&
                previous_layout_coordinates.y == 0 &&
                shift::xbox::captured_xenos_edram_sample_address(
                    format12_target, false,
                    previous_layout_coordinates.x,
                    previous_layout_coordinates.y,
                    previous_layout_coordinates.sample_index,
                    &edram_address, &error) &&
                edram_address.tile_index == 16 &&
                shift::xbox::captured_xenos_edram_sample_coordinates(
                    captured_next_target, false, 0, 1, 0,
                    &edram_coordinates, &error) &&
                edram_coordinates.x == 0 && edram_coordinates.y == 8 &&
                shift::xbox::captured_xenos_edram_sample_address(
                    captured_next_target, false, edram_coordinates.x,
                    edram_coordinates.y, edram_coordinates.sample_index,
                    &edram_address, &error) &&
                edram_address.tile_index == 16 &&
                edram_address.sample_index_in_tile == 0,
            "captured draw-0/draw-1 layouts did not map their shared tile sample to both logical coordinates");
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                format12_target, true, 0, 0, 40, &edram_coordinates, &error) &&
                edram_coordinates.x == 0 && edram_coordinates.y == 0 &&
                edram_coordinates.sample_index == 0 &&
                shift::xbox::captured_xenos_edram_sample_address(
                    format12_target, true, edram_coordinates.x,
                    edram_coordinates.y, edram_coordinates.sample_index,
                    &edram_address, &error) &&
                edram_address.tile_index == 1024 &&
                edram_address.sample_index_in_tile == 40,
            "depth EDRAM reverse mapping did not invert the half-tile swap");
    auto two_sample_edram_coordinates_target = format12_target;
    two_sample_edram_coordinates_target.width = 1280;
    two_sample_edram_coordinates_target.height = 1440;
    two_sample_edram_coordinates_target.surface_pitch = 1280;
    two_sample_edram_coordinates_target.sample_count = 2;
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                two_sample_edram_coordinates_target, false, 0, 0, 80,
                &edram_coordinates, &error) &&
                edram_coordinates.x == 0 && edram_coordinates.y == 0 &&
                edram_coordinates.sample_index == 1,
            "2x EDRAM reverse mapping did not recover its vertical sample lane");
    auto partial_edram_target = format12_target;
    partial_edram_target.width = 320;
    partial_edram_target.height = 243;
    partial_edram_target.surface_pitch = 320;
    partial_edram_target.sample_count = 1;
    require(shift::xbox::captured_xenos_edram_sample_coordinates(
                partial_edram_target, false, 0, 15, 2u * 80u,
                &edram_coordinates, &error) &&
                edram_coordinates.x == 0 && edram_coordinates.y == 242 &&
                edram_coordinates.sample_index == 0,
            "single-sample EDRAM reverse mapping mishandled the partial bottom tile");
    require(!shift::xbox::captured_xenos_edram_sample_coordinates(
                partial_edram_target, false, 0, 15, 3u * 80u,
                &edram_coordinates, &error) &&
                error == "captured Xenos EDRAM sample lies outside the partial edge tile",
            "single-sample EDRAM reverse mapping accepted a sample beyond the target edge");
    auto mode6_copy_source_registers = format12_registers;
    mode6_copy_source_registers.mode_control = 6u;
    shift::xbox::CapturedRasterState mode6_copy_source{};
    require(shift::xbox::decode_captured_copy_source_raster_state(
                mode6_copy_source_registers, &mode6_copy_source, &error,
                2560, 1440) &&
                mode6_copy_source.width == 2560u &&
                mode6_copy_source.height == 1440u &&
                mode6_copy_source.sample_count == 4u &&
                mode6_copy_source.guest_color_format == 12u,
            "mode-6 Copy/Convert did not retain its source EDRAM layout");
    auto wrapped_format12_target = format12_target;
    wrapped_format12_target.color_base_tiles = 2047;
    require(shift::xbox::captured_xenos_edram_sample_address(
                wrapped_format12_target, false, 40, 0, 0, &edram_address, &error) &&
                edram_address.tile_index == 0 &&
                edram_address.byte_offset == 0,
            "captured format-12 Xenos tile addressing did not wrap at tile 2048");
    auto unsupported_64bpp_target = format12_target;
    unsupported_64bpp_target.guest_color_format = 7u;
    require(!shift::xbox::captured_xenos_edram_sample_address(
                unsupported_64bpp_target, false, 0, 0, 0, &edram_address,
                &error) &&
                error ==
                    "captured 64bpp Xenos EDRAM color addressing is unsupported",
            "true 64bpp Xenos EDRAM color addressing was accepted");

    shift::xbox::GuestRasterRegisterState raster_register_state;
    shift::xbox::CapturedRasterRegisters tracked_raster_registers{};
    require(!raster_register_state.snapshot(&tracked_raster_registers, &error),
            "incomplete raster register state was accepted");
    require(raster_register_state.observed_register_mask() == 0,
            "empty raster register state reported observed writes");
    raster_register_state.apply({0x2000u, 0x12345678u});
    require(raster_register_state.observed_register_mask() == 1u,
            "partial raster register state lost its observed register mask");
    uint32_t partial_raster_valid_mask = 0;
    require(raster_register_state.snapshot_partial(
                &tracked_raster_registers, &partial_raster_valid_mask) &&
                partial_raster_valid_mask == 1u &&
                tracked_raster_registers.surface_info == 0x12345678u,
            "partial raster register snapshot lost captured register values");
    raster_register_state.reset();
    const std::array<shift::xbox::GuestRegisterWrite, 26> raster_writes{{
        {0x2000, captured_raster_registers.surface_info},
        {0x2001, captured_raster_registers.color_info},
        {0x2002, captured_raster_registers.depth_info},
        {0x2208, captured_raster_registers.mode_control},
        {0x2200, captured_raster_registers.depth_control},
        {0x2104, captured_raster_registers.color_mask},
        {0x210F, captured_raster_registers.viewport_x_scale},
        {0x2110, captured_raster_registers.viewport_x_offset},
        {0x2111, captured_raster_registers.viewport_y_scale},
        {0x2112, captured_raster_registers.viewport_y_offset},
        {0x200E, captured_raster_registers.screen_scissor_tl},
        {0x200F, captured_raster_registers.screen_scissor_br},
        {0x2080, captured_raster_registers.window_offset},
        {0x2081, captured_raster_registers.window_scissor_tl},
        {0x2082, captured_raster_registers.window_scissor_br},
        {0x2201, captured_raster_registers.blend_control_0},
        {0x2205, captured_raster_registers.setup_mode_control},
        {0x2204, 1u << 16},
        {0x2206, 1u << 8},
        {0x2318, 0x00100004u},
        {0x2319, 0x0975E000u},
        {0x231A, 0x02D00500u},
        {0x231B, 0x00000306u},
        {0x231D, 0x3F800000u},
        {0x231E, 0x00C00000u},
        {0x231F, 0x12345678u},
    }};
    for (const auto& write : raster_writes) raster_register_state.apply(write);
    raster_register_state.apply({0x3000, 0xFFFFFFFFu});
    require(raster_register_state.snapshot(&tracked_raster_registers, &error),
            "captured PM4 raster register writes did not produce complete state");
    require(tracked_raster_registers.copy_valid_mask == 0xFu &&
                tracked_raster_registers.copy_control == 0x00100004u &&
                tracked_raster_registers.copy_dest_base == 0x0975E000u &&
                tracked_raster_registers.copy_dest_pitch == 0x02D00500u &&
                tracked_raster_registers.copy_dest_info == 0x00000306u &&
                tracked_raster_registers.copy_clear_valid_mask == 7u &&
                tracked_raster_registers.depth_clear == 0x3F800000u &&
                tracked_raster_registers.color_clear == 0x00C00000u &&
                tracked_raster_registers.color_clear_lo == 0x12345678u,
            "captured Xenos EDRAM copy registers changed");
    shift::xbox::CapturedRasterState tracked_window_coordinates{};
    require(shift::xbox::decode_captured_raster_state(
                tracked_raster_registers, &tracked_window_coordinates, &error,
                1280, 720) &&
                tracked_window_coordinates.clip_control_valid &&
                tracked_window_coordinates.clip_disabled &&
                tracked_window_coordinates.viewport_transform_control_valid &&
                tracked_window_coordinates.clip_disabled_window_coordinates &&
                tracked_window_coordinates.viewport_transform_control == (1u << 8),
            "captured clip-disabled Xenos window-coordinate state was lost");
    auto bink_raster_registers = tracked_raster_registers;
    bink_raster_registers.viewport_transform_control = 1u << 10;
    require(shift::xbox::decode_captured_raster_state(
                bink_raster_registers, &tracked_window_coordinates, &error,
                1280, 720) &&
                tracked_window_coordinates.clip_disabled &&
                tracked_window_coordinates.clip_disabled_window_coordinates &&
                tracked_window_coordinates.viewport_transform_control == (1u << 10),
            "Bink clip-disabled draw with VTE_W0 did not select window-coordinate handling");
    bink_raster_registers.clip_control = 0;
    require(shift::xbox::decode_captured_raster_state(
                bink_raster_registers, &tracked_window_coordinates, &error,
                1280, 720) &&
                !tracked_window_coordinates.clip_disabled &&
                !tracked_window_coordinates.clip_disabled_window_coordinates,
            "clip-enabled draw incorrectly selected window-coordinate handling");
    shift::xbox::CapturedRasterRegisters phone_copy_registers{};
    phone_copy_registers.copy_valid_mask = 0xFu;
    phone_copy_registers.copy_control = 0x00100000u;
    phone_copy_registers.copy_dest_base = 0x0975E000u;
    phone_copy_registers.copy_dest_pitch = 0x02D00500u;
    phone_copy_registers.copy_dest_info = 0x01000300u;
    shift::xbox::CapturedCopyState phone_copy_state{};
    require(shift::xbox::decode_captured_copy_state(
                phone_copy_registers, &phone_copy_state, &error) &&
                phone_copy_state.source_select == 0 &&
                phone_copy_state.sample_select == 0 &&
                phone_copy_state.command == shift::xbox::CapturedCopyCommand::Convert &&
                phone_copy_state.destination_base == 0x0975E000u &&
                phone_copy_state.destination_pitch == 1280 &&
                phone_copy_state.destination_height == 720 &&
                phone_copy_state.destination_format == 6 &&
                phone_copy_state.destination_swap_red_blue &&
                !phone_copy_state.source_gamma,
            "live Redmi 1280x720 color Copy/Convert state was rejected");
    phone_copy_registers.color_info = 1u << 16;
    require(shift::xbox::decode_captured_copy_state(
                phone_copy_registers, &phone_copy_state, &error) &&
                phone_copy_state.source_gamma,
            "Copy/Convert source color format did not retain the captured gamma bit");
    auto captured_msaa_copy = phone_copy_registers;
    captured_msaa_copy.color_info = 0x000C0000u;
    captured_msaa_copy.copy_control = 0x00100360u;
    captured_msaa_copy.copy_dest_base = 0x0BE19000u;
    captured_msaa_copy.copy_dest_pitch = 0x02D00500u;
    captured_msaa_copy.copy_dest_info = 0x000B4D01u;
    require(shift::xbox::decode_captured_copy_state(
                captured_msaa_copy, &phone_copy_state, &error) &&
                phone_copy_state.sample_select == 6u &&
                phone_copy_state.color_clear_enable &&
                phone_copy_state.depth_clear_enable &&
                phone_copy_state.destination_endian == 1u &&
                phone_copy_state.destination_format == 26u &&
                phone_copy_state.destination_number_format == 2u &&
                phone_copy_state.destination_exp_bias == 11 &&
                phone_copy_state.destination_pitch == 1280u &&
                phone_copy_state.destination_height == 720u &&
                !phone_copy_state.destination_swap_red_blue &&
                !phone_copy_state.source_gamma,
            "captured 4x format-26 Copy/Convert register contract was rejected");
    auto captured_downsample_copy = phone_copy_registers;
    captured_downsample_copy.color_info = 0x00060000u;
    captured_downsample_copy.copy_control = 0x00100100u;
    captured_downsample_copy.copy_dest_base = 0x0CC87000u;
    captured_downsample_copy.copy_dest_pitch = 0x00F30100u;
    captured_downsample_copy.copy_dest_info = 0x0000EF82u;
    require(shift::xbox::decode_captured_copy_state(
                captured_downsample_copy, &phone_copy_state, &error) &&
                phone_copy_state.sample_select == 0u &&
                phone_copy_state.color_clear_enable &&
                !phone_copy_state.depth_clear_enable &&
                phone_copy_state.destination_endian == 2u &&
                phone_copy_state.destination_format == 31u &&
                phone_copy_state.destination_number_format == 7u &&
                phone_copy_state.destination_exp_bias == 0 &&
                phone_copy_state.destination_pitch == 256u &&
                phone_copy_state.destination_height == 243u &&
                !phone_copy_state.destination_swap_red_blue,
            "captured 16_16_FLOAT downsample Copy/Convert contract was rejected");
    auto unsupported_copy_registers = phone_copy_registers;
    unsupported_copy_registers.copy_valid_mask = 0x7u;
    require(!shift::xbox::decode_captured_copy_state(
                unsupported_copy_registers, &phone_copy_state, &error),
            "incomplete Xenos copy registers were accepted");
    unsupported_copy_registers = phone_copy_registers;
    unsupported_copy_registers.copy_control |= 1u << 10;
    require(!shift::xbox::decode_captured_copy_state(
                unsupported_copy_registers, &phone_copy_state, &error),
            "reserved Xenos copy control bits were accepted");
    unsupported_copy_registers = phone_copy_registers;
    unsupported_copy_registers.copy_dest_info |= 1u << 25;
    require(!shift::xbox::decode_captured_copy_state(
                unsupported_copy_registers, &phone_copy_state, &error),
            "reserved Xenos copy destination bits were accepted");
    unsupported_copy_registers = phone_copy_registers;
    unsupported_copy_registers.copy_control = 0x00100004u;
    require(!shift::xbox::decode_captured_copy_state(
                unsupported_copy_registers, &phone_copy_state, &error),
            "uncaptured depth-source Copy/Convert state was accepted");
    shift::xbox::CapturedRasterState tracked_raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                tracked_raster_registers, &tracked_raster_state, &error) &&
                tracked_raster_state.width == raster_state.width &&
                tracked_raster_state.height == raster_state.height &&
                tracked_raster_state.scissor_x1 == raster_state.scissor_x1 &&
                tracked_raster_state.depth_format == raster_state.depth_format &&
                tracked_raster_state.cull_mode == raster_state.cull_mode &&
                tracked_raster_state.front_face_ccw == raster_state.front_face_ccw &&
                tracked_raster_state.setup_mode_control ==
                    raster_state.setup_mode_control,
            "tracked PM4 raster state diverged from the captured draw contract");
    raster_register_state.reset();
    require(!raster_register_state.snapshot(&tracked_raster_registers, &error),
            "reset raster register state retained stale draw state");

    shift::xbox::CapturedRasterRegisters unsupported_raster = captured_raster_registers;
    unsupported_raster.window_offset = 1;
    require(!shift::xbox::decode_captured_raster_state(
                unsupported_raster, &raster_state, &error),
            "uncaptured non-zero window offset was accepted");

    std::array<uint32_t, 512 * 4> captured_float_constants{};
    const auto set_float4 = [&](uint32_t index, std::array<uint32_t, 4> value) {
        std::copy(value.begin(), value.end(), captured_float_constants.begin() + index * 4);
    };
    set_float4(0, {0x43B14000u, 0, 0, 0x44200000u});
    set_float4(1, {0, 0x42B00000u, 0, 0x43B3C000u});
    set_float4(2, {0, 0, 0x3F800000u, 0});
    set_float4(3, {0, 0, 0, 0x3F800000u});
    set_float4(64, {0x3F47FFFFu, 0x00000000u, 0x00000000u, 0xC3F9FFFFu});
    set_float4(65, {0x00000000u, 0x3FB1C71Cu, 0x00000000u, 0xC3F9FFFFu});
    set_float4(66, {0x00000000u, 0x00000000u, 0x3F8020C5u, 0xBF8020C5u});
    set_float4(67, {0x00000000u, 0x00000000u, 0x3F800000u, 0x00000000u});
    set_float4(68, {0x3EB14000u, 0x00000000u, 0x00000000u, 0x3EB14000u});
    set_float4(69, {0x00000000u, 0x3EB00000u, 0x00000000u, 0x3EB00000u});
    set_float4(254, {0x00000000u, 0x3F800000u, 0xBF800000u, 0x40800000u});
    set_float4(255, {0x43FA0000u, 0x00000000u, 0x00000000u, 0x00000000u});
    set_float4(256, {0x3F800000u, 0x3F800000u, 0x3F800000u, 0x3F800000u});
    set_float4(511, {0x3F800000u, 0x00000000u, 0x00000000u, 0x00000000u});
    std::array<uint32_t, 8> captured_bool_constants{};
    captured_bool_constants[4] = 0x00000001u;
    shift::xbox::CapturedShaderConstants shader_constants{};
    require(shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size(),
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FF100u, &shader_constants, &error),
            "captured Xbox shader constant banks were rejected");
    require(shader_constants.vertex_float_constants[0] ==
                std::array<uint32_t, 4>{0x43B14000u, 0, 0, 0x44200000u} &&
                shader_constants.vertex_float_constants[1] ==
                std::array<uint32_t, 4>{0, 0x42B00000u, 0, 0x43B3C000u} &&
                shader_constants.vertex_float_constants[2][2] == 0x3F800000u &&
                shader_constants.vertex_float_constants[3][3] == 0x3F800000u &&
                shader_constants.vertex_float_constants[64][0] == 0x3F47FFFFu &&
                shader_constants.vertex_float_constants[69][3] == 0x3EB00000u &&
                shader_constants.vertex_float_constants[254][2] == 0xBF800000u &&
                shader_constants.vertex_float_constants[255][0] == 0x43FA0000u,
            "captured Xbox vertex shader constants changed");
    require(shader_constants.pixel_float_constants[0] ==
                std::array<uint32_t, 4>{0x3F800000u, 0x3F800000u,
                                        0x3F800000u, 0x3F800000u} &&
                shader_constants.pixel_float_constants[255] ==
                std::array<uint32_t, 4>{0x3F800000u, 0, 0, 0} &&
                shader_constants.pixel_b128 && !shader_constants.pixel_b129 &&
                shader_constants.pixel_boolean_constants_valid,
            "captured Xbox pixel constants or conditional path changed");
    shift::xbox::CapturedXboxShaderRegisterState shader_register_state;
    shift::xbox::CapturedShaderConstants tracked_shader_constants{};
    std::array<uint32_t, 2> tracked_vertex_descriptor{};
    std::array<uint32_t, 6> tracked_texture_descriptor{};
    require(!shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                error == "missing vertex shader control register 0x2307",
            "incomplete captured shader register state was accepted");
    shader_register_state.apply({0x2307u, 0x000FF000u});
    shader_register_state.apply({0x2308u, 0x000FF100u});
    const std::array<uint32_t, 10> required_shader_constants{
        64u, 65u, 66u, 67u, 68u, 69u, 254u, 255u, 256u, 511u,
    };
    for (uint32_t c : required_shader_constants) {
        for (uint32_t component = 0; component < 4; ++component) {
            shader_register_state.apply({
                0x4000u + c * 4u + component,
                captured_float_constants[c * 4u + component],
            });
        }
    }
    for (uint32_t i = 0; i < 6; ++i) {
        shader_register_state.apply({0x4800u + i, captured_texture_descriptor[i]});
    }
    for (uint32_t i = 0; i < 2; ++i) {
        shader_register_state.apply({0x4800u + 190u + i, captured_vertex_descriptor[i]});
    }
    require(shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                !tracked_shader_constants.pixel_boolean_constants_valid &&
                !tracked_shader_constants.pixel_b128 &&
                !tracked_shader_constants.pixel_b129,
            "unloaded pixel boolean constants were not marked as unknown");
    shader_register_state.apply({0x4904u, captured_bool_constants[4]});
    require(shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                tracked_shader_constants.vertex_float_constants[64][0] == 0x3F47FFFFu &&
                tracked_shader_constants.pixel_float_constants[255][0] == 0x3F800000u &&
                tracked_shader_constants.pixel_b128 &&
                tracked_vertex_descriptor ==
                    std::array<uint32_t, 2>{0x0975DFD3u, 0x10000032u} &&
                tracked_texture_descriptor ==
                    std::array<uint32_t, 6>{0x8800D8FEu, 0x09D57086u, 0x001FE3FFu,
                                            0x01280C14u, 0x00000003u, 0x00000A10u},
            "captured shader register bank snapshot diverged from its draw inputs");
    shader_register_state.apply(loaded_loop_constants.front());
    const auto loop_constant_bank =
        shader_register_state.snapshot_loop_constants();
    require(loop_constant_bank.valid[7] &&
                loop_constant_bank.words[7] == 0x00FE0503u &&
                !loop_constant_bank.valid[6],
            "captured loop-constant register bank was not tracked by index");
    shader_register_state.reset();
    require(!shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error),
            "shader register reset retained captured draw state");
    const auto reset_loop_constant_bank =
        shader_register_state.snapshot_loop_constants();
    require(std::none_of(reset_loop_constant_bank.valid.begin(),
                         reset_loop_constant_bank.valid.end(),
                         [](bool valid) { return valid; }),
            "shader register reset retained loop constants");
    shift::xbox::CapturedXboxShaderRegisterState dynamic_fetch_state;
    dynamic_fetch_state.apply({0x4800u, captured_vertex_descriptor[0]});
    dynamic_fetch_state.apply({0x4801u, captured_vertex_descriptor[1]});
    std::array<uint32_t, 2> descriptor_zero{};
    require(dynamic_fetch_state.snapshot_vertex_fetch_descriptor(
                0, &descriptor_zero, &error) &&
                descriptor_zero == std::array<uint32_t, 2>{
                    captured_vertex_descriptor[0], captured_vertex_descriptor[1]},
            "shader fetch descriptor zero was not dynamically addressable");
    require(!dynamic_fetch_state.snapshot_vertex_fetch_descriptor(
                96, &descriptor_zero, &error),
            "out-of-range vertex fetch descriptor index was accepted");
    shift::xbox::CapturedXboxShaderRegisterState sparse_constants;
    sparse_constants.apply({0x2307u, 0x000FF000u});
    sparse_constants.apply({0x2308u, 0x000FF100u});
    shift::xbox::CapturedShaderConstants sparse_snapshot{};
    require(sparse_constants.snapshot_constants(&sparse_snapshot, &error) &&
                !sparse_constants.validate_float_constants(
                    shift::xbox::GuestShaderStage::Vertex,
                    std::vector<uint32_t>{0}, false, &error) &&
                error == "captured vertex float constant 0 is incomplete",
            "shader constant snapshot still requires unused fixed registers");
    for (uint32_t component = 0; component < 4; ++component) {
        sparse_constants.apply({0x4000u + component, 0x3F800000u});
    }
    require(sparse_constants.validate_float_constants(
                shift::xbox::GuestShaderStage::Vertex,
                std::vector<uint32_t>{0}, false, &error),
            "captured shader read-set constant validation rejected a loaded register");
    require(!shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size() - 1,
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FF100u, &shader_constants, &error),
            "truncated captured shader constant bank was accepted");
    require(!shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size(),
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FE100u, &shader_constants, &error),
            "shader constant range too short for the captured pair was accepted");

    shift::xbox::CapturedTextureFetch white_border_texture = texture_fetch;
    white_border_texture.border_color = 1;
    require(shift::xbox::decode_captured_texture_sampling(
                white_border_texture, &texture_sampling, &error) &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrWhite &&
                texture_sampling.border_alpha_known,
            "known opaque-white border color lost its alpha contract");
    shift::xbox::CapturedTextureFetch reserved_swizzle = texture_fetch;
    reserved_swizzle.swizzle = (reserved_swizzle.swizzle & ~0x7u) | 6u;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_swizzle, &texture_sampling, &error),
            "reserved texture swizzle selector was accepted");
    shift::xbox::CapturedTextureFetch reserved_anisotropy = texture_fetch;
    reserved_anisotropy.aniso_filter = 6;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_anisotropy, &texture_sampling, &error),
            "reserved texture anisotropy value was accepted");

    std::vector<uint8_t> tiled_texture(texture_fetch.byte_length);
    const size_t texture_pixels = texture_fetch.byte_length / 4;
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        tiled_texture[pixel * 4] = static_cast<uint8_t>(pixel);
        tiled_texture[pixel * 4 + 1] = static_cast<uint8_t>(pixel >> 8);
        tiled_texture[pixel * 4 + 2] = static_cast<uint8_t>(pixel >> 16);
        tiled_texture[pixel * 4 + 3] = static_cast<uint8_t>(pixel >> 24);
    }
    std::vector<uint8_t> linear_texture;
    require(shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "captured tiled texture bytes were rejected");
    require(linear_texture.size() == texture_fetch.byte_length,
            "untiled texture byte length changed");

    std::vector<bool> seen_texture_pixels(texture_pixels, false);
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        const uint32_t source_pixel = read_be32(linear_texture.data() + pixel * 4);
        require(source_pixel < texture_pixels && !seen_texture_pixels[source_pixel],
                "untile mapping duplicated or exceeded a source texel");
        seen_texture_pixels[source_pixel] = true;
    }
    for (bool seen : seen_texture_pixels) {
        require(seen, "untile mapping skipped a source texel");
    }
    const auto require_texture_source_pixel = [&](uint32_t x, uint32_t y,
                                                  uint32_t expected) {
        const size_t pixel = static_cast<size_t>(y) * texture_fetch.width + x;
        require(read_be32(linear_texture.data() + pixel * 4) == expected,
                "captured Xenos tiled address or 8-in-32 byte order changed");
    };
    require_texture_source_pixel(0, 0, 0);
    require_texture_source_pixel(4, 0, 8);
    require_texture_source_pixel(0, 2, 64);
    require_texture_source_pixel(0, 16, 512);
    require_texture_source_pixel(32, 0, 1024);
    require_texture_source_pixel(0, 32, 32768);
    require_texture_source_pixel(1023, 255, 262111);

    auto dxt2_3_test_fetch = dxt2_3_fetch;
    dxt2_3_test_fetch.width = 128;
    dxt2_3_test_fetch.height = 128;
    dxt2_3_test_fetch.pitch = 128;
    dxt2_3_test_fetch.byte_length = 128u * 128u;
    const auto dxt2_3_tiled_offset = [](uint32_t x, uint32_t y,
                                        uint32_t pitch_blocks) {
        const uint64_t macro =
            ((static_cast<uint64_t>(x >> 5) +
              static_cast<uint64_t>(y >> 5) * (pitch_blocks >> 5)) << 11);
        const uint64_t micro =
            (static_cast<uint64_t>((x & 7u) + ((y & 0xEu) << 2)) << 4);
        const uint64_t offset = macro + ((micro & ~uint64_t{0xFu}) << 1) +
                                (micro & 0xFu) +
                                (static_cast<uint64_t>(y & 1u) << 4);
        return static_cast<size_t>(
            ((offset & ~uint64_t{0x1FFu}) << 3) +
            (static_cast<uint64_t>(y & 0x10u) << 7) +
            ((offset & 0x1C0u) << 2) +
            (((((y & 8u) >> 2) + (x >> 3)) & 3u) << 6) +
            (offset & 0x3Fu));
    };
    std::vector<uint8_t> tiled_dxt2_3(dxt2_3_test_fetch.byte_length);
    for (uint32_t block_y = 0; block_y < 32; ++block_y) {
        for (uint32_t block_x = 0; block_x < 32; ++block_x) {
            std::array<uint8_t, 16> normalized_block{};
            std::fill_n(normalized_block.begin(), 8, 0xFFu);
            const uint16_t packed_color = static_cast<uint16_t>(
                ((block_x & 0x1Fu) << 11) | ((block_y & 0x3Fu) << 5) |
                ((block_x + block_y) & 0x1Fu));
            normalized_block[8] = static_cast<uint8_t>(packed_color);
            normalized_block[9] = static_cast<uint8_t>(packed_color >> 8);
            normalized_block[10] = normalized_block[8];
            normalized_block[11] = normalized_block[9];
            const size_t destination = dxt2_3_tiled_offset(
                block_x, block_y, dxt2_3_test_fetch.pitch / 4u);
            for (size_t byte = 0; byte < normalized_block.size(); ++byte) {
                tiled_dxt2_3[destination + byte] = normalized_block[byte ^ 1u];
            }
        }
    }
    std::vector<uint8_t> decoded_dxt2_3;
    require(shift::xbox::untile_captured_texture_2d(
                dxt2_3_test_fetch, tiled_dxt2_3.data(), tiled_dxt2_3.size(),
                &decoded_dxt2_3, &error) &&
                decoded_dxt2_3.size() == 128u * 128u * 4u,
            "captured tiled DXT2/3 texture did not decode to Vulkan RGBA8");
    const auto require_dxt2_3_pixel = [&](uint32_t x, uint32_t y,
                                          uint32_t block_x, uint32_t block_y) {
        const uint16_t packed_color = static_cast<uint16_t>(
            ((block_x & 0x1Fu) << 11) | ((block_y & 0x3Fu) << 5) |
            ((block_x + block_y) & 0x1Fu));
        const size_t pixel = (static_cast<size_t>(y) * 128u + x) * 4u;
        require(decoded_dxt2_3[pixel] == ((packed_color >> 11 & 0x1Fu) * 255u / 31u) &&
                    decoded_dxt2_3[pixel + 1u] ==
                        ((packed_color >> 5 & 0x3Fu) * 255u / 63u) &&
                    decoded_dxt2_3[pixel + 2u] == ((packed_color & 0x1Fu) * 255u / 31u) &&
                    decoded_dxt2_3[pixel + 3u] == 255u,
                "captured DXT2/3 block tiling, byte order, or decode changed");
    };
    require_dxt2_3_pixel(1, 1, 0, 0);
    require_dxt2_3_pixel(32, 1, 8, 0);
    require_dxt2_3_pixel(1, 64, 0, 16);
    require_dxt2_3_pixel(127, 127, 31, 31);

    struct LiveDxt4_5Capture {
        uint32_t draw;
        uint32_t descriptor[6];
        uint32_t guest_address;
        uint32_t width;
        uint32_t height;
        uint32_t pitch;
        uint32_t storage_bytes;
    };
    const LiveDxt4_5Capture live_dxt4_5_captures[] = {
        {32, {0x820048FEu, 0x0A199054u, 0x0003E0FFu, 0x06A80D10u,
              0x00000C03u, 0x00000A10u}, 0x0A199000u, 256, 32, 256, 32768},
        {45, {0x810048FEu, 0x0A1E9054u, 0x0003E03Fu, 0x06A80D10u,
              0x00000C03u, 0x00000A10u}, 0x0A1E9000u, 64, 32, 128, 16384},
    };
    shift::xbox::CapturedTextureFetch live_dxt4_5_fetch{};
    for (const auto& capture : live_dxt4_5_captures) {
        const bool decoded = shift::xbox::decode_captured_texture_fetch(
            capture.descriptor, &live_dxt4_5_fetch, &error);
        if (!decoded) {
            std::cerr << "captured retail DXT4/5 draw #" << capture.draw
                      << " decode failed: " << error << '\n';
        }
        const bool matches = decoded &&
            live_dxt4_5_fetch.guest_address == capture.guest_address &&
            live_dxt4_5_fetch.format == 20 && live_dxt4_5_fetch.endian_mode == 1 &&
            live_dxt4_5_fetch.tiled && live_dxt4_5_fetch.width == capture.width &&
            live_dxt4_5_fetch.height == capture.height &&
            live_dxt4_5_fetch.pitch == capture.pitch &&
            live_dxt4_5_fetch.mip_filter == 1 &&
            live_dxt4_5_fetch.byte_length == capture.storage_bytes;
        if (!matches && decoded) {
            std::cerr << "captured retail DXT4/5 draw #" << capture.draw
                      << " decoded as addr=" << std::hex << live_dxt4_5_fetch.guest_address
                      << " format=" << std::dec << live_dxt4_5_fetch.format
                      << " size=" << live_dxt4_5_fetch.width << 'x'
                      << live_dxt4_5_fetch.height << " pitch=" << live_dxt4_5_fetch.pitch
                      << " mip=" << static_cast<uint32_t>(live_dxt4_5_fetch.mip_filter)
                      << " bytes=" << live_dxt4_5_fetch.byte_length << '\n';
        }
        require(matches,
                "captured retail DXT4/5 texture descriptor was rejected or misdecoded");
    }
    const uint32_t captured_dxt4_5_mip_chain_descriptor[] = {
        0x840248FEu, 0x0A24B054u, 0x0000E1FFu, 0x06A80D10u,
        0x00000E43u, 0x0A24BA10u,
    };
    require(shift::xbox::decode_captured_texture_fetch(
                captured_dxt4_5_mip_chain_descriptor, &live_dxt4_5_fetch, &error) &&
                live_dxt4_5_fetch.guest_address == 0x0A24B000u &&
                live_dxt4_5_fetch.format == 20 && live_dxt4_5_fetch.tiled &&
                live_dxt4_5_fetch.width == 512 && live_dxt4_5_fetch.height == 8 &&
                live_dxt4_5_fetch.pitch == 512 &&
                live_dxt4_5_fetch.mip_filter == 1 &&
                live_dxt4_5_fetch.byte_length == 65536u,
            "captured DXT4/5 base/mip alias was not kept as its one available base level");
    std::vector<uint8_t> aliased_dxt4_5(live_dxt4_5_fetch.byte_length, 0);
    std::vector<uint8_t> aliased_dxt4_5_rgba;
    require(shift::xbox::untile_captured_texture_2d(
                live_dxt4_5_fetch, aliased_dxt4_5.data(), aliased_dxt4_5.size(),
                &aliased_dxt4_5_rgba, &error) &&
                aliased_dxt4_5_rgba.size() == 512u * 8u * 4u,
            "captured DXT4/5 base/mip alias could not decode its base image");

    uint32_t unaliased_mip_descriptor[6];
    std::copy(std::begin(captured_dxt4_5_mip_chain_descriptor),
              std::end(captured_dxt4_5_mip_chain_descriptor),
              std::begin(unaliased_mip_descriptor));
    unaliased_mip_descriptor[5] = 0x0A24CA10u;
    require(!shift::xbox::decode_captured_texture_fetch(
                unaliased_mip_descriptor, &live_dxt4_5_fetch, &error),
            "captured DXT4/5 with distinct mip storage was accepted without mip data");

    require(shift::xbox::decode_captured_texture_fetch(
                live_dxt4_5_captures[0].descriptor, &live_dxt4_5_fetch, &error),
            "captured retail DXT4/5 texture could not be selected for untile regression");
    std::vector<uint8_t> tiled_dxt4_5(live_dxt4_5_fetch.byte_length, 0);
    for (uint32_t block_y = 0; block_y < live_dxt4_5_fetch.height / 4u; ++block_y) {
        for (uint32_t block_x = 0; block_x < live_dxt4_5_fetch.width / 4u; ++block_x) {
            std::array<uint8_t, 16> normalized_block{};
            normalized_block[0] = block_x == 0 ? 10u : block_x == 1 ? 200u : 255u;
            normalized_block[1] = block_x == 0 ? 20u : block_x == 1 ? 100u : 255u;
            if (block_x == 0) normalized_block[2] = 0x3Eu;  // alpha indices 6, 7
            if (block_x == 1) normalized_block[2] = 0x1Au;  // alpha indices 2, 3
            normalized_block[9] = 0xF8u;  // RGB565 red endpoints
            normalized_block[11] = 0xF8u;
            const size_t destination = dxt2_3_tiled_offset(
                block_x, block_y, live_dxt4_5_fetch.pitch / 4u);
            require(destination + normalized_block.size() <= tiled_dxt4_5.size(),
                    "captured DXT4/5 tiled address exceeded its padded allocation");
            for (size_t byte = 0; byte < normalized_block.size(); ++byte) {
                tiled_dxt4_5[destination + byte] = normalized_block[byte ^ 1u];
            }
        }
    }
    std::vector<uint8_t> decoded_dxt4_5;
    require(shift::xbox::untile_captured_texture_2d(
                live_dxt4_5_fetch, tiled_dxt4_5.data(), tiled_dxt4_5.size(),
                &decoded_dxt4_5, &error) &&
                decoded_dxt4_5.size() ==
                    static_cast<size_t>(live_dxt4_5_fetch.width) *
                    live_dxt4_5_fetch.height * 4u,
            "captured tiled DXT4/5 texture did not decode to Vulkan RGBA8");
    const auto require_dxt4_5_pixel = [&](uint32_t x, uint8_t alpha) {
        const size_t pixel = (static_cast<size_t>(x) * 4u);
        require(decoded_dxt4_5[pixel] == 255u && decoded_dxt4_5[pixel + 1u] == 0u &&
                    decoded_dxt4_5[pixel + 2u] == 0u &&
                    decoded_dxt4_5[pixel + 3u] == alpha,
                "captured DXT4/5 alpha interpolation or color decode changed");
    };
    require_dxt4_5_pixel(0, 0);
    require_dxt4_5_pixel(1, 255);
    require_dxt4_5_pixel(4, 185);
    require_dxt4_5_pixel(5, 171);

    const uint32_t captured_dxt5a_descriptor[] = {
        0x840048FEu, 0x0A1ED07Bu, 0x0003E1FFu, 0x06A80EDAu,
        0x00000C03u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch dxt5a_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_dxt5a_descriptor, &dxt5a_fetch, &error) &&
                dxt5a_fetch.guest_address == 0x0A1ED000u &&
                dxt5a_fetch.format == 59 && dxt5a_fetch.endian_mode == 1 &&
                dxt5a_fetch.tiled && dxt5a_fetch.width == 512 &&
                dxt5a_fetch.height == 32 && dxt5a_fetch.pitch == 512 &&
                dxt5a_fetch.byte_length == 32768 && dxt5a_fetch.swizzle == 0x76Du,
            "captured retail DXT5A texture descriptor was rejected or misdecoded");
    const auto dxt5a_tiled_offset = [](uint32_t x, uint32_t y,
                                       uint32_t pitch_blocks) {
        const uint64_t outer_blocks =
            ((static_cast<uint64_t>(x >> 5) +
              static_cast<uint64_t>(y >> 5) * (pitch_blocks >> 5)) << 6);
        const uint64_t inner_blocks = (((y >> 1) & 0x7u) << 3) | (x & 0x7u);
        const uint64_t outer_inner_bytes = (outer_blocks | inner_blocks) << 3;
        const uint32_t bank = (y >> 4) & 1u;
        const uint32_t pipe = ((x >> 3) & 3u) ^ (((y >> 3) & 1u) << 1);
        return static_cast<size_t>(
            (static_cast<uint64_t>(y & 1u) << 4) |
            (static_cast<uint64_t>(pipe) << 6) |
            (static_cast<uint64_t>(bank) << 11) |
            (outer_inner_bytes & 0xFu) |
            (((outer_inner_bytes >> 4) & 1u) << 5) |
            (((outer_inner_bytes >> 5) & 7u) << 8) |
            (outer_inner_bytes >> 8 << 12));
    };
    std::vector<uint8_t> tiled_dxt5a(dxt5a_fetch.byte_length, 0);
    std::vector<bool> seen_dxt5a_blocks(dxt5a_fetch.byte_length / 8u, false);
    for (uint32_t block_y = 0; block_y < dxt5a_fetch.height / 4u; ++block_y) {
        for (uint32_t block_x = 0; block_x < dxt5a_fetch.width / 4u; ++block_x) {
            std::array<uint8_t, 8> normalized_block{};
            normalized_block[0] = block_x == 0 ? 10u : block_x == 1 ? 200u : 255u;
            normalized_block[1] = block_x == 0 ? 20u : block_x == 1 ? 100u : 255u;
            if (block_x == 0) normalized_block[2] = 0x3Eu;
            if (block_x == 1) normalized_block[2] = 0x1Au;
            const size_t destination = dxt5a_tiled_offset(
                block_x, block_y, dxt5a_fetch.pitch / 4u);
            require(destination + normalized_block.size() <= tiled_dxt5a.size() &&
                        destination % 8u == 0 &&
                        !seen_dxt5a_blocks[destination / 8u],
                    "captured DXT5A tiled addresses overlapped or exceeded storage");
            seen_dxt5a_blocks[destination / 8u] = true;
            for (size_t byte = 0; byte < normalized_block.size(); ++byte) {
                tiled_dxt5a[destination + byte] = normalized_block[byte ^ 1u];
            }
        }
    }
    std::vector<uint8_t> decoded_dxt5a;
    require(shift::xbox::untile_captured_texture_2d(
                dxt5a_fetch, tiled_dxt5a.data(), tiled_dxt5a.size(),
                &decoded_dxt5a, &error) &&
                decoded_dxt5a.size() == 512u * 32u * 4u,
            "captured tiled DXT5A texture did not decode to Vulkan RGBA8");
    const auto require_dxt5a_pixel = [&](uint32_t x, uint8_t alpha) {
        const size_t pixel = static_cast<size_t>(x) * 4u;
        require(decoded_dxt5a[pixel] == 255u && decoded_dxt5a[pixel + 1u] == 255u &&
                    decoded_dxt5a[pixel + 2u] == 255u &&
                    decoded_dxt5a[pixel + 3u] == alpha,
                "captured DXT5A alpha values or W-channel mapping changed");
    };
    require_dxt5a_pixel(0, 0);
    require_dxt5a_pixel(1, 255);
    require_dxt5a_pixel(4, 185);
    require_dxt5a_pixel(5, 171);

    std::vector<uint8_t> linear_dxt2_3(tiled_dxt2_3.size());
    for (uint32_t block_y = 0; block_y < 32; ++block_y) {
        for (uint32_t block_x = 0; block_x < 32; ++block_x) {
            const size_t source = dxt2_3_tiled_offset(
                block_x, block_y, dxt2_3_test_fetch.pitch / 4u);
            const size_t destination =
                (static_cast<size_t>(block_y) * 32u + block_x) * 16u;
            std::copy_n(tiled_dxt2_3.data() + source, 16u,
                        linear_dxt2_3.data() + destination);
        }
    }
    dxt2_3_test_fetch.tiled = false;
    dxt2_3_test_fetch.packed_mips = false;
    require(shift::xbox::untile_captured_texture_2d(
                dxt2_3_test_fetch, linear_dxt2_3.data(), linear_dxt2_3.size(),
                &decoded_dxt2_3, &error) &&
                decoded_dxt2_3.size() == 128u * 128u * 4u,
            "captured linear DXT2/3 texture did not decode to Vulkan RGBA8");
    require_dxt2_3_pixel(1, 1, 0, 0);
    require_dxt2_3_pixel(32, 1, 8, 0);
    require_dxt2_3_pixel(1, 64, 0, 16);
    require_dxt2_3_pixel(127, 127, 31, 31);

    shift::xbox::CapturedTextureFetch unsupported_texture_layout = texture_fetch;
    unsupported_texture_layout.pitch -= 32;
    require(!shift::xbox::untile_captured_texture_2d(
                unsupported_texture_layout, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "uncaptured texture pitch was accepted");
    require(!shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size() - 1,
                &linear_texture, &error),
            "truncated captured texture was accepted");

    const uint8_t captured_indices[] = {
        0x00, 0x00, 0x00, 0x01, 0x00, 0x02,
        0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
    };
    const std::vector<uint8_t> expected_vk_indices{
        0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x03, 0x00,
    };
    std::vector<uint8_t> normalized;
    require(shift::xbox::normalize_captured_buffer_bytes(
                input.index_endian_mode, captured_indices, sizeof(captured_indices),
                &normalized, &error),
            "captured 8-in-16 index bytes were rejected");
    require(normalized == expected_vk_indices,
            "captured index bytes did not normalize to Vulkan UInt16 values");
    uint32_t maximum_vertex_index = 0;
    require(shift::xbox::decode_captured_index_data(
                input, captured_indices, sizeof(captured_indices), &normalized,
                &maximum_vertex_index, &error) &&
                normalized == expected_vk_indices && maximum_vertex_index == 3,
            "captured index data did not resolve the highest referenced vertex");
    uint32_t vertex_span_bytes = 0;
    require(shift::xbox::captured_vertex_required_bytes(
                maximum_vertex_index, 12, 0, 12, &vertex_span_bytes, &error) &&
                vertex_span_bytes == 48,
            "captured FLOAT3 vertex span did not cover four 12-byte vertices");
    require(!shift::xbox::captured_vertex_required_bytes(
                std::numeric_limits<uint32_t>::max(), 12, 0, 12,
                &vertex_span_bytes, &error),
            "overflowing captured vertex span was accepted");

    const uint8_t captured_vertex_words[] = {
        0xBF, 0x80, 0x00, 0x00, 0xBF, 0x80, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
    };
    const std::vector<uint8_t> expected_vk_vertex_words{
        0x00, 0x00, 0x80, 0xBF, 0x00, 0x00, 0x80, 0xBF,
        0x00, 0x00, 0x00, 0x00,
    };
    require(shift::xbox::normalize_captured_buffer_bytes(
                vertex_fetch.endian_mode, captured_vertex_words,
                sizeof(captured_vertex_words),
                &normalized, &error),
            "captured 8-in-32 vertex words were rejected");
    require(normalized == expected_vk_vertex_words,
            "captured vertex words did not normalize to Vulkan float32 values");

    require(!shift::xbox::normalize_captured_buffer_bytes(
                3, captured_indices, sizeof(captured_indices), &normalized, &error),
            "uncaptured endian mode was accepted");
    require(!shift::xbox::normalize_captured_buffer_bytes(
                1, captured_indices, sizeof(captured_indices) - 1, &normalized, &error),
            "truncated 8-in-16 resource was accepted");

    uint32_t unsupported_vertex_descriptor[] = {
        captured_vertex_descriptor[0], captured_vertex_descriptor[1]};
    unsupported_vertex_descriptor[0] =
        (unsupported_vertex_descriptor[0] & 0xFFFFFFFCu) | 2u;
    require(!shift::xbox::decode_captured_vertex_fetch(
                unsupported_vertex_descriptor, &vertex_fetch, &error),
            "texture-fetch descriptor was accepted as a vertex buffer");

    uint32_t unsupported_texture_descriptor[6];
    for (size_t i = 0; i < 6; ++i) {
        unsupported_texture_descriptor[i] = captured_texture_descriptor[i];
    }
    unsupported_texture_descriptor[1] =
        (unsupported_texture_descriptor[1] & ~0x3Fu) | 5u;
    require(!shift::xbox::decode_captured_texture_fetch(
                unsupported_texture_descriptor, &texture_fetch, &error),
            "uncaptured texture format was accepted");

    uint8_t unsupported[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported[i] = kCapturedPacket[i];
    }
    unsupported[2] = 0x23;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported, sizeof(unsupported), &input, &error),
            "unsupported packet opcode was accepted");

    uint8_t disagreeing_counts[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        disagreeing_counts[i] = kCapturedPacket[i];
    }
    disagreeing_counts[9] = 0x07;
    require(!shift::xbox::decode_captured_draw_indx(
                disagreeing_counts, sizeof(disagreeing_counts), &input, &error),
            "disagreeing packet index counts were accepted");

    uint8_t unsupported_index_size[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_index_size[i] = kCapturedPacket[i];
    }
    unsupported_index_size[10] |= 0x08;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_index_size, sizeof(unsupported_index_size), &input, &error),
            "unsupported 32-bit index format was accepted");

    uint8_t unsupported_source[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_source[i] = kCapturedPacket[i];
    }
    unsupported_source[11] |= 0x40;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_source, sizeof(unsupported_source), &input, &error),
            "unsupported immediate-index source was accepted");

    uint8_t unsupported_endian[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_endian[i] = kCapturedPacket[i];
    }
    unsupported_endian[16] = 0x80;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_endian, sizeof(unsupported_endian), &input, &error),
            "uncaptured index endian mode was accepted");

    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket) - 4, &input, &error),
            "truncated packet was accepted");

    const uint8_t captured_swap[] = {
        0xC0, 0x03, 0x64, 0x00,  // PM4_XE_SWAP, four payload dwords
        0x53, 0x57, 0x41, 0x50,  // "SWAP"
        0x09, 0x75, 0xD0, 0x00,  // 4 KiB-aligned physical frontbuffer
        0x00, 0x00, 0x05, 0x00,  // 1280
        0x00, 0x00, 0x02, 0xD0,  // 720
    };
    shift::xbox::DecodedGuestSwap swap{};
    require(shift::xbox::decode_guest_swap(
                captured_swap, sizeof(captured_swap), &swap, &error),
            "captured PM4_XE_SWAP packet was rejected");
    require(swap.frontbuffer_guest_address == 0x0975D000u &&
                swap.width == 1280u && swap.height == 720u,
            "PM4_XE_SWAP fields were decoded incorrectly");
    uint8_t bad_swap[sizeof(captured_swap)];
    std::copy(std::begin(captured_swap), std::end(captured_swap), std::begin(bad_swap));
    bad_swap[4] = 0;
    require(!shift::xbox::decode_guest_swap(
                bad_swap, sizeof(bad_swap), &swap, &error),
            "PM4_XE_SWAP with an invalid signature was accepted");
    require(!shift::xbox::decode_guest_swap(
                captured_swap, sizeof(captured_swap) - 4, &swap, &error),
            "truncated PM4_XE_SWAP packet was accepted");

    std::cout << "captured PM4_DRAW_INDX input check passed\n";
    return 0;
}
