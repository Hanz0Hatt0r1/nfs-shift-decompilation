#include "shift_recompiled_pcode_module.hpp"
#include "shift_recompiled_pcode_abi.h"

#include <dlfcn.h>
#include <sys/mman.h>

#include <array>
#include <cstdio>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <unordered_map>

namespace shift::runtime {
namespace {

constexpr uint64_t kGuestRamSize = UINT64_C(1) << 32;
constexpr size_t kRegisterBankSize = 0x1000;
constexpr size_t kMaximumPcodeValueSize = 16;
constexpr uint32_t kMaximumCallDepth = 256;

using PcodeFunction = int (*)(RviPcodeContext*);

}  // namespace

struct RecompiledPcodeModule::Impl {
    explicit Impl(const std::string& path) {
        static_assert(sizeof(size_t) >= sizeof(uint64_t),
                      "the guest RAM reservation requires a 64-bit host");
        ram = mmap(nullptr, static_cast<size_t>(kGuestRamSize),
                   PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
        if (ram == MAP_FAILED) {
            ram = nullptr;
            throw std::runtime_error("cannot reserve 4 GiB guest RAM");
        }

        module = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!module) {
            const char* error = dlerror();
            munmap(ram, static_cast<size_t>(kGuestRamSize));
            ram = nullptr;
            throw std::runtime_error("cannot load P-code module: " +
                                     std::string(error ? error : "unknown dlopen error"));
        }
        context = {this, &read_callback, &write_callback,
                   &call_callback, &reject_userop_callback};
    }

    ~Impl() {
        if (module) dlclose(module);
        if (ram) munmap(ram, static_cast<size_t>(kGuestRamSize));
    }

    static int read_callback(void* opaque, const char* space, uint64_t offset,
                             size_t size, uint8_t* output) {
        auto* self = static_cast<Impl*>(opaque);
        return self && self->read_guest(space, offset, size, output) ? 0 : -1;
    }

    static int write_callback(void* opaque, const char* space, uint64_t offset,
                              size_t size, const uint8_t* input) {
        auto* self = static_cast<Impl*>(opaque);
        return self && self->write_guest(space, offset, size, input) ? 0 : -1;
    }

    static int call_callback(void* opaque, uint64_t target) {
        auto* self = static_cast<Impl*>(opaque);
        return self ? self->dispatch(target) : -1;
    }

    static int reject_userop_callback(void* opaque, uint32_t index,
                                      const uint64_t*, const unsigned*, size_t,
                                      uint64_t*, unsigned) {
        auto* self = static_cast<Impl*>(opaque);
        if (self) {
            self->error = "unhandled P-code userop index " +
                          std::to_string(index);
        }
        return -1;
    }

    PcodeFunction resolve(uint32_t address) {
        const auto found = functions.find(address);
        if (found != functions.end()) return found->second;

        char symbol[16]{};
        std::snprintf(symbol, sizeof(symbol), "rvi_%08x", address);
        dlerror();
        void* value = dlsym(module, symbol);
        const char* lookup_error = dlerror();
        if (lookup_error || !value) {
            error = "P-code module has no exported function " +
                    std::string(symbol);
            return nullptr;
        }
        auto function = reinterpret_cast<PcodeFunction>(value);
        functions.emplace(address, function);
        return function;
    }

    int dispatch(uint64_t target) {
        if (target > std::numeric_limits<uint32_t>::max()) {
            error = "P-code call target exceeds the x86-32 address space";
            return -1;
        }
        if (call_depth >= kMaximumCallDepth) {
            error = "P-code call depth limit exceeded";
            return -1;
        }
        const auto function = resolve(static_cast<uint32_t>(target));
        if (!function) return -1;

        ++call_depth;
        ++function_count;
        const int result = function(&context);
        --call_depth;
        if (result != 0 && error.empty()) {
            char message[96]{};
            std::snprintf(message, sizeof(message),
                          "P-code function 0x%08x returned %d",
                          static_cast<uint32_t>(target), result);
            error = message;
        }
        return result;
    }

    bool read_guest(const char* space, uint64_t offset, size_t size,
                    uint8_t* output) {
        if (!space || !output || size == 0 || size > kMaximumPcodeValueSize) {
            error = "invalid P-code memory read request";
            return false;
        }
        if (std::strcmp(space, "register") == 0) {
            if (offset > kRegisterBankSize ||
                size > kRegisterBankSize - static_cast<size_t>(offset)) {
                error = "P-code register read is out of range";
                return false;
            }
            std::memcpy(output, registers.data() + offset, size);
            return true;
        }
        if (std::strcmp(space, "ram") == 0) {
            if (offset > kGuestRamSize || size > kGuestRamSize - offset) {
                error = "P-code RAM read is out of range";
                return false;
            }
            std::memcpy(output, static_cast<const uint8_t*>(ram) + offset,
                        size);
            return true;
        }
        error = "unsupported P-code address space: " + std::string(space);
        return false;
    }

    bool write_guest(const char* space, uint64_t offset, size_t size,
                     const uint8_t* input) {
        if (!space || !input || size == 0 || size > kMaximumPcodeValueSize) {
            error = "invalid P-code memory write request";
            return false;
        }
        if (std::strcmp(space, "register") == 0) {
            if (offset > kRegisterBankSize ||
                size > kRegisterBankSize - static_cast<size_t>(offset)) {
                error = "P-code register write is out of range";
                return false;
            }
            std::memcpy(registers.data() + offset, input, size);
            return true;
        }
        if (std::strcmp(space, "ram") == 0) {
            if (offset > kGuestRamSize || size > kGuestRamSize - offset) {
                error = "P-code RAM write is out of range";
                return false;
            }
            std::memcpy(static_cast<uint8_t*>(ram) + offset, input, size);
            return true;
        }
        error = "unsupported P-code address space: " + std::string(space);
        return false;
    }

    void* module = nullptr;
    void* ram = nullptr;
    std::array<uint8_t, kRegisterBankSize> registers{};
    RviPcodeContext context{};
    std::unordered_map<uint32_t, PcodeFunction> functions;
    uint64_t function_count = 0;
    uint32_t call_depth = 0;
    std::string error;
};

RecompiledPcodeModule::RecompiledPcodeModule(const std::string& shared_object_path)
    : impl_(std::make_unique<Impl>(shared_object_path)) {}

RecompiledPcodeModule::~RecompiledPcodeModule() = default;

int RecompiledPcodeModule::call(uint32_t guest_address) {
    impl_->error.clear();
    if (impl_->call_depth != 0) {
        impl_->error = "cannot begin a P-code entry call during dispatch";
        return -1;
    }
    return impl_->dispatch(guest_address);
}

uint64_t RecompiledPcodeModule::dispatched_function_count() const {
    return impl_->function_count;
}

const std::string& RecompiledPcodeModule::last_error() const {
    return impl_->error;
}

bool RecompiledPcodeModule::read_guest(const char* space, uint64_t offset,
                                       size_t size, uint8_t* output) {
    return impl_->read_guest(space, offset, size, output);
}

bool RecompiledPcodeModule::write_guest(const char* space, uint64_t offset,
                                        size_t size, const uint8_t* input) {
    return impl_->write_guest(space, offset, size, input);
}

}  // namespace shift::runtime
