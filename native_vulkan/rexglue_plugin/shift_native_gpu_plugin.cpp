#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_guest_ring.hpp"

#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

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

namespace {

using rex::X_STATUS;

constexpr uint32_t kGpuMmioBase = 0x7FC80000u;
constexpr uint32_t kGpuMmioMask = 0xFFFF0000u;
constexpr uint32_t kGpuMmioSize = 0x0000FFFFu;
constexpr uint32_t kRingWritePointerRegister = 0x01C5u;
constexpr uint32_t kRingReadPointerRegister = 0x01C4u;
constexpr uint32_t kPhysicalAddressMask = 0x1FFFFFFFu;

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
    std::vector<uint8_t> vertex_shader_program;
    std::vector<uint8_t> pixel_shader_program;
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
        vertex_shader_program.clear();
        pixel_shader_program.clear();
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
        uint32_t loaded_shader_programs = 0;
        uint32_t unresolved_shader_programs = 0;
        uint32_t unsupported_draws = 0;
        uint32_t raw_register_writes = 0;
        if (expanded_ok) {
          for (const shift::xbox::ResolvedGuestPacket& resolved : expanded.packets) {
            const shift::xbox::PacketSpan& packet = resolved.packet;
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

            if (packet.type == shift::xbox::PacketType::Type0 ||
                packet.type == shift::xbox::PacketType::Type1) {
              std::vector<shift::xbox::GuestRegisterWrite> writes;
              if (shift::xbox::decode_guest_register_writes(
                      packet_bytes, packet.byte_length, &writes, &error)) {
                raw_register_writes += static_cast<uint32_t>(writes.size());
                for (const shift::xbox::GuestRegisterWrite& write : writes) {
                  raster_register_state.apply(write);
                }
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
                       packet.opcode == 0x22u) {
              shift::xbox::DecodedIndexedDraw draw{};
              if (shift::xbox::decode_captured_draw_indx(
                      packet_bytes, packet.byte_length, &draw, &error)) {
                ++decoded_draws;
                shift::xbox::CapturedRasterRegisters raster_registers{};
                shift::xbox::CapturedRasterState raster_state{};
                if (raster_register_state.snapshot(&raster_registers, &error) &&
                    shift::xbox::decode_captured_raster_state(
                        raster_registers, &raster_state, &error)) {
                  ++draws_with_raster_state;
                }
                if (!vertex_shader_program.empty() && !pixel_shader_program.empty()) {
                  ++draws_with_both_shader_programs;
                }
              } else {
                ++unsupported_draws;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x36u) {
              ++unsupported_draws;
            }
          }
          REXLOG_DEBUG("shift-native: framed {} PM4 packets, {} raw register writes, "
                       "{} pointer-loaded shader programs ({} unresolved), "
                       "{} captured DRAW_INDX packets ({} with supported raster state, "
                       "{} with both shader programs), {} unsupported draw forms; "
                       "Vulkan draw submission is not wired",
                       expanded.packets.size(), raw_register_writes,
                       loaded_shader_programs, unresolved_shader_programs, decoded_draws,
                       draws_with_raster_state, draws_with_both_shader_programs,
                       unsupported_draws);
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
