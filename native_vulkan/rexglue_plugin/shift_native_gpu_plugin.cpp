#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_guest_ring.hpp"
#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <limits>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

#include <SPIRV/GlslangToSpv.h>
#include <StandAlone/ResourceLimits.h>
#include <glslang/Public/ShaderLang.h>
#include <rex/logging.h>
#include <rex/memory.h>
#include <rex/system/function_dispatcher.h>
#include <rex/system/gpu_plugin.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/system/mmio_handler.h>
#include <rex/system/xtypes.h>
#include <rex/ui/presenter.h>
#include <rex/ui/vulkan/presenter.h>
#include <rex/ui/vulkan/provider.h>
#include <rex/ui/windowed_app_context.h>

#include "shift_xbox_live_vulkan_renderer.hpp"

namespace {

using rex::X_STATUS;

constexpr uint32_t kGpuMmioBase = 0x7FC80000u;
constexpr uint32_t kGpuMmioMask = 0xFFFF0000u;
constexpr uint32_t kGpuMmioSize = 0x0000FFFFu;
constexpr uint32_t kRingWritePointerRegister = 0x01C5u;
constexpr uint32_t kRingReadPointerRegister = 0x01C4u;
constexpr uint32_t kPhysicalAddressMask = 0x1FFFFFFFu;

uint32_t ReadGuestDword(const uint8_t* bytes) {
  return (static_cast<uint32_t>(bytes[0]) << 24) |
         (static_cast<uint32_t>(bytes[1]) << 16) |
         (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

bool CompileCapturedShader(
    shift::xbox::CapturedShaderStage stage,
    const std::string& source,
    std::vector<uint32_t>* spirv,
    std::string* error) {
  if (!spirv || source.empty()) return false;
  static std::once_flag initialize_once;
  static std::mutex cache_mutex;
  static std::unordered_map<std::string, std::vector<uint32_t>> cache;
  const char* stage_name = stage == shift::xbox::CapturedShaderStage::Vertex ? "vertex" : "pixel";
  const std::string key = std::string(stage_name) + '\0' + source;
  std::lock_guard<std::mutex> lock(cache_mutex);
  if (const auto it = cache.find(key); it != cache.end()) {
    *spirv = it->second;
    return true;
  }
  std::call_once(initialize_once, [] { glslang::InitializeProcess(); });

  const EShLanguage language = stage == shift::xbox::CapturedShaderStage::Vertex
                                   ? EShLangVertex
                                   : EShLangFragment;
  const char* source_ptr = source.data();
  const int source_length = static_cast<int>(source.size());
  glslang::TShader shader(language);
  shader.setStringsWithLengths(&source_ptr, &source_length, 1);
  shader.setEnvInput(glslang::EShSourceGlsl, language, glslang::EShClientVulkan, 450);
  shader.setEnvClient(glslang::EShClientVulkan, glslang::EShTargetVulkan_1_1);
  shader.setEnvTarget(glslang::EShTargetSpv, glslang::EShTargetSpv_1_3);
  constexpr EShMessages messages = EShMessages(EShMsgSpvRules | EShMsgVulkanRules);
  if (!shader.parse(&glslang::DefaultTBuiltInResource, 450, false, messages)) {
    if (error) *error = std::string("glslang parse failed: ") + shader.getInfoLog();
    return false;
  }
  glslang::TProgram program;
  program.addShader(&shader);
  if (!program.link(messages)) {
    if (error) *error = std::string("glslang link failed: ") + program.getInfoLog();
    return false;
  }
  const glslang::TIntermediate* intermediate = program.getIntermediate(language);
  if (!intermediate) {
    if (error) *error = "glslang produced no captured shader intermediate";
    return false;
  }
  std::vector<uint32_t> compiled;
  glslang::SpvOptions options{};
  options.disableOptimizer = true;
  glslang::GlslangToSpv(*intermediate, compiled, &options);
  if (compiled.empty()) {
    if (error) *error = "glslang produced empty captured SPIR-V";
    return false;
  }
  cache.emplace(key, compiled);
  *spirv = std::move(compiled);
  if (error) error->clear();
  return true;
}

class ShiftNativeGraphicsSystem final : public rex::system::IGraphicsSystem {
 public:
  ~ShiftNativeGraphicsSystem() override { Shutdown(); }

  X_STATUS SetupPresentation(rex::ui::WindowedAppContext* app_context) override {
    if (presenter_) return X_STATUS_SUCCESS;
    if (!provider_) {
      // Native project renderer: do not enable ReXGlue's Xenos GPU features.
      provider_ = rex::ui::vulkan::VulkanProvider::Create(false, true);
    }
    if (!provider_) {
      REXLOG_ERROR("shift-native: unable to create the Vulkan presentation provider");
      return X_STATUS_UNSUCCESSFUL;
    }

    app_context_ = app_context;
    const auto create_presenter = [this]() {
      presenter_ = provider_->CreatePresenter(
          [](bool is_responsible, bool) {
            if (is_responsible) {
              REXLOG_ERROR("shift-native: Vulkan host device was lost");
            }
          });
    };
    if (app_context_) {
      if (!app_context_->CallInUIThreadSynchronous(create_presenter)) {
        return X_STATUS_UNSUCCESSFUL;
      }
    } else {
      create_presenter();
    }
    if (!presenter_) {
      REXLOG_ERROR("shift-native: unable to create the Vulkan presenter");
      return X_STATUS_UNSUCCESSFUL;
    }
    return X_STATUS_SUCCESS;
  }

  X_STATUS SetupGuestGpu(rex::runtime::FunctionDispatcher* function_dispatcher,
                         rex::system::KernelState*) override {
    if (!function_dispatcher) return X_STATUS_UNSUCCESSFUL;
    memory_ = function_dispatcher->memory();
    if (!memory_) return X_STATUS_UNSUCCESSFUL;
    if (!provider_) {
      // Headless Vulkan device for callers that deliberately skip presentation.
      provider_ = rex::ui::vulkan::VulkanProvider::Create(false, false);
    }
    if (!provider_) return X_STATUS_UNSUCCESSFUL;

    if (!memory_->AddVirtualMappedRange(kGpuMmioBase, kGpuMmioMask, kGpuMmioSize, this,
                                        ReadRegisterThunk, WriteRegisterThunk)) {
      REXLOG_ERROR("shift-native: unable to register the guest GPU MMIO range");
      return X_STATUS_UNSUCCESSFUL;
    }
    try {
      ring_worker_ = std::thread([this] { RingWorkerLoop(); });
    } catch (const std::exception& e) {
      REXLOG_ERROR("shift-native: unable to start PM4 input worker: {}", e.what());
      return X_STATUS_UNSUCCESSFUL;
    }
    REXLOG_INFO("shift-native: installed emulator-free Vulkan frontend; waiting for guest PM4");
    return X_STATUS_SUCCESS;
  }

  bool has_presentation() const override { return presenter_ != nullptr; }
  rex::ui::GraphicsProvider* provider() const override { return provider_.get(); }
  rex::ui::Presenter* presenter() const override { return presenter_.get(); }

  void SetInterruptCallback(uint32_t callback, uint32_t) override {
    if (callback) REXLOG_WARN("shift-native: guest GPU interrupts are not implemented");
  }

  void InitializeRingBuffer(uint32_t guest_address, uint32_t size_log2) override {
    size_t byte_length = 0;
    std::string error;
    if (!shift::xbox::guest_ring_byte_length_from_size_log2(size_log2, &byte_length, &error) ||
        !physical_span_valid(guest_address, byte_length)) {
      REXLOG_ERROR("shift-native: rejected guest ring setup ({})", error);
      return;
    }

    std::lock_guard<std::mutex> lock(ring_mutex_);
    ring_guest_address_ = guest_address;
    ring_byte_length_ = byte_length;
    ring_read_pointer_ = 0;
    ring_write_pointer_ = 0;
    ring_initialized_ = true;
    ++ring_generation_;
    REXLOG_INFO("shift-native: guest PM4 ring at {:08X}, {} bytes", guest_address,
                byte_length);
    ring_changed_.notify_one();
  }

  void EnableReadPointerWriteBack(uint32_t guest_address, uint32_t) override {
    std::lock_guard<std::mutex> lock(ring_mutex_);
    read_pointer_writeback_address_ = guest_address;
  }

  void Shutdown() override {
    {
      std::lock_guard<std::mutex> lock(ring_mutex_);
      ring_initialized_ = false;
      ring_worker_shutdown_ = true;
    }
    ring_changed_.notify_all();
    if (ring_worker_.joinable()) ring_worker_.join();
    if (presenter_ && app_context_) {
      app_context_->CallInUIThreadSynchronous([this]() { presenter_.reset(); });
    } else {
      presenter_.reset();
    }
    provider_.reset();
    app_context_ = nullptr;
    memory_ = nullptr;
  }

 private:
  static uint32_t ReadRegisterThunk(void*, void* context, uint32_t address) {
    return static_cast<ShiftNativeGraphicsSystem*>(context)->ReadRegister(address);
  }

  static void WriteRegisterThunk(void*, void* context, uint32_t address, uint32_t value) {
    try {
      static_cast<ShiftNativeGraphicsSystem*>(context)->NotifyWritePointer(address, value);
    } catch (const std::exception& e) {
      REXLOG_ERROR("shift-native: guest PM4 batch failed: {}", e.what());
    } catch (...) {
      REXLOG_ERROR("shift-native: guest PM4 batch failed with an unknown exception");
    }
  }

  bool physical_span_valid(uint32_t guest_address, size_t byte_length) const {
    const uint64_t physical_offset = guest_address & kPhysicalAddressMask;
    const uint64_t physical_limit = uint64_t{kPhysicalAddressMask} + 1u;
    return memory_ && byte_length != 0 &&
           physical_offset + static_cast<uint64_t>(byte_length) <= physical_limit;
  }

  static bool ReadGuestMemory(void* context, uint32_t guest_address, size_t byte_length,
                              const uint8_t** bytes, size_t* available_bytes) {
    auto* self = static_cast<ShiftNativeGraphicsSystem*>(context);
    if (!bytes || !available_bytes || !self->physical_span_valid(guest_address, byte_length)) {
      return false;
    }
    *bytes = self->memory_->TranslatePhysical<const uint8_t*>(guest_address);
    *available_bytes = byte_length;
    return *bytes != nullptr;
  }

  bool PrepareCapturedDrawResources(
      const shift::xbox::DecodedIndexedDraw& draw,
      const shift::xbox::CapturedRasterState& raster_state,
      const shift::xbox::CapturedXboxShaderRegisterState& shader_state,
      const std::vector<uint8_t>& vertex_program,
      const std::vector<uint8_t>& pixel_program,
      shift::xbox::CapturedVulkanDraw* prepared_draw,
      bool* inputs_ready,
      bool* shaders_translated,
      std::string* error) {
    if (!prepared_draw || !inputs_ready || !shaders_translated) return false;
    *inputs_ready = false;
    *shaders_translated = false;

    shift::xbox::CapturedShaderConstants constants{};
    std::array<uint32_t, 2> vertex_descriptor{};
    std::array<uint32_t, 6> texture_descriptor{};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    shift::xbox::CapturedTextureFetch texture_fetch{};
    shift::xbox::CapturedTextureSampling texture_sampling{};
    if (vertex_program.empty() || pixel_program.empty() ||
        !shader_state.snapshot(&constants, &vertex_descriptor, &texture_descriptor, error) ||
        !shift::xbox::decode_captured_vertex_fetch(
            vertex_descriptor.data(), &vertex_fetch, error) ||
        !shift::xbox::decode_captured_texture_fetch(
            texture_descriptor.data(), &texture_fetch, error) ||
        !shift::xbox::decode_captured_texture_sampling(
            texture_fetch, &texture_sampling, error)) {
      return false;
    }
    *inputs_ready = true;

    shift::xbox::CapturedShaderTranslationOptions options{};
    options.pixel_b128 = constants.pixel_b128;
    options.pixel_b129 = constants.pixel_b129;
    for (size_t i = 0; i < options.texture_swizzle.size(); ++i) {
      options.texture_swizzle[i] = static_cast<uint32_t>(texture_sampling.swizzle[i]);
    }
    shift::xbox::CapturedShaderTranslation vertex_translation{};
    shift::xbox::CapturedShaderTranslation pixel_translation{};
    if (!shift::xbox::translate_captured_shader_glsl(
            shift::xbox::CapturedShaderStage::Vertex, vertex_program.data(),
            vertex_program.size(), options, &vertex_translation, error)) {
      if (error) *error = "captured vertex shader: " + *error;
      return false;
    }
    if (!shift::xbox::translate_captured_shader_glsl(
            shift::xbox::CapturedShaderStage::Pixel, pixel_program.data(),
            pixel_program.size(), options, &pixel_translation, error)) {
      if (error) *error = "captured pixel shader: " + *error;
      return false;
    }
    *shaders_translated = true;

    shift::xbox::CapturedVulkanDraw prepared{};
    prepared.raster = raster_state;
    prepared.constants = constants;
    prepared.texture_sampling = texture_sampling;
    prepared.index_count = draw.index_count;
    prepared.texture_width = texture_fetch.width;
    prepared.texture_height = texture_fetch.height;
    if (!CompileCapturedShader(shift::xbox::CapturedShaderStage::Vertex,
                               vertex_translation.glsl, &prepared.vertex_shader_spirv, error) ||
        !CompileCapturedShader(shift::xbox::CapturedShaderStage::Pixel,
                               pixel_translation.glsl, &prepared.pixel_shader_spirv, error)) {
      return false;
    }

    std::vector<shift::xbox::CapturedShaderControlFlow> control_flow;
    std::vector<shift::xbox::CapturedShaderInstructionSchedule> schedule;
    if (!shift::xbox::decode_captured_shader_control_flow(
            vertex_program.data(), vertex_program.size(), &control_flow, error) ||
        !shift::xbox::schedule_captured_shader_instructions(
            control_flow, vertex_program.size(), &schedule, error)) {
      return false;
    }
    std::vector<shift::xbox::CapturedShaderControlFlow> pixel_control_flow;
    std::vector<shift::xbox::CapturedShaderInstructionSchedule> pixel_schedule;
    if (!shift::xbox::decode_captured_shader_control_flow(
            pixel_program.data(), pixel_program.size(), &pixel_control_flow, error) ||
        !shift::xbox::schedule_captured_shader_instructions(
            pixel_control_flow, pixel_program.size(), &pixel_schedule, error)) {
      return false;
    }

    uint32_t vertex_stride_bytes = 0;
    uint32_t vertex_offset_bytes = 0;
    bool has_vertex_fetch = false;
    for (const auto& instruction : schedule) {
      if (instruction.kind != shift::xbox::ShaderScheduledInstructionKind::Fetch ||
          std::find(vertex_translation.executed_instruction_addresses.begin(),
                    vertex_translation.executed_instruction_addresses.end(),
                    instruction.address) ==
              vertex_translation.executed_instruction_addresses.end()) {
        continue;
      }
      const size_t offset = static_cast<size_t>(instruction.address) * 12;
      shift::xbox::CapturedShaderFetchInstruction fetch{};
      if (offset + 12 > vertex_program.size() ||
          !shift::xbox::decode_captured_shader_fetch_instruction(
              vertex_program.data() + offset, 12, &fetch, error)) {
        return false;
      }
      if (fetch.kind != shift::xbox::CapturedShaderFetchKind::VertexFull) continue;

      const uint32_t stride = fetch.vertex_stride * 4;
      const uint32_t attribute_offset = fetch.vertex_offset < 0
                                            ? std::numeric_limits<uint32_t>::max()
                                            : static_cast<uint32_t>(fetch.vertex_offset);
      if (fetch.fetch_constant_index != 95 || fetch.vertex_format != 57 || stride != 12 ||
          attribute_offset != 0 || fetch.source_relative || fetch.destination_relative ||
          fetch.predicated ||
          (has_vertex_fetch &&
           (stride != vertex_stride_bytes || attribute_offset != vertex_offset_bytes))) {
        return false;
      }
      vertex_stride_bytes = stride;
      vertex_offset_bytes = attribute_offset;
      has_vertex_fetch = true;
    }
    for (const auto& instruction : pixel_schedule) {
      if (instruction.kind != shift::xbox::ShaderScheduledInstructionKind::Fetch ||
          std::find(pixel_translation.executed_instruction_addresses.begin(),
                    pixel_translation.executed_instruction_addresses.end(),
                    instruction.address) ==
              pixel_translation.executed_instruction_addresses.end()) {
        continue;
      }
      const size_t offset = static_cast<size_t>(instruction.address) * 12;
      shift::xbox::CapturedShaderFetchInstruction fetch{};
      if (offset + 12 > pixel_program.size() ||
          !shift::xbox::decode_captured_shader_fetch_instruction(
              pixel_program.data() + offset, 12, &fetch, error) ||
          fetch.kind != shift::xbox::CapturedShaderFetchKind::Texture2D ||
          fetch.fetch_constant_index != 0) {
        return false;
      }
    }

    constexpr uint32_t kMaxLiveIndexBytes = 2u * 1024u * 1024u;
    constexpr uint32_t kMaxLiveVertexBytes = 4u * 1024u * 1024u;
    constexpr uint32_t kMaxLiveTextureBytes = 16u * 1024u * 1024u;
    const uint8_t* guest_bytes = nullptr;
    size_t guest_byte_length = 0;
    uint32_t maximum_vertex_index = 0;
    uint32_t required_vertex_bytes = 0;
    if (!has_vertex_fetch || draw.index_byte_length > kMaxLiveIndexBytes ||
        texture_fetch.byte_length > kMaxLiveTextureBytes ||
        !ReadGuestMemory(this, draw.index_guest_address, draw.index_byte_length,
                         &guest_bytes, &guest_byte_length) ||
        guest_byte_length < draw.index_byte_length ||
        !shift::xbox::decode_captured_index_data(
            draw, guest_bytes, draw.index_byte_length, &prepared.indices,
            &maximum_vertex_index, error) ||
        !shift::xbox::captured_vertex_required_bytes(
            maximum_vertex_index, vertex_stride_bytes, vertex_offset_bytes, 12,
            &required_vertex_bytes, error) ||
        required_vertex_bytes > kMaxLiveVertexBytes ||
        required_vertex_bytes > vertex_fetch.byte_length ||
        !ReadGuestMemory(this, vertex_fetch.guest_address, required_vertex_bytes,
                         &guest_bytes, &guest_byte_length) ||
        guest_byte_length < required_vertex_bytes ||
        !shift::xbox::normalize_captured_buffer_bytes(
            vertex_fetch.endian_mode, guest_bytes, required_vertex_bytes,
            &prepared.vertices, error) ||
        !ReadGuestMemory(this, texture_fetch.guest_address, texture_fetch.byte_length,
                         &guest_bytes, &guest_byte_length) ||
        guest_byte_length < texture_fetch.byte_length ||
        !shift::xbox::untile_captured_texture_2d(
            texture_fetch, guest_bytes, texture_fetch.byte_length,
            &prepared.texture_rgba8, error)) {
      return false;
    }
    *prepared_draw = std::move(prepared);
    return true;
  }

  uint32_t ReadRegister(uint32_t address) {
    const uint32_t index = (address & 0xFFFFu) / sizeof(uint32_t);
    std::lock_guard<std::mutex> lock(ring_mutex_);
    if (index == kRingReadPointerRegister) return ring_read_pointer_;
    if (index == kRingWritePointerRegister) return ring_write_pointer_;
    return 0;
  }

  void NotifyWritePointer(uint32_t address, uint32_t value) {
    const uint32_t index = (address & 0xFFFFu) / sizeof(uint32_t);
    if (index != kRingWritePointerRegister) return;

    {
      std::lock_guard<std::mutex> lock(ring_mutex_);
      if (!ring_initialized_ || !memory_) return;
      const uint32_t ring_dwords = static_cast<uint32_t>(ring_byte_length_ / sizeof(uint32_t));
      if (value >= ring_dwords) {
        REXLOG_WARN("shift-native: ignored out-of-range CP_RB_WPTR {:08X}", value);
        return;
      }
      ring_write_pointer_ = value;
    }
    ring_changed_.notify_one();
  }

  void RingWorkerLoop() {
    shift::xbox::GuestRasterRegisterState raster_register_state;
    shift::xbox::CapturedXboxShaderRegisterState shader_register_state;
    std::vector<uint8_t> vertex_shader_program;
    std::vector<uint8_t> pixel_shader_program;
    std::vector<shift::xbox::CapturedVulkanDraw> frame_draws;
    uint64_t observed_ring_generation = 0;
    for (;;) {
      uint32_t read_pointer = 0;
      uint32_t write_pointer = 0;
      uint32_t ring_guest_address = 0;
      size_t ring_byte_length = 0;
      uint64_t ring_generation = 0;
      {
        std::unique_lock<std::mutex> lock(ring_mutex_);
        ring_changed_.wait(lock, [this] {
          return ring_worker_shutdown_ ||
                 (ring_initialized_ && ring_read_pointer_ != ring_write_pointer_);
        });
        if (ring_worker_shutdown_) return;
        read_pointer = ring_read_pointer_;
        write_pointer = ring_write_pointer_;
        ring_guest_address = ring_guest_address_;
        ring_byte_length = ring_byte_length_;
        ring_generation = ring_generation_;
      }
      if (ring_generation != observed_ring_generation) {
        raster_register_state.reset();
        shader_register_state.reset();
        vertex_shader_program.clear();
        pixel_shader_program.clear();
        frame_draws.clear();
        observed_ring_generation = ring_generation;
      }

      try {
        std::atomic_thread_fence(std::memory_order_acquire);
        const uint8_t* ring_bytes =
            memory_->TranslatePhysical<const uint8_t*>(ring_guest_address);
        shift::xbox::GuestRingBatch batch{};
        std::string error;
        const bool snapshotted = shift::xbox::snapshot_guest_ring_batch(
            ring_bytes, ring_byte_length, read_pointer, write_pointer, &batch, &error);
        shift::xbox::ExpandedGuestCommandStream expanded{};
        const bool expanded_ok = snapshotted && shift::xbox::expand_guest_indirect_buffers(
            batch, ReadGuestMemory, this, &expanded, &error);

        uint32_t decoded_draws = 0;
        uint32_t draws_with_raster_state = 0;
        uint32_t draws_with_both_shader_programs = 0;
        uint32_t draws_with_captured_shader_inputs = 0;
        uint32_t draws_with_project_shader_translation = 0;
        uint32_t draws_with_resolved_resource_payloads = 0;
        uint32_t draws_with_unresolved_resource_payloads = 0;
        uint32_t loaded_shader_programs = 0;
        uint32_t unresolved_shader_programs = 0;
        uint32_t loaded_immediate_shader_programs = 0;
        uint32_t unresolved_immediate_shader_programs = 0;
        uint32_t loaded_constant_spans = 0;
        uint32_t unresolved_constant_spans = 0;
        uint32_t unsupported_draws = 0;
        bool logged_draw_preparation_failure = false;
        uint32_t decoded_swaps = 0;
        uint32_t submitted_frames = 0;
        uint32_t raw_register_writes = 0;
        std::array<uint32_t, 256> type3_opcode_counts{};
        std::array<uint32_t, 256> draw_source_primitive_counts{};
        std::map<uint32_t, uint32_t> draw_index_count_counts;
        std::array<bool, 2> type3_packet_sample_logged{};
        bool logged_draw_decode_failure = false;
        if (expanded_ok) {
          for (const shift::xbox::ResolvedGuestPacket& resolved : expanded.packets) {
            const shift::xbox::PacketSpan& packet = resolved.packet;
            if (packet.type == shift::xbox::PacketType::Type3) {
              ++type3_opcode_counts[packet.opcode & 0xFFu];
            }
            const uint8_t* packet_bytes = nullptr;
            if (resolved.nesting_depth == 0) {
              packet_bytes = batch.bytes.data() + packet.byte_offset;
            } else {
              const uint8_t* source_bytes = nullptr;
              size_t source_available = 0;
              if (!ReadGuestMemory(this, resolved.source_guest_address,
                                   resolved.source_guest_buffer_byte_length,
                                   &source_bytes, &source_available) ||
                  source_available < resolved.source_guest_buffer_byte_length) {
                ++unsupported_draws;
                continue;
              }
              packet_bytes = source_bytes + packet.byte_offset;
            }

            if (packet.type == shift::xbox::PacketType::Type3 &&
                (packet.opcode == 0x2Bu || packet.opcode == 0x36u)) {
              if (packet.opcode == 0x36u && packet.byte_length >= 8u) {
                const uint32_t initiator = ReadGuestDword(packet_bytes + 4u);
                const uint32_t primitive_type = initiator & 0x3Fu;
                const uint32_t source_select = (initiator >> 6) & 0x3u;
                const uint32_t index_count = initiator >> 16;
                ++draw_source_primitive_counts[source_select * 64u +
                                               primitive_type];
                ++draw_index_count_counts[index_count];
              }
              const size_t sample_index = packet.opcode == 0x2Bu ? 0u : 1u;
              if (!type3_packet_sample_logged[sample_index]) {
                type3_packet_sample_logged[sample_index] = true;
                std::ostringstream sample;
                sample << std::hex << packet.opcode << std::dec << '/'
                       << packet.byte_length << ':';
                const size_t word_count = std::min(packet.byte_length / 4u, size_t{12});
                for (size_t word = 0; word < word_count; ++word) {
                  sample << (word ? "," : "") << std::hex
                         << ReadGuestDword(packet_bytes + word * 4u) << std::dec;
                }
                REXLOG_DEBUG("shift-native: raw type3 packet sample {}",
                             sample.str());
              }
            }

            if (packet.type == shift::xbox::PacketType::Type0 ||
                packet.type == shift::xbox::PacketType::Type1) {
              std::vector<shift::xbox::GuestRegisterWrite> writes;
              if (shift::xbox::decode_guest_register_writes(
                      packet_bytes, packet.byte_length, &writes, &error)) {
                raw_register_writes += static_cast<uint32_t>(writes.size());
                for (const shift::xbox::GuestRegisterWrite& write : writes) {
                  raster_register_state.apply(write);
                  shader_register_state.apply(write);
                }
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x2Fu) {
              shift::xbox::CapturedConstantLoad load{};
              const uint8_t* source_bytes = nullptr;
              size_t source_byte_length = 0;
              std::vector<shift::xbox::GuestRegisterWrite> writes;
              if (shift::xbox::decode_captured_constant_load(
                      packet_bytes, packet.byte_length, &load, &error) &&
                  ReadGuestMemory(this, load.guest_address, load.byte_length,
                                  &source_bytes, &source_byte_length) &&
                  source_byte_length >= load.byte_length &&
                  shift::xbox::decode_captured_constant_load_data(
                      load, source_bytes, load.byte_length, &writes, &error)) {
                for (const shift::xbox::GuestRegisterWrite& write : writes) {
                  raster_register_state.apply(write);
                  shader_register_state.apply(write);
                }
                ++loaded_constant_spans;
              } else {
                ++unresolved_constant_spans;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x2Bu) {
              shift::xbox::CapturedImmediateShaderProgramLoad shader_load{};
              if (shift::xbox::decode_captured_immediate_shader_program_load(
                      packet_bytes, packet.byte_length, &shader_load, &error) &&
                  shader_load.code_offset <= packet.byte_length &&
                  shader_load.byte_length <= packet.byte_length - shader_load.code_offset) {
                std::vector<uint8_t>& active_program =
                    shader_load.stage == shift::xbox::GuestShaderStage::Vertex
                        ? vertex_shader_program
                        : pixel_shader_program;
                active_program.assign(packet_bytes + shader_load.code_offset,
                                      packet_bytes + shader_load.code_offset +
                                          shader_load.byte_length);
                ++loaded_immediate_shader_programs;
              } else {
                ++unresolved_immediate_shader_programs;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x27u) {
              shift::xbox::CapturedShaderProgramLoad shader_load{};
              const uint8_t* shader_bytes = nullptr;
              size_t shader_byte_length = 0;
              if (shift::xbox::decode_captured_shader_program_load(
                      packet_bytes, packet.byte_length, &shader_load, &error) &&
                  ReadGuestMemory(this, shader_load.guest_address,
                                  shader_load.byte_length, &shader_bytes,
                                  &shader_byte_length) &&
                  shader_byte_length >= shader_load.byte_length) {
                std::vector<uint8_t>& active_program =
                    shader_load.stage == shift::xbox::GuestShaderStage::Vertex
                        ? vertex_shader_program
                        : pixel_shader_program;
                active_program.assign(shader_bytes,
                                      shader_bytes + shader_load.byte_length);
                ++loaded_shader_programs;
              } else {
                ++unresolved_shader_programs;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       (packet.opcode == 0x22u || packet.opcode == 0x36u)) {
              shift::xbox::DecodedIndexedDraw draw{};
              if (shift::xbox::decode_captured_draw_indx(
                      packet_bytes, packet.byte_length, &draw, &error)) {
                ++decoded_draws;
                shift::xbox::CapturedRasterRegisters raster_registers{};
                shift::xbox::CapturedRasterState raster_state{};
                const bool raster_state_ready =
                    raster_register_state.snapshot(&raster_registers, &error) &&
                    shift::xbox::decode_captured_raster_state(
                        raster_registers, &raster_state, &error);
                if (raster_state_ready) {
                  ++draws_with_raster_state;
                }
                if (!vertex_shader_program.empty() && !pixel_shader_program.empty()) {
                  ++draws_with_both_shader_programs;
                }
                bool shader_inputs_ready = false;
                bool shaders_translated = false;
                shift::xbox::CapturedVulkanDraw prepared_draw{};
                const bool resources_resolved =
                    raster_state_ready && raster_state.scissor_has_area &&
                    PrepareCapturedDrawResources(draw, raster_state, shader_register_state,
                                                 vertex_shader_program, pixel_shader_program,
                                                 &prepared_draw, &shader_inputs_ready,
                                                 &shaders_translated, &error);
                if (shader_inputs_ready) {
                  ++draws_with_captured_shader_inputs;
                }
                if (shaders_translated) {
                  ++draws_with_project_shader_translation;
                  if (resources_resolved) {
                    ++draws_with_resolved_resource_payloads;
                    frame_draws.push_back(std::move(prepared_draw));
                  } else {
                    ++draws_with_unresolved_resource_payloads;
                  }
                }
                if (!resources_resolved && !logged_draw_preparation_failure) {
                  REXLOG_DEBUG("shift-native: skipped captured indexed draw: {}",
                               error.empty() ? "unsupported shader or resource form" : error);
                  logged_draw_preparation_failure = true;
                }
              } else {
                ++unsupported_draws;
                if (!logged_draw_decode_failure) {
                  REXLOG_DEBUG("shift-native: rejected draw packet opcode {} "
                               "({} bytes): {}",
                               packet.opcode, packet.byte_length,
                               error.empty() ? "unsupported draw packet form"
                                             : error);
                  logged_draw_decode_failure = true;
                }
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x64u) {
              shift::xbox::DecodedGuestSwap swap{};
              if (!shift::xbox::decode_guest_swap(
                      packet_bytes, packet.byte_length, &swap, &error)) {
                ++unsupported_draws;
                frame_draws.clear();
                continue;
              }
              ++decoded_swaps;
              if (!frame_draws.empty() && presenter_ && provider_ &&
                  provider_->vulkan_device()) {
                const uint32_t draw_count = static_cast<uint32_t>(frame_draws.size());
                std::string render_error;
                const bool refreshed = presenter_->RefreshGuestOutput(
                    swap.width, swap.height, swap.width, swap.height,
                    [this, &frame_draws, &render_error, width = swap.width,
                     height = swap.height](
                        rex::ui::Presenter::GuestOutputRefreshContext& base) {
                      auto* context = dynamic_cast<
                          rex::ui::vulkan::VulkanPresenter::VulkanGuestOutputRefreshContext*>(
                          &base);
                      auto* device = provider_->vulkan_device();
                      if (!context || !device) return false;
                      const uint32_t family = device->queue_family_graphics_compute();
                      const auto queue = device->AcquireQueue(family, 0);
                      return shift::xbox::submit_captured_vulkan_frame(
                          device->physical_device(), device->device(), queue.queue(), family,
                          context->image(), context->image_view(),
                          context->image_ever_written_previously(),
                          width, height, frame_draws, &render_error);
                    });
                if (refreshed) {
                  ++submitted_frames;
                  REXLOG_INFO("shift-native: submitted {} captured indexed draw packets to "
                              "the Vulkan presenter at {}x{} (frontbuffer {:08X})",
                              draw_count, swap.width, swap.height,
                              swap.frontbuffer_guest_address);
                } else {
                  REXLOG_WARN("shift-native: Vulkan frame refresh failed for {}x{} "
                              "with {} captured draws: {}",
                              swap.width, swap.height, draw_count, render_error);
                }
              }
              frame_draws.clear();
            }
          }
          std::ostringstream type3_opcode_summary;
          bool first_type3_opcode = true;
          for (size_t opcode = 0; opcode < type3_opcode_counts.size(); ++opcode) {
            if (!type3_opcode_counts[opcode]) continue;
            if (!first_type3_opcode) type3_opcode_summary << ',';
            type3_opcode_summary << std::hex << opcode << std::dec << ':'
                                 << type3_opcode_counts[opcode];
            first_type3_opcode = false;
          }
          type3_opcode_summary << "; DRAW_INDX_2 source/primitive [";
          bool first_draw_form = true;
          for (uint32_t source = 0; source < 4u; ++source) {
            for (uint32_t primitive = 0; primitive < 64u; ++primitive) {
              const uint32_t count =
                  draw_source_primitive_counts[source * 64u + primitive];
              if (!count)
                continue;
              if (!first_draw_form)
                type3_opcode_summary << ',';
              type3_opcode_summary << "source=" << source
                                   << "/primitive=" << primitive << ':'
                                   << count;
              first_draw_form = false;
            }
          }
          type3_opcode_summary << ']';
          type3_opcode_summary << "; DRAW_INDX_2 index-count [";
          bool first_draw_count = true;
          for (const auto &[index_count, count] : draw_index_count_counts) {
            if (!first_draw_count)
              type3_opcode_summary << ',';
            type3_opcode_summary << index_count << ':' << count;
            first_draw_count = false;
          }
          type3_opcode_summary << ']';
          REXLOG_DEBUG("shift-native: framed {} PM4 packets, {} raw register writes, "
                       "{} constant spans loaded ({} unresolved), "
                       "{} pointer-loaded shader programs ({} unresolved), "
                       "{} inline shader programs ({} unresolved), "
                       "{} captured indexed draw packets ({} with supported raster state, "
                       "{} with both shader programs, {} with complete captured shader inputs, "
                       "{} translated to project GLSL, {} with resolved resource bytes "
                       "({} unresolved)), "
                       "{} guest swaps, {} Vulkan frames submitted, "
                       "{} unsupported packet/draw forms, type3 opcodes [{}]",
                       expanded.packets.size(), raw_register_writes,
                       loaded_constant_spans, unresolved_constant_spans,
                       loaded_shader_programs, unresolved_shader_programs,
                       loaded_immediate_shader_programs, unresolved_immediate_shader_programs,
                       decoded_draws,
                       draws_with_raster_state, draws_with_both_shader_programs,
                       draws_with_captured_shader_inputs, draws_with_project_shader_translation,
                       draws_with_resolved_resource_payloads,
                       draws_with_unresolved_resource_payloads, decoded_swaps, submitted_frames,
                       unsupported_draws, type3_opcode_summary.str());
        } else {
          REXLOG_WARN("shift-native: dropped malformed PM4 batch at WPTR {:08X}: {}",
                      write_pointer, error);
        }
      } catch (const std::exception& e) {
        REXLOG_ERROR("shift-native: failed to process guest PM4 batch: {}", e.what());
      } catch (...) {
        REXLOG_ERROR("shift-native: failed to process guest PM4 batch");
      }

      uint32_t writeback_address = 0;
      {
        std::lock_guard<std::mutex> lock(ring_mutex_);
        // Consume unsupported packets to keep the guest command producer moving.
        ring_read_pointer_ = write_pointer;
        writeback_address = read_pointer_writeback_address_;
      }
      if (writeback_address && physical_span_valid(writeback_address, sizeof(uint32_t))) {
        rex::memory::store_and_swap<uint32_t>(
            memory_->TranslatePhysical<uint32_t*>(writeback_address), write_pointer);
      }
    }
  }

  std::unique_ptr<rex::ui::vulkan::VulkanProvider> provider_;
  std::unique_ptr<rex::ui::Presenter> presenter_;
  rex::ui::WindowedAppContext* app_context_ = nullptr;
  rex::memory::Memory* memory_ = nullptr;
  std::mutex ring_mutex_;
  std::condition_variable ring_changed_;
  std::thread ring_worker_;
  uint32_t ring_guest_address_ = 0;
  size_t ring_byte_length_ = 0;
  uint32_t ring_read_pointer_ = 0;
  uint32_t ring_write_pointer_ = 0;
  uint32_t read_pointer_writeback_address_ = 0;
  uint64_t ring_generation_ = 0;
  bool ring_initialized_ = false;
  bool ring_worker_shutdown_ = false;
};

}  // namespace

extern "C" REX_GPU_PLUGIN_EXPORT uint32_t rex_gpu_abi_version() {
  return rex::system::kGpuPluginAbiVersion;
}

extern "C" REX_GPU_PLUGIN_EXPORT rex::system::IGraphicsSystem* rex_gpu_create(
    uint32_t abi_version, const rex::system::GpuCreateInfo* info) {
  if (abi_version != rex::system::kGpuPluginAbiVersion ||
      (info && info->struct_size < sizeof(rex::system::GpuCreateInfo))) {
    return nullptr;
  }
  if (info && info->backend && std::string(info->backend) != "any" &&
      std::string(info->backend) != "vulkan") {
    return nullptr;
  }
  return new ShiftNativeGraphicsSystem();
}
