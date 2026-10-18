#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>

namespace shift::runtime {

struct Pe32ImageInfo {
    uint32_t image_base = 0;
    uint32_t image_size = 0;
    uint32_t entry_point = 0;
    uint16_t section_count = 0;
    uint32_t import_module_count = 0;
    uint32_t import_function_count = 0;
    uint32_t import_stub_base = 0;
};

class RecompiledPcodeModule {
public:
    explicit RecompiledPcodeModule(const std::string& shared_object_path);
    ~RecompiledPcodeModule();

    RecompiledPcodeModule(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule& operator=(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule(RecompiledPcodeModule&&) = delete;
    RecompiledPcodeModule& operator=(RecompiledPcodeModule&&) = delete;

    int call(uint32_t guest_address);
    Pe32ImageInfo load_pe32_image(const std::string& path);
    int call_pe32_entry_point();
    int run_guest_threads();
    bool pe32_entry_point_complete() const;
    bool load_supplemental_module(const std::string& shared_object_path);
    bool load_override_module(const std::string& shared_object_path);
    uint64_t dispatched_function_count() const;
    uint64_t unique_dispatched_function_count() const;
    const std::string& last_error() const;

    bool read_guest(const char* space, uint64_t offset, size_t size,
                    uint8_t* output);
    bool write_guest(const char* space, uint64_t offset, size_t size,
                     const uint8_t* input);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace shift::runtime
