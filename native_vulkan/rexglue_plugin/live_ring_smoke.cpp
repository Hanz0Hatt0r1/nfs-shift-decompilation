#include <dlfcn.h>
#include <rex/logging/api.h>
#include <rex/system/function_dispatcher.h>
#include <rex/system/gpu_plugin.h>
#include <rex/system/mmio_handler.h>
#include <rex/system/xmemory.h>
#include <spdlog/sinks/ostream_sink.h>

#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
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
constexpr uint32_t kIndexAddress = 0x0975D7B0u;
constexpr uint32_t kVertexAddress = 0x0975DFD0u;
constexpr uint32_t kPixelShaderAddress = 0x09D50460u;
constexpr uint32_t kVertexShaderAddress = 0x09D568E0u;
constexpr uint32_t kTextureAddress = 0x09D57000u;
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
  // A simple export ALU instruction writes the fetched position to the output.
  write_shader_triplet(&shader, 3, 0xC80F8000u, 0, 0xA1000000u);
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
  // Raster registers from the captured 1280x720 gamma RGBA8/D24S8 draw.
  constexpr std::array<std::pair<uint32_t, uint32_t>, 16> raster_registers = {{
      {0x2000u, 0x14000500u},
      {0x2001u, 0x00010000u},
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
  }};
  for (const auto& [index, value] : raster_registers)
    append_type0(&stream, index, value);

  // Captured shader controls and fetch descriptors. The synthetic VS multiplies
  // positions by c0, so use ones instead of collapsing the test geometry to 0.
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
  append_type3(&stream, 0x64u,
               {0x53574150u, kFrontbufferAddress, kTargetWidth, kTargetHeight});
  return stream;
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
  if (!ring_bytes || !writeback_bytes || !index_bytes || !vertex_bytes ||
      !pixel_shader_bytes || !vertex_shader_bytes || !texture_bytes) {
    dlclose(library);
    return fail("ReXGlue guest memory translation failed");
  }

  const std::vector<uint8_t> vertex_shader = make_vertex_shader();
  const std::vector<uint8_t> pixel_shader = make_captured_pixel_shader_slice();
  const std::vector<uint8_t> pm4_stream = make_pm4_stream();
  if ((pm4_stream.size() & 3u) != 0u || pm4_stream.size() > 0x1000u) {
    dlclose(library);
    return fail(
        "synthetic live-ring PM4 stream is not dword aligned or exceeds "
        "capacity");
  }
  std::memset(ring_bytes, 0, 0x3000u);
  std::memcpy(ring_bytes, pm4_stream.data(), pm4_stream.size());
  std::memcpy(vertex_shader_bytes, vertex_shader.data(), vertex_shader.size());
  std::memcpy(pixel_shader_bytes, pixel_shader.data(), pixel_shader.size());
  constexpr uint8_t captured_indices[] = {
      0x00, 0x00, 0x00, 0x01, 0x00, 0x02, 0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
  };
  std::memcpy(index_bytes, captured_indices, sizeof(captured_indices));
  constexpr float normalized_vertices[] = {
      -1.0f, -1.0f, 0.0f, 1.0f, -1.0f, 0.0f,
      -1.0f, 1.0f,  0.0f, 1.0f, 1.0f,  0.0f,
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
  const uint32_t stream_dwords = static_cast<uint32_t>(pm4_stream.size() / 4u);
  if (!mmio || !mmio->CheckStore(kWritePointerRegister, stream_dwords)) {
    graphics->Shutdown();
    graphics.reset();
    dlclose(library);
    return fail("guest CP_RB_WPTR MMIO write was not handled");
  }

  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(20);
  while (std::chrono::steady_clock::now() < deadline &&
         read_be32(writeback_bytes) != stream_dwords) {
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  uint32_t read_pointer = 0;
  const bool consumed = read_be32(writeback_bytes) == stream_dwords &&
                        mmio->CheckLoad(kReadPointerRegister, &read_pointer) &&
                        read_pointer == stream_dwords;

  graphics->Shutdown();
  graphics.reset();
  rex::RemoveSink(log_sink);
  dlclose(library);
  const std::string diagnostics = log_output.str();
  const char* debug_fragment_color =
      std::getenv("SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR");
  if (debug_fragment_color &&
      std::string(debug_fragment_color) == "magenta" &&
      diagnostics.find("diagnostic fragment override is active") ==
          std::string::npos) {
    std::cerr << diagnostics << '\n';
    return fail("debug fragment override was not activated");
  }
  if (!consumed) {
    std::cerr << diagnostics << '\n';
    return fail("PM4 stream was not consumed through live MMIO");
  }
  if (diagnostics.find("2 pointer-loaded shader programs (0 unresolved)") ==
          std::string::npos ||
      diagnostics.find(
          "2 captured indexed draw packets (2 with supported raster state") ==
          std::string::npos ||
      diagnostics.find("2 with resolved resource bytes (0 unresolved)") ==
          std::string::npos ||
      diagnostics.find("1 Vulkan frames submitted") == std::string::npos ||
      diagnostics.find("submitted 2 captured indexed draw packets to the "
                       "Vulkan presenter") == std::string::npos) {
    std::cerr << diagnostics << '\n';
    return fail("live PM4 fixture did not reach Vulkan presenter submission");
  }
  std::cout << "live ReXGlue PM4 ring reached Vulkan 1.1 presenter submission; "
               "fixture uses synthetic vertex/resource inputs\n";
  return 0;
}
