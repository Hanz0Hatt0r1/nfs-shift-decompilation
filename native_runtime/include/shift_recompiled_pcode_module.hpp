#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>

namespace shift::runtime {

class RecompiledPcodeModule {
public:
    explicit RecompiledPcodeModule(const std::string& shared_object_path);
    ~RecompiledPcodeModule();

    RecompiledPcodeModule(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule& operator=(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule(RecompiledPcodeModule&&) = delete;
    RecompiledPcodeModule& operator=(RecompiledPcodeModule&&) = delete;

    int call(uint32_t guest_address);
    uint64_t dispatched_function_count() const;
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
