#include <cstdint>
#include <cstring>
#include <iostream>

#include <dlfcn.h>

#include <rex/system/gpu_plugin.h>

int main(int argc, char** argv) {
  if (argc != 2 && argc != 3) return 2;
  const bool sampler_anisotropy_check = argc == 3;
  if (sampler_anisotropy_check && std::strcmp(argv[2], "--sampler-anisotropy") != 0) return 2;

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
    return 1;
  }

  rex::system::GpuCreateInfo info{};
  info.struct_size = sizeof(info);
  info.backend = "vulkan";
  auto* graphics = create(rex::system::kGpuPluginAbiVersion, &info);
  if (!graphics || graphics->has_presentation()) {
    delete graphics;
    dlclose(library);
    return 1;
  }
  delete graphics;

  if (sampler_anisotropy_check) {
    using SamplerAnisotropyCheckFn = int (*)();
    const auto check = reinterpret_cast<SamplerAnisotropyCheckFn>(
        dlsym(library, "rexgpu_shift_native_check_sampler_anisotropy"));
    if (!check) {
      std::cerr << "plugin does not expose the sampler anisotropy test hook\n";
      dlclose(library);
      return 1;
    }
    const int result = check();
    dlclose(library);
    return result;
  }

  info.backend = "unsupported";
  const bool rejected_backend =
      create(rex::system::kGpuPluginAbiVersion, &info) == nullptr;
  info.backend = "vulkan";
  info.struct_size = 0;
  const bool rejected_short_info =
      create(rex::system::kGpuPluginAbiVersion, &info) == nullptr;
  info.struct_size = sizeof(info);
  const bool rejected_abi = create(rex::system::kGpuPluginAbiVersion + 1, &info) == nullptr;
  dlclose(library);

  if (!rejected_backend || !rejected_short_info || !rejected_abi) return 1;
  return 0;
}
