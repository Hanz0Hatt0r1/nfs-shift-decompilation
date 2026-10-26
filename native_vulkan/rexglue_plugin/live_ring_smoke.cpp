#include <dlfcn.h>
#include <rex/logging/api.h>
#include <rex/system/function_dispatcher.h>
#include <rex/system/gpu_plugin.h>
#include <rex/system/mmio_handler.h>
#include <rex/system/xmemory.h>
#include <spdlog/sinks/ostream_sink.h>

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

constexpr uint32_t kRingAddress = 0x00010000u;
constexpr uint32_t kWritebackAddress = 0x00012000u;
constexpr uint32_t kRingSizeLog2 = 9u;
constexpr uint32_t kWritePointerRegister = 0x7FC80714u;
constexpr uint32_t kReadPointerRegister = 0x7FC80710u;
constexpr uint32_t kVblankStatusAddress = 0x7FC86544u;
constexpr uint32_t kCoherStatusHostAddress = 0x7FC828C4u;
constexpr uint32_t kCoherBaseHostAddress = 0x7FC828C0u;
constexpr uint32_t kCoherSizeHostAddress = 0x7FC828BCu;
constexpr uint32_t kIndexAddress = 0x0975D7B0u;
constexpr uint32_t kVertexAddress = 0x0975DFD0u;
constexpr uint32_t kPixelShaderAddress = 0x09D50460u;
constexpr uint32_t kVertexShaderAddress = 0x09D568E0u;
constexpr uint32_t kTextureAddress = 0x09D57000u;
constexpr uint32_t kQueueDescriptorPhysicalAddress = 0x17AF4000u;
constexpr uint32_t kQueueDescriptorVirtualAddress = 0xB7AF4000u;
constexpr uint32_t kWaitMarkerAddress = 0x00014000u;
constexpr uint32_t kWaitScratchAddress = 0x1B964000u;
constexpr uint32_t kIndirectBufferAddress = 0x00030000u;
constexpr uint32_t kFrontbufferAddress = 0x00020000u;
constexpr uint32_t kTargetWidth = 1280u;
constexpr uint32_t kTargetHeight = 720u;
constexpr uint32_t kPageBytes = 0x1000u;
constexpr uint32_t kTextureBytes = 1024u * 256u * 4u;

uint32_t read_be32(const uint8_t* bytes) {
  return (uint32_t{bytes[0]} << 24) | (uint32_t{bytes[1]} << 16) |
         (uint32_t{bytes[2]} << 8) | uint32_t{bytes[3]};
}

void write_be32(uint8_t* bytes, uint32_t value) {
  bytes[0] = static_cast<uint8_t>(value >> 24);
  bytes[1] = static_cast<uint8_t>(value >> 16);
  bytes[2] = static_cast<uint8_t>(value >> 8);
  bytes[3] = static_cast<uint8_t>(value);
}

void store_guest_be32_atomic(uint8_t* bytes, uint32_t value) {
  auto* word = reinterpret_cast<uint32_t*>(bytes);
  const uint32_t raw = std::endian::native == std::endian::little
                           ? std::byteswap(value)
                           : value;
  __atomic_store_n(word, raw, __ATOMIC_RELEASE);
}

void append_be32(std::vector<uint8_t>* bytes, uint32_t value) {
  const size_t offset = bytes->size();
  bytes->resize(offset + sizeof(value));
  write_be32(bytes->data() + offset, value);
}

void append_type0(std::vector<uint8_t>* stream, uint32_t base_register,
                  const std::vector<uint32_t>& values) {
  if (values.empty()) return;
  append_be32(stream, (static_cast<uint32_t>(values.size() - 1u) << 16) |
                          (base_register & 0x7FFFu));
  for (uint32_t value : values) append_be32(stream, value);
}

void append_type0(std::vector<uint8_t>* stream, uint32_t index,
                  uint32_t value) {
  append_type0(stream, index, std::vector<uint32_t>{value});
}

