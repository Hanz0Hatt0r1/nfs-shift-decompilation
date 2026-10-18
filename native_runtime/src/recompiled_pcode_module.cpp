#include "shift_recompiled_pcode_module.hpp"
#include "shift_recompiled_pcode_abi.h"

#include <dlfcn.h>
#include <sys/mman.h>

#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace shift::runtime {
namespace {

constexpr uint64_t kGuestRamSize = UINT64_C(1) << 32;
constexpr size_t kRegisterBankSize = 0x1000;
constexpr size_t kMaximumPcodeValueSize = 16;
constexpr uint32_t kMaximumCallDepth = 256;
constexpr uint16_t kPeI386 = 0x014c;
constexpr uint16_t kPe32Magic = 0x010b;
constexpr uint16_t kMaximumPeSectionCount = 96;
constexpr size_t kPeSectionHeaderSize = 40;
constexpr size_t kCopyChunkSize = 64 * 1024;

using PcodeFunction = int (*)(RviPcodeContext*);

struct PeSection {
    uint32_t virtual_address = 0;
    uint32_t virtual_size = 0;
    uint32_t raw_offset = 0;
    uint32_t raw_size = 0;

    uint64_t mapped_size() const {
        return std::max(virtual_size, raw_size);
    }
};

void require_pe(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error("invalid PE32 image: " +
                                 std::string(message));
    }
}

void require_file_range(uint64_t offset, uint64_t size, uint64_t file_size) {
    require_pe(offset <= file_size && size <= file_size - offset,
               "file range is out of bounds");
}

void read_file_range(std::ifstream& file, uint64_t file_size,
                     uint64_t offset, uint8_t* output, size_t size) {
    require_file_range(offset, size, file_size);
    require_pe(offset <= static_cast<uint64_t>(
                            std::numeric_limits<std::streamoff>::max()),
               "file offset cannot be represented by the host stream");
    file.clear();
    file.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
    require_pe(static_cast<bool>(file), "cannot seek in image file");
    file.read(reinterpret_cast<char*>(output),
              static_cast<std::streamsize>(size));
    require_pe(file.gcount() == static_cast<std::streamsize>(size),
               "short read from image file");
}

uint16_t read_u16(std::ifstream& file, uint64_t file_size, uint64_t offset) {
    std::array<uint8_t, 2> bytes{};
    read_file_range(file, file_size, offset, bytes.data(), bytes.size());
    return static_cast<uint16_t>(bytes[0]) |
           static_cast<uint16_t>(static_cast<uint16_t>(bytes[1]) << 8);
}

