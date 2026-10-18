#include "shift_recompiled_pcode_module.hpp"
#include "shift_recompiled_pcode_abi.h"

#include <dlfcn.h>
#include <sys/mman.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
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
constexpr size_t kPeImportDescriptorSize = 20;
constexpr size_t kCopyChunkSize = 64 * 1024;
constexpr uint32_t kImportStubPreferredBase = 0xf0000000;
constexpr uint32_t kImportStubStride = 0x10;
constexpr uint64_t kWindowsFileTimeUnixEpoch = UINT64_C(116444736000000000);
constexpr uint64_t kWindowsFileTimeTicksPerSecond = UINT64_C(10000000);
constexpr uint64_t kX86EspRegisterOffset = 0x10;
constexpr size_t kMaximumImportDescriptors = 4096;
constexpr size_t kMaximumImportThunksPerModule = 65536;
constexpr size_t kMaximumImportFunctions = 65536;
constexpr size_t kMaximumImportNameSize = 512;

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

struct ImportedThunk {
    uint32_t iat_rva = 0;
    std::string name;
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

uint64_t file_offset_for_rva(uint32_t rva, size_t size,
                             uint32_t headers_size,
                             const std::vector<PeSection>& sections) {
    if (rva <= headers_size && size <= headers_size - rva) return rva;
    for (const auto& section : sections) {
        if (rva < section.virtual_address) continue;
        const uint64_t delta =
            static_cast<uint64_t>(rva) - section.virtual_address;
        if (delta <= section.raw_size && size <= section.raw_size - delta) {
            return static_cast<uint64_t>(section.raw_offset) + delta;
        }
    }
    throw std::runtime_error(
        "invalid PE32 image: import RVA has no raw file backing");
}

uint32_t read_rva_u32(std::ifstream& file, uint64_t file_size, uint32_t rva,
                      uint32_t headers_size,
                      const std::vector<PeSection>& sections) {
    return read_u32(file, file_size,
                    file_offset_for_rva(rva, sizeof(uint32_t), headers_size,
                                        sections));
}

std::string read_import_name(std::ifstream& file, uint64_t file_size,
                             uint32_t rva, uint32_t headers_size,
                             const std::vector<PeSection>& sections) {
    std::string name;
    name.reserve(32);
    for (size_t index = 0; index < kMaximumImportNameSize; ++index) {
        require_pe(static_cast<uint64_t>(rva) + index <=
                       std::numeric_limits<uint32_t>::max(),
                   "import name RVA overflows");
        const uint64_t offset = file_offset_for_rva(
            rva + static_cast<uint32_t>(index), 1, headers_size, sections);
        uint8_t byte = 0;
        read_file_range(file, file_size, offset, &byte, 1);
        if (byte == 0) {
            require_pe(!name.empty(), "import name is empty");
            return name;
        }
        require_pe(byte >= 0x20 && byte <= 0x7e,
                   "import name contains a non-ASCII byte");
        name.push_back(static_cast<char>(byte));
    }
    throw std::runtime_error(
        "invalid PE32 image: import name is not terminated");
}

uint32_t choose_import_stub_base(uint32_t image_base, uint32_t image_size,
                                 size_t unique_import_count) {
    if (unique_import_count == 0) return 0;
    const uint64_t span = static_cast<uint64_t>(unique_import_count) *
                          kImportStubStride;
    const uint64_t image_end =
        static_cast<uint64_t>(image_base) + image_size;
    uint64_t candidate = kImportStubPreferredBase;
    if (candidate + span > (UINT64_C(1) << 32) ||
        (candidate < image_end && image_base < candidate + span)) {
        require_pe(static_cast<uint64_t>(image_base) >= span + 0x10000,
                   "no guest address range is available for import traps");
        candidate = (static_cast<uint64_t>(image_base) - span) &
                    ~static_cast<uint64_t>(kImportStubStride - 1);
    }
    require_pe(candidate >= 0x10000 &&
                   candidate + span <= (UINT64_C(1) << 32) &&
                   !(candidate < image_end && image_base < candidate + span),
               "no guest address range is available for import traps");
    return static_cast<uint32_t>(candidate);
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
        const auto imported = import_traps.find(
            static_cast<uint32_t>(target));
        if (imported != import_traps.end()) {
            if (imported->second ==
                "KERNEL32.dll!GetSystemTimeAsFileTime") {
                return get_system_time_as_file_time();
            }
            error = "unimplemented PE import " + imported->second;
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

    int get_system_time_as_file_time() {
        std::array<uint8_t, 4> bytes{};
        if (!read_guest("register", kX86EspRegisterOffset,
                        bytes.size(), bytes.data())) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime cannot read ESP";
            return -1;
        }
        const uint32_t esp = static_cast<uint32_t>(bytes[0]) |
            (static_cast<uint32_t>(bytes[1]) << 8) |
            (static_cast<uint32_t>(bytes[2]) << 16) |
            (static_cast<uint32_t>(bytes[3]) << 24);
        const uint64_t argument_address = static_cast<uint64_t>(esp) + 4;
        if (!read_guest("ram", argument_address, bytes.size(), bytes.data())) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime has an invalid stack argument";
            return -1;
        }
        const uint32_t output_address = static_cast<uint32_t>(bytes[0]) |
            (static_cast<uint32_t>(bytes[1]) << 8) |
            (static_cast<uint32_t>(bytes[2]) << 16) |
            (static_cast<uint32_t>(bytes[3]) << 24);
        if (output_address == 0 ||
            static_cast<uint64_t>(output_address) + sizeof(uint64_t) >
                kGuestRamSize) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime has an invalid output pointer";
            return -1;
        }

