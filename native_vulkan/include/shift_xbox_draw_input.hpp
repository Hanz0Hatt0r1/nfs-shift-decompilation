#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

enum class PrimitiveTopology : uint8_t {
    TriangleList,
};

struct DecodedIndexedDraw {
    PrimitiveTopology topology;
    uint32_t index_count;
    uint32_t index_guest_address;
    uint32_t index_type_bits;
    uint32_t index_endian_mode;
    uint32_t index_byte_length;
};

enum class PacketType : uint8_t {
    Type0,
    Type1,
    Type2,
    Type3,
    ZeroNop,
};

struct PacketSpan {
    PacketType type;
    size_t byte_offset;
    size_t byte_length;
    // Valid only for type-3 packets. Other packet spans use 0.
    uint32_t opcode;
};

struct GuestRegisterWrite {
    // PM4 register index (not a byte address) and decoded host-order value.
    uint32_t register_index;
    uint32_t value;
};

enum class GuestShaderStage : uint8_t {
    Vertex,
    Pixel,
};

struct CapturedShaderProgramLoad {
    GuestShaderStage stage;
    uint32_t guest_address;
    uint32_t dword_count;
    uint32_t byte_length;
};

struct CapturedIndirectBuffer {
    uint32_t guest_address;
    uint32_t dword_count;
};

enum class ShaderControlFlowOpcode : uint8_t {
    Nop = 0,
    Exec = 1,
    ExecEnd = 2,
    ConditionalJump = 11,
    Allocate = 12,
};

struct CapturedShaderControlFlow {
    uint32_t instruction_index;
    ShaderControlFlowOpcode opcode;
    uint32_t address;
    uint32_t instruction_count;
    uint32_t sequence;
    uint32_t bool_constant;
    bool condition;
    bool unconditional;
    bool predicated;
    bool jump_direction;
    uint32_t allocation_size;
    uint32_t allocation_type;
    bool allocation_unserialized;
};

enum class ShaderScheduledInstructionKind : uint8_t {
    Alu,
    Fetch,
};

struct CapturedShaderInstructionSchedule {
    uint32_t address;
    uint32_t control_flow_index;
    ShaderScheduledInstructionKind kind;
    bool serialized;
};

enum class CapturedShaderFetchKind : uint8_t {
    VertexFull,
    Texture2D,
};

struct CapturedShaderFetchInstruction {
    CapturedShaderFetchKind kind;
    uint32_t source_register;
    uint32_t destination_register;
    uint32_t source_swizzle;
    uint32_t destination_swizzle;
    uint32_t fetch_constant_index;
    uint32_t vertex_format;
    uint32_t vertex_stride;
    int32_t vertex_offset;
    uint32_t texture_dimension;
    bool source_relative;
    bool destination_relative;
    bool predicated;
    bool predicate_condition;
};

struct CapturedShaderAluInstruction {
    uint32_t vector_opcode;
    uint32_t scalar_opcode;
    uint32_t vector_destination;
    uint32_t scalar_destination;
    uint32_t vector_write_mask;
    uint32_t scalar_write_mask;
    uint32_t source_registers[3];
    uint32_t source_temporary_registers[3];
    uint32_t source_swizzles[3];
    bool source_is_temporary[3];
    bool source_temporary_relative[3];
    bool source_temporary_absolute[3];
    bool source_negate[3];
    uint32_t scalar_temporary_register;
    uint32_t scalar_temporary_component;
    uint32_t scalar_constant_component;
    bool export_data;
    bool vector_destination_relative;
    bool scalar_destination_relative;
    bool absolute_constants;
    bool vector_clamp;
    bool scalar_clamp;
    bool predicated;
    bool predicate_condition;
    bool const0_relative;
    bool const1_relative;
    bool const_address_register_relative;
};

// Xenos ALU swizzles store a component-relative offset for each lane.
constexpr uint32_t captured_alu_source_component(
    uint32_t swizzle,
    uint32_t component) {
    return ((swizzle >> (2 * component)) + component) & 3u;
}

struct CapturedVertexFetch {
    uint32_t guest_address;
    uint32_t endian_mode;
    uint32_t size_words;
    uint32_t byte_length;
};