uint32_t read_u32(std::ifstream& file, uint64_t file_size, uint64_t offset) {
    std::array<uint8_t, 4> bytes{};
    read_file_range(file, file_size, offset, bytes.data(), bytes.size());
    return static_cast<uint32_t>(bytes[0]) |
           (static_cast<uint32_t>(bytes[1]) << 8) |
           (static_cast<uint32_t>(bytes[2]) << 16) |
           (static_cast<uint32_t>(bytes[3]) << 24);
}

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

    Pe32ImageInfo load_pe32_image(const std::string& path) {
        if (pe_image_load_attempted) {
            throw std::runtime_error(
                "a PE32 image load has already been attempted");
        }
        pe_image_load_attempted = true;

        std::ifstream file(path, std::ios::binary | std::ios::ate);
        require_pe(static_cast<bool>(file), "cannot open image file");
        const std::streampos end = file.tellg();
        require_pe(end >= 0, "cannot determine image file size");
        const uint64_t file_size =
            static_cast<uint64_t>(static_cast<std::streamoff>(end));
        require_pe(file_size >= 64, "DOS header is truncated");

        std::array<uint8_t, 64> dos_header{};
        read_file_range(file, file_size, 0, dos_header.data(),
                        dos_header.size());
        require_pe(dos_header[0] == 'M' && dos_header[1] == 'Z',
                   "missing MZ signature");
        const uint32_t pe_offset =
            static_cast<uint32_t>(dos_header[0x3c]) |
            (static_cast<uint32_t>(dos_header[0x3d]) << 8) |
            (static_cast<uint32_t>(dos_header[0x3e]) << 16) |
            (static_cast<uint32_t>(dos_header[0x3f]) << 24);

        require_file_range(pe_offset, 24, file_size);
        std::array<uint8_t, 4> signature{};
        read_file_range(file, file_size, pe_offset, signature.data(),
                        signature.size());
        require_pe(signature == std::array<uint8_t, 4>{'P', 'E', 0, 0},
                   "missing PE signature");

        const uint64_t coff_offset = static_cast<uint64_t>(pe_offset) + 4;
        require_pe(read_u16(file, file_size, coff_offset) == kPeI386,
                   "expected machine type I386");
        const uint16_t section_count =
            read_u16(file, file_size, coff_offset + 2);
        const uint16_t optional_header_size =
            read_u16(file, file_size, coff_offset + 16);
        require_pe(section_count > 0 &&
                       section_count <= kMaximumPeSectionCount,
                   "section count is outside the supported range");
        require_pe(optional_header_size >= 64,
                   "optional header is truncated");

        const uint64_t optional_offset = coff_offset + 20;
        require_file_range(optional_offset, optional_header_size, file_size);
        require_pe(read_u16(file, file_size, optional_offset) == kPe32Magic,
                   "expected PE32 optional header");
        const uint32_t entry_rva =
            read_u32(file, file_size, optional_offset + 16);
        const uint32_t image_base =
            read_u32(file, file_size, optional_offset + 28);
        const uint32_t image_size =
            read_u32(file, file_size, optional_offset + 56);
        const uint32_t headers_size =
            read_u32(file, file_size, optional_offset + 60);
        require_pe(image_size != 0 &&
                       static_cast<uint64_t>(image_base) + image_size <=
                           kGuestRamSize,
                   "image does not fit in the x86-32 guest address space");
        require_pe(headers_size >= optional_offset + optional_header_size +
                                      static_cast<uint64_t>(section_count) *
                                          kPeSectionHeaderSize &&
                       headers_size <= image_size &&
                       headers_size <= file_size,
                   "headers size is inconsistent with the PE tables");
        require_pe(entry_rva == 0 || entry_rva < image_size,
                   "entry point is outside the image");

        const uint64_t section_table_offset =
            optional_offset + optional_header_size;
        require_file_range(section_table_offset,
                           static_cast<uint64_t>(section_count) *
                               kPeSectionHeaderSize,
                           file_size);

        std::vector<PeSection> sections;
        sections.reserve(section_count);
        for (uint16_t index = 0; index < section_count; ++index) {
            const uint64_t section_offset = section_table_offset +
                static_cast<uint64_t>(index) * kPeSectionHeaderSize;
            PeSection section;
            section.virtual_size =
                read_u32(file, file_size, section_offset + 8);
            section.virtual_address =
                read_u32(file, file_size, section_offset + 12);
            section.raw_size =
                read_u32(file, file_size, section_offset + 16);
            section.raw_offset =
                read_u32(file, file_size, section_offset + 20);
            const uint64_t mapped_size = section.mapped_size();
            require_pe(section.virtual_address <= image_size &&
                           mapped_size <= image_size - section.virtual_address,
                       "section exceeds SizeOfImage");
            if (mapped_size != 0) {
                require_pe(section.virtual_address >= headers_size,
                           "section overlaps the mapped headers");
            }
            require_file_range(section.raw_offset, section.raw_size, file_size);
            sections.push_back(section);
        }

        std::vector<PeSection> virtual_order = sections;
        std::sort(virtual_order.begin(), virtual_order.end(),
                  [](const PeSection& left, const PeSection& right) {
                      return left.virtual_address < right.virtual_address;
                  });
        uint64_t previous_end = headers_size;
        for (const auto& section : virtual_order) {
            if (section.mapped_size() == 0) continue;
            require_pe(section.virtual_address >= previous_end,
                       "virtual sections overlap");
            previous_end = section.virtual_address + section.mapped_size();
        }

        std::array<uint8_t, kCopyChunkSize> buffer{};
        auto copy_range = [&](uint64_t file_offset, uint64_t guest_offset,
                              uint64_t size) {
            while (size != 0) {
                const size_t chunk = static_cast<size_t>(
                    std::min<uint64_t>(size, buffer.size()));
                read_file_range(file, file_size, file_offset,
                                buffer.data(), chunk);
                std::memcpy(static_cast<uint8_t*>(ram) + guest_offset,
                            buffer.data(), chunk);
                file_offset += chunk;
                guest_offset += chunk;
                size -= chunk;
            }
        };
        copy_range(0, image_base, headers_size);
        for (const auto& section : sections) {
            if (section.raw_size == 0) continue;
            copy_range(section.raw_offset,
                       static_cast<uint64_t>(image_base) +
                           section.virtual_address,
                       section.raw_size);
        }

        return {image_base, image_size,
                entry_rva == 0 ? 0 : image_base + entry_rva,
                section_count};
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
    bool pe_image_load_attempted = false;
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

Pe32ImageInfo RecompiledPcodeModule::load_pe32_image(const std::string& path) {
    return impl_->load_pe32_image(path);
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