void append_type3(std::vector<uint8_t>* stream, uint32_t opcode,
                  const std::vector<uint32_t>& payload) {
  append_be32(stream, 0xC0000000u |
                          (static_cast<uint32_t>(payload.size() - 1u) << 16) |
                          (opcode << 8));
  for (uint32_t value : payload) append_be32(stream, value);
}

void write_shader_triplet(std::vector<uint8_t>* shader, size_t triplet,
                          uint32_t word0, uint32_t word1, uint32_t word2) {
  uint8_t* bytes = shader->data() + triplet * 12u;
  write_be32(bytes, word0);
  write_be32(bytes + 4u, word1);
  write_be32(bytes + 8u, word2);
}

// Small synthetic VS with the captured fetch descriptor 95 and output class.
// The PS below is an exact 108-byte retail instruction slice used by the
// translator regression; this pairing and its resource bytes are test-only.
std::vector<uint8_t> make_vertex_shader() {
  std::vector<uint8_t> shader(4u * 12u, 0);
  // CF: EXEC fetch@2; ALLOC position; EXEC_END ALU@3; NOP.
  write_shader_triplet(&shader, 0, 0x00011002u, 0x00011000u, 0xC2000000u);
  write_shader_triplet(&shader, 1, 0x00001003u, 0x00002000u, 0);
  // vfetch_full: descriptor 95, float3, stride 3 dwords, offset 0.
  write_shader_triplet(&shader, 2, 0x05F00000u, 0x00390E42u, 3u);
  // Export the fetched xyz and supply the position's homogeneous w as one.
  write_shader_triplet(&shader, 3, 0xC88F8000u, 0, 0xA1000000u);
  return shader;
}

std::vector<uint8_t> make_captured_pixel_shader_slice() {
  constexpr uint8_t bytes[] = {
      0x00, 0x00, 0x00, 0x05, 0x20, 0x04, 0xB2, 0x00, 0x12, 0x00, 0x00, 0x09,
      0x00, 0x00, 0x00, 0x04, 0x10, 0x06, 0xB2, 0x04, 0x12, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x20, 0x06, 0x10, 0x07, 0xB0, 0x00, 0x12, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x10, 0x08, 0xC4, 0x00, 0x22, 0x00, 0x00, 0x00,
      0x10, 0x08, 0x00, 0x01, 0x1F, 0x1F, 0xF6, 0x88, 0x00, 0x00, 0x40, 0x00,
      0xC8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0xC8, 0x0F, 0x00, 0x00, 0x00, 0x6C, 0x6C, 0x00, 0x22, 0xFF, 0xFF, 0x00,
      0xC8, 0x0F, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA1, 0x00, 0x00, 0x00,
  };
  return std::vector<uint8_t>(std::begin(bytes), std::end(bytes));
}

