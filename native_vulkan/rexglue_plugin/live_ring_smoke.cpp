#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <iostream>
#include <memory>
#include <thread>

#include <rex/system/function_dispatcher.h>
#include <rex/system/gpu_plugin.h>
#include <rex/system/mmio_handler.h>
#include <rex/system/xmemory.h>

namespace {

constexpr uint32_t kRingAddress = 0x00010000u;
constexpr uint32_t kWritebackAddress = 0x00012000u;
constexpr uint32_t kRingSizeLog2 = 9u;
constexpr uint32_t kWritePointerRegister = 0x7FC80714u;
constexpr uint32_t kReadPointerRegister = 0x7FC80710u;
constexpr std::array<uint8_t, 20> kCapturedDrawPacket = {
    0xC0, 0x03, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04, 0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

uint32_t read_be32(const uint8_t* bytes) {
  return (uint32_t{bytes[0]} << 24) | (uint32_t{bytes[1]} << 16) |
         (uint32_t{bytes[2]} << 8) | uint32_t{bytes[3]};
}

int fail(const char* message) {
  std::cerr << message << '\n';
  return 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) return 2;

  void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  if (!library) {
    std::cerr << dlerror() << '\n';
    return 1;
  }
  const auto abi_version = reinterpret_cast<rex::system::GpuAbiVersionFn>(
      dlsym(library, rex::system::kGpuAbiVersionSymbol));
  const auto create = reinterpret_cast<rex::system::GpuCreateFn>(
      dlsym(library, rex::system::kGpuCreateSymbol));
  if (!abi_version || !create || abi_version() != rex::system::kGpuPluginAbiVersion) {
    dlclose(library);
    return fail("native GPU plugin ABI check failed");
  }

  rex::memory::Memory memory;
  if (!memory.Initialize()) {
    dlclose(library);
    return fail("ReXGlue guest memory initialization failed");
  }
  auto* physical_heap = memory.GetPhysicalHeap();
  if (!physical_heap ||
      !physical_heap->AllocFixed(
          kRingAddress, 0x3000u, 0x1000u,
          rex::memory::kMemoryAllocationReserve | rex::memory::kMemoryAllocationCommit,
          rex::memory::kMemoryProtectRead | rex::memory::kMemoryProtectWrite)) {
    dlclose(library);
    return fail("ReXGlue physical guest memory allocation failed");
  }
  uint8_t* const ring_bytes = memory.TranslatePhysical<uint8_t*>(kRingAddress);
  uint8_t* const writeback_bytes = memory.TranslatePhysical<uint8_t*>(kWritebackAddress);
  std::memset(ring_bytes, 0, 0x3000u);
  std::memcpy(ring_bytes, kCapturedDrawPacket.data(), kCapturedDrawPacket.size());

  rex::runtime::FunctionDispatcher dispatcher(&memory, nullptr);
  rex::system::GpuCreateInfo info{};
  info.struct_size = sizeof(info);
  info.backend = "vulkan";
  std::unique_ptr<rex::system::IGraphicsSystem> graphics(
      create(rex::system::kGpuPluginAbiVersion, &info));
  if (!graphics ||
      XFAILED(graphics->SetupGuestGpu(&dispatcher, nullptr))) {
    graphics.reset();
    dlclose(library);
    return fail("native GPU plugin setup failed");
  }

  graphics->EnableReadPointerWriteBack(kWritebackAddress, 0);
  graphics->InitializeRingBuffer(kRingAddress, kRingSizeLog2);
  auto* mmio = rex::runtime::MMIOHandler::global_handler();
  if (!mmio || !mmio->CheckStore(kWritePointerRegister, 5u)) {
    graphics->Shutdown();
    graphics.reset();
    dlclose(library);
    return fail("guest CP_RB_WPTR MMIO write was not handled");
  }

  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
  while (std::chrono::steady_clock::now() < deadline && read_be32(writeback_bytes) != 5u) {
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  uint32_t read_pointer = 0;
  const bool consumed = read_be32(writeback_bytes) == 5u &&
                        mmio->CheckLoad(kReadPointerRegister, &read_pointer) &&
                        read_pointer == 5u;

  graphics->Shutdown();
  graphics.reset();
  dlclose(library);
  if (!consumed) return fail("captured DRAW_INDX was not consumed through live PM4 MMIO");
  std::cout << "live ReXGlue PM4 ring/MMIO consumption passed\n";
  return 0;
}