struct CapturedTextureFetch {
    uint32_t guest_address;
    uint32_t format;
    uint32_t endian_mode;
    uint32_t sign_x;
    uint32_t sign_y;
    uint32_t sign_z;
    uint32_t sign_w;
    uint32_t clamp_x;
    uint32_t clamp_y;
    uint32_t clamp_z;
    uint32_t width;
    uint32_t height;
    uint32_t pitch;
    uint32_t byte_length;
    uint32_t dimension;
    uint32_t swizzle;
    uint32_t mag_filter;
    uint32_t min_filter;
    uint32_t mip_filter;
    uint32_t aniso_filter;
    bool integer_format;
    uint32_t border_color;
    bool border_size;
    bool tiled;
};

enum class TextureComponent : uint8_t {
    X,
    Y,
    Z,
    W,
    Zero,
    One,
};

enum class TextureSign : uint8_t {
    Unsigned,
    Signed,
    UnsignedBiased,
    Gamma,
};

enum class TextureClamp : uint8_t {
    Repeat,
    MirroredRepeat,
    ClampToEdge,
    MirrorClampToEdge,
    ClampToHalfway,
    MirrorClampToHalfway,
    ClampToBorder,
    MirrorClampToBorder,
};

enum class TextureFilter : uint8_t {
    Point,
    Linear,
    BaseMap,
    FetchConstant,
};

enum class TextureAnisotropy : uint8_t {
    Disabled,
    Max1To1,
    Max2To1,
    Max4To1,
    Max8To1,
    Max16To1,
    FetchConstant = 7,
};

enum class TextureBorderColor : uint8_t {
    AbgrBlack,
    AbgrWhite,
    AcbycrBlack,
    AcbcryBlack,
};

struct CapturedTextureSampling {
    std::array<TextureComponent, 4> swizzle;
    std::array<TextureSign, 4> signs;
    std::array<TextureClamp, 3> clamps;
    TextureFilter mag_filter;
    TextureFilter min_filter;
    TextureFilter mip_filter;
    TextureAnisotropy anisotropy;
    TextureBorderColor border_color;
    bool border_alpha_known;
};

enum class CapturedColorTargetFormat : uint8_t {
    Rgba8Gamma,
};

enum class CapturedDepthTargetFormat : uint8_t {
    D24S8,
};

struct CapturedRasterRegisters {
    uint32_t surface_info;
    uint32_t color_info;
    uint32_t depth_info;
    uint32_t mode_control;
    uint32_t depth_control;
    uint32_t color_mask;
    uint32_t viewport_x_scale;
    uint32_t viewport_x_offset;
    uint32_t viewport_y_scale;
    uint32_t viewport_y_offset;
    uint32_t screen_scissor_tl;
    uint32_t screen_scissor_br;
    uint32_t window_offset;
    uint32_t window_scissor_tl;
    uint32_t window_scissor_br;
};

// Retains only the raster registers used by the captured Xbox draw contract.
// Call apply() for each decoded PM4 register write and snapshot() at a draw.
struct GuestRasterRegisterState {
    void reset() noexcept;
    void apply(const GuestRegisterWrite& write) noexcept;
    bool snapshot(CapturedRasterRegisters* output, std::string* error) const;

private:
    CapturedRasterRegisters registers_{};
    uint16_t valid_mask_ = 0;
};

struct CapturedRasterState {
    uint32_t width;
    uint32_t height;
    uint32_t sample_count;
    uint32_t color_base_tiles;
    CapturedColorTargetFormat color_format;
    uint32_t depth_base_tiles;
    CapturedDepthTargetFormat depth_format;
    uint32_t color_write_mask;
    bool viewport_y_flipped;
    bool depth_test_enabled;
    bool depth_write_enabled;
    bool stencil_test_enabled;
    uint32_t scissor_x0;
    uint32_t scissor_y0;
    uint32_t scissor_x1;
    uint32_t scissor_y1;
    bool scissor_has_area;
};

struct CapturedShaderConstants {
    std::array<std::array<uint32_t, 4>, 256> vertex_float_constants;
    std::array<std::array<uint32_t, 4>, 256> pixel_float_constants;
    bool pixel_b128;
    bool pixel_b129;
};

// Scans big-endian packet framing only. It does not interpret register writes
// or execute packets.
bool scan_captured_packet_stream(
    const uint8_t* stream_bytes,
    size_t byte_length,
    std::vector<PacketSpan>* output,
    std::string* error);

// Decodes one PM4 type-0 or type-1 packet into raw host-order register writes.
// It does not update a GPU register file or apply state.
bool decode_guest_register_writes(
    const uint8_t* packet_bytes,
    size_t byte_length,
    std::vector<GuestRegisterWrite>* output,
    std::string* error);