        using FileTimeDuration = std::chrono::duration<
            int64_t, std::ratio<1, kWindowsFileTimeTicksPerSecond>>;
        const auto unix_ticks = std::chrono::duration_cast<FileTimeDuration>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        if (unix_ticks < 0) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime host clock predates Unix epoch";
            return -1;
        }
        const uint64_t filetime = kWindowsFileTimeUnixEpoch +
                                  static_cast<uint64_t>(unix_ticks);
        std::array<uint8_t, sizeof(filetime)> filetime_bytes{};
        for (size_t index = 0; index < filetime_bytes.size(); ++index) {
            filetime_bytes[index] =
                static_cast<uint8_t>(filetime >> (index * 8));
        }
        if (!write_guest("ram", output_address, filetime_bytes.size(),
                         filetime_bytes.data())) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime cannot write FILETIME";
            return -1;
        }

        const uint32_t caller_esp = esp + 8;
        for (size_t index = 0; index < bytes.size(); ++index) {
            bytes[index] =
                static_cast<uint8_t>(caller_esp >> (index * 8));
        }
        if (!write_guest("register", kX86EspRegisterOffset,
                         bytes.size(), bytes.data())) {
            error = "KERNEL32.dll!GetSystemTimeAsFileTime cannot restore ESP";
            return -1;
        }
        return 0;
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
        uint32_t import_directory_rva = 0;
        uint32_t import_directory_size = 0;
        const uint32_t data_directory_count = optional_header_size >= 96
            ? read_u32(file, file_size, optional_offset + 92)
            : 0;
        if (data_directory_count > 1) {
            require_pe(optional_header_size >= 112,
                       "optional header truncates the import directory");
            import_directory_rva =
                read_u32(file, file_size, optional_offset + 104);
            import_directory_size =
                read_u32(file, file_size, optional_offset + 108);
        }
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
        require_pe((import_directory_rva == 0) ==
                       (import_directory_size == 0),
                   "import directory RVA and size disagree");
        if (import_directory_rva != 0) {
            require_pe(import_directory_size >=
                           2 * kPeImportDescriptorSize &&
                           static_cast<uint64_t>(import_directory_rva) +
                                   import_directory_size <=
                               image_size,
                       "import directory exceeds the PE image");
        }

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

        std::vector<ImportedThunk> imported_thunks;
        std::vector<std::string> import_modules;
        std::unordered_set<uint32_t> imported_iat_slots;
        if (import_directory_rva != 0) {
            require_pe(import_directory_size % kPeImportDescriptorSize == 0,
                       "import directory size is not descriptor aligned");
            const size_t descriptor_count =
                import_directory_size / kPeImportDescriptorSize;
            require_pe(descriptor_count <= kMaximumImportDescriptors,
                       "import directory has too many descriptors");
            bool found_terminator = false;
            for (size_t descriptor_index = 0;
                 descriptor_index < descriptor_count; ++descriptor_index) {
                const uint64_t descriptor_rva =
                    static_cast<uint64_t>(import_directory_rva) +
                    descriptor_index * kPeImportDescriptorSize;
                require_pe(descriptor_rva <=
                               std::numeric_limits<uint32_t>::max(),
                           "import descriptor RVA overflows");
                const uint64_t descriptor_offset = file_offset_for_rva(
                    static_cast<uint32_t>(descriptor_rva),
                    kPeImportDescriptorSize, headers_size, sections);
                const uint32_t lookup_table_rva =
                    read_u32(file, file_size, descriptor_offset);
                const uint32_t timestamp =
                    read_u32(file, file_size, descriptor_offset + 4);
                const uint32_t forwarder_chain =
                    read_u32(file, file_size, descriptor_offset + 8);
                const uint32_t module_name_rva =
                    read_u32(file, file_size, descriptor_offset + 12);
                const uint32_t first_thunk_rva =
                    read_u32(file, file_size, descriptor_offset + 16);
                if (lookup_table_rva == 0 && timestamp == 0 &&
                    forwarder_chain == 0 && module_name_rva == 0 &&
                    first_thunk_rva == 0) {
                    found_terminator = true;
                    break;
                }
                require_pe(module_name_rva != 0 && first_thunk_rva != 0,
                           "import descriptor omits a name or IAT");
                const std::string module_name = read_import_name(
                    file, file_size, module_name_rva, headers_size, sections);
                if (std::find(import_modules.begin(), import_modules.end(),
                              module_name) == import_modules.end()) {
                    import_modules.push_back(module_name);
                }
                const uint32_t thunk_table_rva =
                    lookup_table_rva != 0 ? lookup_table_rva : first_thunk_rva;
                bool found_thunk_terminator = false;
                for (size_t thunk_index = 0;
                     thunk_index < kMaximumImportThunksPerModule;
                     ++thunk_index) {
                    const uint64_t thunk_rva =
                        static_cast<uint64_t>(thunk_table_rva) +
                        thunk_index * sizeof(uint32_t);
                    const uint64_t iat_rva =
                        static_cast<uint64_t>(first_thunk_rva) +
                        thunk_index * sizeof(uint32_t);
                    require_pe(thunk_rva <=
                                   std::numeric_limits<uint32_t>::max() &&
                                   thunk_rva + sizeof(uint32_t) <= image_size &&
                                   iat_rva <=
                                       std::numeric_limits<uint32_t>::max() &&
                                   iat_rva + sizeof(uint32_t) <= image_size,
                               "import thunk exceeds the PE image");
                    const uint32_t thunk_value = read_rva_u32(
                        file, file_size, static_cast<uint32_t>(thunk_rva),
                        headers_size, sections);
                    if (thunk_value == 0) {
                        found_thunk_terminator = true;
                        break;
                    }
                    require_pe(imported_thunks.size() <
                                   kMaximumImportFunctions,
                               "PE image has too many imported functions");
                    std::string function_name;
                    if ((thunk_value & 0x80000000u) != 0) {
                        require_pe((thunk_value & 0x7fff0000u) == 0,
                                   "ordinal import has reserved bits set");
                        function_name = "#" +
                            std::to_string(thunk_value & 0xffffu);
                    } else {
                        require_pe(static_cast<uint64_t>(thunk_value) + 2 <=
                                       image_size,
                                   "import-by-name entry exceeds the PE image");
                        (void)file_offset_for_rva(
                            thunk_value, 2, headers_size, sections);
                        function_name = read_import_name(
                            file, file_size, thunk_value + 2, headers_size,
                            sections);
                    }
                    require_pe(imported_iat_slots.emplace(
                                   static_cast<uint32_t>(iat_rva)).second,
                               "multiple imports share one IAT slot");
                    imported_thunks.push_back({
                        static_cast<uint32_t>(iat_rva),
                        module_name + "!" + function_name});
                }
                require_pe(found_thunk_terminator,
                           "import thunk array has no terminator");
            }
            require_pe(found_terminator,
                       "import descriptor table has no terminator");
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

        std::vector<std::string> unique_imports;
        std::unordered_map<std::string, size_t> import_indices;
        for (const auto& thunk : imported_thunks) {
            const size_t index = unique_imports.size();
            if (import_indices.emplace(thunk.name, index).second) {
                unique_imports.push_back(thunk.name);
            }
        }
        const uint32_t import_stub_base = choose_import_stub_base(
            image_base, image_size, unique_imports.size());
        for (size_t index = 0; index < unique_imports.size(); ++index) {
            const uint32_t stub = static_cast<uint32_t>(
                static_cast<uint64_t>(import_stub_base) +
                index * kImportStubStride);
            import_traps.emplace(stub, unique_imports[index]);
        }
        for (const auto& thunk : imported_thunks) {
            const size_t index = import_indices.at(thunk.name);
            const uint32_t stub = static_cast<uint32_t>(
                static_cast<uint64_t>(import_stub_base) +
                index * kImportStubStride);
            const std::array<uint8_t, 4> bytes = {
                static_cast<uint8_t>(stub),
                static_cast<uint8_t>(stub >> 8),
                static_cast<uint8_t>(stub >> 16),
                static_cast<uint8_t>(stub >> 24),
            };
            const uint64_t guest_offset =
                static_cast<uint64_t>(image_base) + thunk.iat_rva;
            std::memcpy(static_cast<uint8_t*>(ram) + guest_offset,
                        bytes.data(), bytes.size());
        }

        return {image_base, image_size,
                entry_rva == 0 ? 0 : image_base + entry_rva,
                section_count,
                static_cast<uint32_t>(import_modules.size()),
                static_cast<uint32_t>(imported_thunks.size()),
                import_stub_base};
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
    std::unordered_map<uint32_t, std::string> import_traps;
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