std::vector<uint8_t> make_pm4_stream() {
  std::vector<uint8_t> stream;
  // Raster registers exercise the captured 1280x720 linear RGBA8/D24S8 form.
  constexpr std::array<std::pair<uint32_t, uint32_t>, 17> raster_registers = {{
      {0x2000u, 0x14000500u},
      {0x2001u, 0x00000000u},
      {0x2002u, 0x000002D0u},
      {0x2208u, 0x00000004u},
      {0x2200u, 0x00700770u},
      {0x2104u, 0x0000000Fu},
      {0x210Fu, 0x44200000u},
      {0x2110u, 0x44200000u},
      {0x2111u, 0xC3B40000u},
      {0x2112u, 0x43B40000u},
      {0x200Eu, 0x00000000u},
      {0x200Fu, 0x20002000u},
      {0x2080u, 0x00000000u},
      {0x2081u, 0x00000000u},
      {0x2082u, 0x02D00500u},
      {0x2201u, 0x07010706u},
      {0x2205u, 0x00000000u},
  }};
  for (const auto& [index, value] : raster_registers)
    append_type0(&stream, index, value);

  // Captured shader controls and fetch descriptors. The synthetic VS swizzles
  // input z/x/y to position x/y/z, then multiplies by c0.
  append_type0(&stream, 0x2307u, 0x000FF000u);
  append_type0(&stream, 0x2308u, 0x000FF100u);
  append_type0(&stream, 0x4904u, 0x00000001u);
  append_type0(&stream, 0x4000u,
               {0x3F800000u, 0x3F800000u, 0x3F800000u, 0x3F800000u});
  append_type0(&stream, 0x4800u,
               {0x8800D8FEu, 0x09D57086u, 0x001FE3FFu, 0x01280C14u, 0x00000003u,
                0x00000A10u});
  append_type0(&stream, 0x48BEu, {0x0975DFD3u, 0x10000032u});
  for (const auto& range : std::array<std::pair<uint32_t, uint32_t>, 4>{
           {{0x4100u, 24u}, {0x43F8u, 8u}, {0x4400u, 4u}, {0x47FCu, 4u}}}) {
    append_type0(&stream, range.first, std::vector<uint32_t>(range.second, 0u));
  }

  // The captured pointer-loaded shader packet form (stage in low address bits).
  append_type3(&stream, 0x27u, {kVertexShaderAddress, 12u});
  append_type3(&stream, 0x27u, {kPixelShaderAddress | 1u, 27u});

  // Exact captured PM4_DRAW_INDX packet from ring offset 0x2C64.
  constexpr uint8_t captured_draw[] = {
      0xC0, 0x03, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06,
      0x00, 0x04, 0x09, 0x75, 0xD7, 0xB0, 0x40, 0x00, 0x00, 0x06,
  };
  stream.insert(stream.end(), std::begin(captured_draw),
                std::end(captured_draw));
  // A second draw uses the supported DMA packet form; its payload is fixture
  // data.
  append_type3(&stream, 0x36u, {0x00060004u, kIndexAddress, 0x40000006u});
  // The captured AutoIndex rectangle-list form consumes three fetched vertices.
  append_type3(&stream, 0x36u, {0x00030088u});
  // Exact retail COHER_STATUS_HOST register and WAIT_REG_MEM form from the
  // pre-wait capture. Each batch exercises the fence drain after the previous
  // batch has submitted its Vulkan frame.
  append_type0(&stream, 0x0A31u, 0x02000000u);
  append_type0(&stream, 0x0A2Fu, {0x00002000u, 0x1B962000u});
  append_type3(&stream, 0x3Cu,
               {0x03u, 0x0A31u, 0u, 0x80000000u, 8u});
  // These wait/interrupt/ack operands are from the captured retail stream
  // builder. The two EVENT_WRITE_SHD markers let the smoke test prove that
  // the consumer pauses at the captured waits until their memory conditions
  // are released by the test harness.
  append_type3(&stream, 0x58u,
               {0x00000003u, kWaitMarkerAddress | 2u, 1u});
  append_type3(&stream, 0x3Cu,
               {0x13u, 0x1B964002u, 0x00000004u, 0xFFFFFFFFu, 0x00000100u});
  append_type3(&stream, 0x3Cu,
               {0x13u, 0x1B964016u, 0x00000208u, 0xFFFFFFFFu, 0x00000100u});
  append_type3(&stream, 0x3Cu,
               {0x13u, 0x1B964012u, 0x823A4758u, 0xFFFFFFFFu, 0x00000100u});
  append_type3(&stream, 0x54u, {0x00000004u});
  append_type0(&stream, 0x045Eu, 4u);
  append_type3(&stream, 0x58u,
               {0x00000003u, kWaitMarkerAddress | 2u, 2u});
  // A retail-shaped EVENT_WRITE_SHD updates descriptor+0 through its physical
  // address; the consumer reads the same storage through the 0xB... alias.
  append_type3(&stream, 0x58u,
               {0x00000003u, kQueueDescriptorPhysicalAddress | 2u,
                0x00000003u});
  append_type3(&stream, 0x64u,
               {0x53574150u, kFrontbufferAddress, kTargetWidth, kTargetHeight});
  return stream;
}