// Decodes the captured pointer-based PM4_IM_LOAD form. It identifies the
// guest microcode span only; callers still provide and bound guest-memory IO.
bool decode_captured_shader_program_load(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedShaderProgramLoad* output,
    std::string* error);

// Decodes the captured three-dword PM4_INDIRECT_BUFFER form. It reports the
// guest span only; it does not read or execute the indirect command buffer.
bool decode_captured_indirect_buffer(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedIndirectBuffer* output,
    std::string* error);

// Decodes the bounded control-flow prefix of the captured Xbox shader format.
// It preserves instruction scheduling and branch inputs but does not execute
// shader instructions or translate them to SPIR-V.
bool decode_captured_shader_control_flow(
    const uint8_t* shader_bytes,
    size_t byte_length,
    std::vector<CapturedShaderControlFlow>* output,
    std::string* error);

// Decodes only the captured vfetch_full and tfetch2D 96-bit instruction forms.
// It reads instruction bytes but does not perform a fetch or translate them.
bool decode_captured_shader_fetch_instruction(
    const uint8_t* instruction_bytes,
    size_t byte_length,
    CapturedShaderFetchInstruction* output,
    std::string* error);

// Decodes the raw ALU fields from one 96-bit instruction. Opcode semantics and
// shader execution are intentionally outside this parser.
bool decode_captured_shader_alu_instruction(
    const uint8_t* instruction_bytes,
    size_t byte_length,
    CapturedShaderAluInstruction* output,
    std::string* error);

// Expands captured exec clauses into addressed ALU/fetch slots. Branches are
// retained in the CF input and are not evaluated here.
bool schedule_captured_shader_instructions(
    const std::vector<CapturedShaderControlFlow>& control_flow,
    size_t shader_byte_length,
    std::vector<CapturedShaderInstructionSchedule>* output,
    std::string* error);

// Translates only the captured PM4_DRAW_INDX form. This decodes the guest
// command into renderer inputs; it does not execute or emulate Xenos state.
bool decode_captured_draw_indx(
    const uint8_t* packet_bytes,
    size_t byte_length,
    DecodedIndexedDraw* output,
    std::string* error);

// Decodes the captured two-dword vertex-fetch descriptor. The dwords are
// numeric register values, after the ring frontend's explicit byte-order read.
bool decode_captured_vertex_fetch(
    const uint32_t descriptor_words[2],
    CapturedVertexFetch* output,
    std::string* error);

// Decodes only the captured format-6 tiled 2D texture descriptor.
bool decode_captured_texture_fetch(
    const uint32_t descriptor_words[6],
    CapturedTextureFetch* output,
    std::string* error);

// Gives the captured descriptor fields semantic names without choosing a
// Vulkan format or sampler policy. Unknown/reserved selector values fail.
bool decode_captured_texture_sampling(
    const CapturedTextureFetch& texture,
    CapturedTextureSampling* output,
    std::string* error);

// Decodes only the captured color/depth target, viewport, and scissor form.
// This maps observed registers to neutral render state; it does not emulate
// register writes or Xenos rasterization.
bool decode_captured_raster_state(
    const CapturedRasterRegisters& registers,
    CapturedRasterState* output,
    std::string* error);

// Resolves the stage-relative 256-register VS/PS float windows and the packed
// bool values used by the captured PS branch. The float bank is 512 float4
// registers; the bool bank is eight packed dwords.
bool decode_captured_shader_constants(
    const uint32_t* float_bank_words,
    size_t float_word_count,
    const uint32_t* bool_bank_words,
    size_t bool_word_count,
    uint32_t vertex_constant_control,
    uint32_t pixel_constant_control,
    CapturedShaderConstants* output,
    std::string* error);

// Untiles the captured 8_8_8_8, 8-in-32, tiled 2D texture into linear texel
// order while applying the captured per-dword byte swap. Other layouts fail.
bool untile_captured_texture_2d(
    const CapturedTextureFetch& texture,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error);

// Converts only the two guest byte orders observed on this captured draw:
// 8-in-16 indices and 8-in-32 vertex words. The output byte stream is suitable
// for the Vulkan index/vertex formats used by the captured resources.
bool normalize_captured_buffer_bytes(
    uint32_t endian_mode,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error);

}  // namespace shift::xbox