std::vector<uint8_t> make_ring_stream(const std::vector<uint8_t>& indirect) {
  std::vector<uint8_t> ring_stream;
  append_type3(&ring_stream, 0x3Fu,
               {kIndirectBufferAddress,
                static_cast<uint32_t>(indirect.size() / sizeof(uint32_t))});
  return ring_stream;
}

bool reserve_guest_range(rex::memory::VirtualHeap* heap, uint32_t address,
                         size_t byte_length) {
  return heap && heap->AllocFixed(address, byte_length, kPageBytes,
                                  rex::memory::kMemoryAllocationReserve |
                                      rex::memory::kMemoryAllocationCommit,
                                  rex::memory::kMemoryProtectRead |
                                      rex::memory::kMemoryProtectWrite);
}

int fail(const char* message) {
  std::cerr << message << '\n';
  return 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) return 2;

  rex::InitLogging(nullptr, spdlog::level::debug);
  std::ostringstream log_output;
  auto log_sink = std::make_shared<spdlog::sinks::ostream_sink_mt>(log_output);
  rex::AddSink(log_sink);
  rex::SetAllLevels(spdlog::level::debug);

  void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (!library) {
    std::cerr << dlerror() << '\n';
    return 1;
  }
  const auto abi_version = reinterpret_cast<rex::system::GpuAbiVersionFn>(
      dlsym(library, rex::system::kGpuAbiVersionSymbol));
  const auto create = reinterpret_cast<rex::system::GpuCreateFn>(
      dlsym(library, rex::system::kGpuCreateSymbol));
  if (!abi_version || !create ||
      abi_version() != rex::system::kGpuPluginAbiVersion) {
    dlclose(library);
    return fail("native GPU plugin ABI check failed");
  }

  rex::memory::Memory memory;
  if (!memory.Initialize()) {
    dlclose(library);
    return fail("ReXGlue guest memory initialization failed");
  }
  auto* physical_heap = memory.GetPhysicalHeap();
  const bool ranges_reserved =
      reserve_guest_range(physical_heap, kRingAddress, 0x3000u) &&
      reserve_guest_range(physical_heap, kQueueDescriptorPhysicalAddress,
                          kPageBytes) &&
      reserve_guest_range(physical_heap, kWaitMarkerAddress, kPageBytes) &&
      reserve_guest_range(physical_heap, kWaitScratchAddress, kPageBytes) &&
      reserve_guest_range(physical_heap, kIndirectBufferAddress, kPageBytes) &&
      reserve_guest_range(physical_heap, 0x0975D000u, kPageBytes) &&
      reserve_guest_range(physical_heap, 0x09D50000u, kPageBytes) &&
      reserve_guest_range(physical_heap, 0x09D56000u, kPageBytes) &&
      reserve_guest_range(physical_heap, kTextureAddress, kTextureBytes);
  if (!ranges_reserved) {
    dlclose(library);
    return fail(
        "ReXGlue guest memory could not reserve captured resource addresses");
  }

  uint8_t* const ring_bytes = memory.TranslatePhysical<uint8_t*>(kRingAddress);
  uint8_t* const writeback_bytes =
      memory.TranslatePhysical<uint8_t*>(kWritebackAddress);
  uint8_t* const queue_descriptor_physical =
      memory.TranslatePhysical<uint8_t*>(kQueueDescriptorPhysicalAddress);
  uint8_t* const queue_descriptor_virtual =
      memory.TranslateVirtual<uint8_t*>(kQueueDescriptorVirtualAddress);
  uint8_t* const wait_marker_bytes =
      memory.TranslatePhysical<uint8_t*>(kWaitMarkerAddress);
  uint8_t* const wait_scratch_bytes =
      memory.TranslatePhysical<uint8_t*>(kWaitScratchAddress);
  uint8_t* const indirect_bytes =
      memory.TranslatePhysical<uint8_t*>(kIndirectBufferAddress);
  uint8_t* const index_bytes =
      memory.TranslatePhysical<uint8_t*>(kIndexAddress);
  uint8_t* const vertex_bytes =
      memory.TranslatePhysical<uint8_t*>(kVertexAddress);
  uint8_t* const pixel_shader_bytes =
      memory.TranslatePhysical<uint8_t*>(kPixelShaderAddress);
  uint8_t* const vertex_shader_bytes =
      memory.TranslatePhysical<uint8_t*>(kVertexShaderAddress);
  uint8_t* const texture_bytes =
      memory.TranslatePhysical<uint8_t*>(kTextureAddress);
  if (!ring_bytes || !writeback_bytes || !queue_descriptor_physical ||
      !queue_descriptor_virtual || !wait_marker_bytes || !wait_scratch_bytes ||
      !indirect_bytes || !index_bytes || !vertex_bytes ||
      !pixel_shader_bytes || !vertex_shader_bytes || !texture_bytes) {
    dlclose(library);
    return fail("ReXGlue guest memory translation failed");
  }

  const std::vector<uint8_t> vertex_shader = make_vertex_shader();
  const std::vector<uint8_t> pixel_shader = make_captured_pixel_shader_slice();
  const std::vector<uint8_t> pm4_stream = make_pm4_stream();
  const std::vector<uint8_t> ring_stream = make_ring_stream(pm4_stream);
  if ((pm4_stream.size() & 3u) != 0u || pm4_stream.size() > 0x1000u ||
      ring_stream.size() != 3u * sizeof(uint32_t)) {
    dlclose(library);
    return fail(
        "synthetic live-ring PM4 stream is not dword aligned or exceeds "
        "capacity");
  }
  std::memset(ring_bytes, 0, 0x3000u);
  std::memset(wait_marker_bytes, 0, kPageBytes);
  std::memset(wait_scratch_bytes, 0, kPageBytes);
  std::memcpy(ring_bytes, ring_stream.data(), ring_stream.size());
  std::memcpy(indirect_bytes, pm4_stream.data(), pm4_stream.size());
  write_be32(queue_descriptor_virtual, 1u);
  std::memcpy(vertex_shader_bytes, vertex_shader.data(), vertex_shader.size());
  std::memcpy(pixel_shader_bytes, pixel_shader.data(), pixel_shader.size());
  constexpr uint8_t captured_indices[] = {
      0x00, 0x00, 0x00, 0x01, 0x00, 0x02, 0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
  };
  std::memcpy(index_bytes, captured_indices, sizeof(captured_indices));
  constexpr float normalized_vertices[] = {
      -1.0f, 0.0f, -1.0f, -1.0f, 0.0f, 1.0f,
      1.0f,  0.0f, -1.0f, 1.0f,  0.0f, 1.0f,
  };
  std::array<uint8_t, sizeof(normalized_vertices)> normalized_vertex_bytes{};
  std::memcpy(normalized_vertex_bytes.data(), normalized_vertices,
              normalized_vertex_bytes.size());
  for (size_t offset = 0; offset < normalized_vertex_bytes.size();
       offset += 4u) {
    for (size_t byte = 0; byte < 4u; ++byte) {
      vertex_bytes[offset + byte] = normalized_vertex_bytes[offset + 3u - byte];
    }
  }
  std::memset(texture_bytes, 0xFF, kTextureBytes);

  rex::runtime::FunctionDispatcher dispatcher(&memory, nullptr);
  rex::system::GpuCreateInfo info{};
  info.struct_size = sizeof(info);
  info.backend = "vulkan";
  std::unique_ptr<rex::system::IGraphicsSystem> graphics(
      create(rex::system::kGpuPluginAbiVersion, &info));
  if (!graphics || XFAILED(graphics->SetupPresentation(nullptr)) ||
      XFAILED(graphics->SetupGuestGpu(&dispatcher, nullptr))) {
    graphics.reset();
    dlclose(library);
    return fail("native GPU plugin presentation/guest setup failed");
  }

  graphics->EnableReadPointerWriteBack(kWritebackAddress, 0);
  graphics->InitializeRingBuffer(kRingAddress, kRingSizeLog2);
  auto* mmio = rex::runtime::MMIOHandler::global_handler();
  uint32_t vblank_status = 0;
  if (!mmio || !mmio->CheckLoad(kVblankStatusAddress, &vblank_status) ||
      (vblank_status & 1u) == 0) {
    graphics->Shutdown();
    graphics.reset();
    dlclose(library);
    return fail("guest GPU vblank interrupt-status bit was not asserted");
  }
  const uint32_t stream_dwords = static_cast<uint32_t>(ring_stream.size() / 4u);
  constexpr uint32_t kSubmittedBatches = 3u;
  constexpr uint32_t kRingBytes = 1u << (kRingSizeLog2 + 3u);
  if (ring_stream.size() * kSubmittedBatches > kRingBytes) {
    graphics->Shutdown();
    graphics.reset();
    dlclose(library);
    return fail("successive PM4 fixture batches exceed the guest ring");
  }
  bool consumed_all_batches = true;
  for (uint32_t batch = 1; batch <= kSubmittedBatches; ++batch) {
    const uint32_t batch_end = stream_dwords * batch;
    if (batch > 1u) {
      std::memcpy(
          ring_bytes + static_cast<size_t>(batch - 1u) * ring_stream.size(),
          ring_stream.data(), ring_stream.size());
    }
    if (!mmio->CheckStore(kWritePointerRegister, batch_end)) {
      consumed_all_batches = false;
      break;
    }
    if (batch == 1u) {
      const auto marker_deadline =
          std::chrono::steady_clock::now() + std::chrono::seconds(20);
      while (std::chrono::steady_clock::now() < marker_deadline &&
             read_be32(wait_marker_bytes) != 1u) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
      if (read_be32(wait_marker_bytes) != 1u) {
        consumed_all_batches = false;
        break;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(20));
      if (read_be32(wait_marker_bytes) != 1u ||
          read_be32(writeback_bytes) != 0u) {
        consumed_all_batches = false;
        break;
      }
      store_guest_be32_atomic(wait_scratch_bytes, 4u);
      store_guest_be32_atomic(wait_scratch_bytes + 0x14u, 0x208u);
      store_guest_be32_atomic(wait_scratch_bytes + 0x10u, 0x823A4758u);
    }
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(20);
    while (std::chrono::steady_clock::now() < deadline &&
           read_be32(writeback_bytes) != batch_end) {
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    if (read_be32(writeback_bytes) != batch_end) {
      consumed_all_batches = false;
      break;
    }
    uint32_t coher_status = UINT32_MAX;
    uint32_t coher_base = 0;
    uint32_t coher_size = 0;
    if (!mmio->CheckLoad(kCoherStatusHostAddress, &coher_status) ||
        !mmio->CheckLoad(kCoherBaseHostAddress, &coher_base) ||
        !mmio->CheckLoad(kCoherSizeHostAddress, &coher_size) ||
        coher_status != 0u || coher_base != 0x1B962000u ||
        coher_size != 0x2000u) {
      consumed_all_batches = false;
      break;
    }
  }
  uint32_t read_pointer = 0;
  const bool consumed = consumed_all_batches &&
                        read_be32(writeback_bytes) ==
                            stream_dwords * kSubmittedBatches &&
                        read_be32(wait_marker_bytes) == 2u &&
                        mmio->CheckLoad(kReadPointerRegister, &read_pointer) &&
                        read_pointer == stream_dwords * kSubmittedBatches;
  const bool event_write_visible_through_alias =
      read_be32(queue_descriptor_physical) == 3u &&
      read_be32(queue_descriptor_virtual) == 3u;

  graphics->Shutdown();
  graphics.reset();
  rex::RemoveSink(log_sink);
  dlclose(library);
  const std::string diagnostics = log_output.str();
  const char* debug_fragment_color =
      std::getenv("SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR");
  const char* readback_path =
      std::getenv("SHIFT_NATIVE_VULKAN_READBACK_PATH");
  if (debug_fragment_color &&
      std::string(debug_fragment_color) == "magenta" &&
      diagnostics.find("diagnostic fragment override is active") ==
          std::string::npos) {
    std::cerr << diagnostics << '\n';
    return fail("debug fragment override was not activated");
  }
  if (debug_fragment_color &&
      std::string(debug_fragment_color) == "magenta" && readback_path) {
    const size_t non_black = diagnostics.find("non-black pixels ");
    if (diagnostics.find("saved Vulkan guest output") == std::string::npos ||
        non_black == std::string::npos) {
      std::cerr << diagnostics << '\n';
      return fail("magenta live-ring diagnostic did not read back the image");
    }
    std::istringstream pixel_count_stream(diagnostics.substr(
        non_black + sizeof("non-black pixels ") - 1u));
    size_t non_black_pixels = 0;
    if (!(pixel_count_stream >> non_black_pixels) || non_black_pixels == 0) {
      std::cerr << diagnostics << '\n';
      return fail("magenta live-ring diagnostic produced no visible pixels");
    }
    std::cout << "synthetic live-ring magenta readback: " << non_black_pixels
              << " non-black pixels\n";
  }
  const char* geometry_dump_prefix =
      std::getenv("SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX");
  if (geometry_dump_prefix && *geometry_dump_prefix) {
    const auto read_dump = [](const std::string& path) {
      std::ifstream file(path, std::ios::binary);
      return std::vector<uint8_t>(std::istreambuf_iterator<char>(file), {});
    };
    const std::string vertex_dump_path =
        std::string(geometry_dump_prefix) + ".frame1.draw0.vertices.bin";
    const std::string index_dump_path =
        std::string(geometry_dump_prefix) + ".frame1.draw0.indices.bin";
    const auto dumped_vertices = read_dump(vertex_dump_path);
    const auto dumped_indices = read_dump(index_dump_path);
    constexpr uint8_t expected_indices[] = {
        0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x03, 0x00,
    };
    if (dumped_vertices.size() != normalized_vertex_bytes.size() ||
        !std::equal(dumped_vertices.begin(), dumped_vertices.end(),
                    normalized_vertex_bytes.begin()) ||
        dumped_indices.size() != sizeof(expected_indices) ||
        !std::equal(dumped_indices.begin(), dumped_indices.end(),
                    std::begin(expected_indices))) {
      std::cerr << diagnostics << '\n';
      return fail("selected-frame geometry dump differs from decoded fixture buffers");
    }
    std::cout << "selected-frame raw vertex/index dump matches decoded fixture buffers\n";
  }
  const char* texture_dump_prefix =
      std::getenv("SHIFT_NATIVE_VULKAN_DUMP_TEXTURES_PREFIX");
  if (texture_dump_prefix && *texture_dump_prefix) {
    const std::string texture_dump_path =
        std::string(texture_dump_prefix) + ".frame1.draw0.texture0.rgba8";
    std::ifstream texture_file(texture_dump_path, std::ios::binary);
    const std::vector<uint8_t> dumped_texture(
        std::istreambuf_iterator<char>(texture_file), {});
    if (dumped_texture.size() != kTextureBytes ||
        !std::all_of(dumped_texture.begin(), dumped_texture.end(),
                     [](uint8_t value) { return value == 0xFFu; })) {
      std::cerr << diagnostics << '\n';
      return fail(
          "selected-frame texture dump differs from the captured fixture bytes");
    }
    std::cout << "selected-frame raw texture dump matches captured fixture bytes\n";
  }
  const char* texture_source_dump_prefix =
      std::getenv("SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_PREFIX");
  if (texture_source_dump_prefix && *texture_source_dump_prefix) {
    const std::string texture_source_dump_path =
        std::string(texture_source_dump_prefix) +
        ".frame1.slot0.texture0.source.bin";
    std::ifstream texture_source_file(texture_source_dump_path,
                                      std::ios::binary);
    const std::vector<uint8_t> dumped_texture_source(
        std::istreambuf_iterator<char>(texture_source_file), {});
    if (dumped_texture_source.size() != kTextureBytes ||
        !std::equal(dumped_texture_source.begin(),
                    dumped_texture_source.end(), texture_bytes)) {
      std::cerr << diagnostics << '\n';
      return fail(
          "selected-frame guest texture source dump differs from fixture memory");
    }
    std::cout << "selected-frame guest texture source dump matches fixture memory\n";
    const std::string selected_guest_source_path =
        std::string(texture_source_dump_prefix) +
        ".guest9d57000.first.source.bin";
    std::ifstream selected_guest_source_file(selected_guest_source_path,
                                             std::ios::binary);
    const std::vector<uint8_t> selected_guest_source(
        std::istreambuf_iterator<char>(selected_guest_source_file), {});
    if (selected_guest_source.size() != kTextureBytes ||
        !std::equal(selected_guest_source.begin(), selected_guest_source.end(),
                    texture_bytes)) {
      std::cerr << diagnostics << '\n';
      return fail(
          "guest-address texture source dump differs from fixture memory");
    }
    std::cout << "guest-address texture source dump matches fixture memory\n";
  }
  if (!consumed) {
    std::cerr << diagnostics << '\n';
    return fail("PM4 stream was not consumed through live MMIO");
  }
  if (!event_write_visible_through_alias ||
      diagnostics.find("EVENT_WRITE_SHD #2 initiator=00000003 "
                       "guest=17AF4000 endian=2 packet_value=00000003") ==
          std::string::npos) {
    std::cerr << diagnostics << '\n';
    return fail("EVENT_WRITE_SHD did not update descriptor+0 through its guest alias");
  }
  const char* const submission_marker =
      "submitted 3 captured indexed draw packets to the Vulkan presenter";
  size_t submission_count = 0;
  for (size_t offset = 0;
       (offset = diagnostics.find(submission_marker, offset)) !=
       std::string::npos;
       offset += std::strlen(submission_marker)) {
    ++submission_count;
  }
  const char* const interrupt_marker =
      "consumed 1 PM4_INTERRUPT packets and dispatched 0 guest callbacks";
  size_t interrupt_count = 0;
  for (size_t offset = 0;
       (offset = diagnostics.find(interrupt_marker, offset)) !=
       std::string::npos;
       offset += std::strlen(interrupt_marker)) {
    ++interrupt_count;
  }
  constexpr const char* const coherency_marker =
      "completed captured COHER_STATUS_HOST wait ";
  size_t coherency_wait_count = 0;
  for (size_t offset = 0;
       (offset = diagnostics.find(coherency_marker, offset)) !=
       std::string::npos;
       offset += std::strlen(coherency_marker)) {
    ++coherency_wait_count;
  }
  if (submission_count != kSubmittedBatches ||
      interrupt_count != kSubmittedBatches ||
      coherency_wait_count != kSubmittedBatches ||
      diagnostics.find("2 pointer-loaded shader programs (0 unresolved)") ==
          std::string::npos ||
      diagnostics.find(
          "3 captured indexed draw packets (3 with supported raster state") ==
          std::string::npos ||
      diagnostics.find("3 with resolved resource bytes (0 unresolved)") ==
          std::string::npos ||
      diagnostics.find("1 Vulkan frames submitted") == std::string::npos ||
      diagnostics.find("source=2/primitive=8:1") == std::string::npos) {
    std::cerr << diagnostics << '\n';
    return fail("live PM4 fixture did not reach Vulkan presenter submission");
  }
  std::cout << "live ReXGlue PM4 ring consumed three successive MMIO batches "
               "and submitted each fixture through Vulkan 1.1; fixture uses "
               "synthetic vertex/resource inputs\n";
  std::cout << "EVENT_WRITE_SHD physical write was visible through the guest "
               "descriptor virtual alias\n";
  return 0;
}
