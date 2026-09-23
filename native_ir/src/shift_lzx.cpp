#include "shift_lzx.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace {

constexpr int LZX_MIN_MATCH = 2;
constexpr int LZX_NUM_CHARS = 256;
constexpr int LZX_NUM_PRIMARY_LENGTHS = 7;
constexpr int LZX_NUM_SECONDARY_LENGTHS = 249;

const std::array<int, 50> EXTRA_BITS = {
    0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13,
    14,14,15,15,16,16,17,17,17,17,17,17,17,17,17,17,17,17,17,17
};
const std::array<int, 50> POSITION_BASE = {
    0,1,2,3,4,6,8,12,16,24,32,48,64,96,128,192,256,384,512,768,
    1024,1536,2048,3072,4096,6144,8192,12288,16384,24576,32768,49152,
    65536,98304,131072,196608,262144,393216,524288,655360,786432,917504,
    1048576,1179648,1310720,1441792,1572864,1703936,1835008,1966080
};

struct BitReader {
    const std::uint8_t* data{};
    std::size_t size{};
    std::size_t pos{};
    std::uint64_t word{};
    int bits{};

    void ensure(int n) {
        while (bits < n) {
            if (pos + 2 > size) throw std::runtime_error("LZX input exhausted");
            std::uint32_t nxt = std::uint32_t(data[pos]) | (std::uint32_t(data[pos+1]) << 8);
            pos += 2;
            word = (word << 16) | nxt;
            bits += 16;
            if (bits > 56) throw std::runtime_error("LZX bit buffer overflow");
        }
    }
    std::uint32_t peek(int n) { ensure(n); return std::uint32_t(word >> (bits - n)); }
    void consume(int n) {
        if (n < 0 || n > bits) throw std::runtime_error("invalid LZX bit consume");
        bits -= n;
        if (bits == 0) word = 0;
        else word &= ((std::uint64_t(1) << bits) - 1);
    }
    std::uint32_t read(int n) {
        if (n == 0) return 0;
        auto v = peek(n); consume(n); return v;
    }
    void align16() { word = 0; bits = 0; }
    std::uint32_t read_u32le() {
        if (bits != 0) throw std::runtime_error("LZX stream not word-aligned");
        if (pos + 4 > size) throw std::runtime_error("LZX input exhausted");
        std::uint32_t v = std::uint32_t(data[pos]) | (std::uint32_t(data[pos+1]) << 8) |
                          (std::uint32_t(data[pos+2]) << 16) | (std::uint32_t(data[pos+3]) << 24);
        pos += 4; return v;
    }
};

struct HuffmanTable {
    int table_bits{};
    std::vector<std::uint32_t> lookup;
    std::unordered_map<std::uint64_t, std::uint16_t> long_codes;
};

HuffmanTable build_huffman(const std::vector<int>& lengths, int table_bits) {
    int max_len = 0; for (int l : lengths) max_len = std::max(max_len, l);
    std::vector<int> counts(max_len + 1, 0);
    for (int l : lengths) if (l) counts[l]++;
    std::vector<int> next_code(max_len + 1, 0);
    int code = 0;
    for (int bits = 1; bits <= max_len; ++bits) {
        code = (code + counts[bits-1]) << 1;
        next_code[bits] = code;
    }
    HuffmanTable t;
    t.table_bits = table_bits;
    t.lookup.assign(std::size_t(1) << table_bits, 0);
    for (std::size_t symbol = 0; symbol < lengths.size(); ++symbol) {
        int len = lengths[symbol]; if (!len) continue;
        int c = next_code[len]++;
        std::uint64_t key = (std::uint64_t(len) << 32) | std::uint32_t(c);
        t.long_codes.emplace(key, static_cast<std::uint16_t>(symbol));
        if (len <= table_bits) {
            int base = c << (table_bits - len);
            int fill = 1 << (table_bits - len);
            std::uint32_t packed = (std::uint32_t(len) << 16) | static_cast<std::uint32_t>(symbol);
            for (int i = 0; i < fill; ++i) t.lookup[base+i] = packed;
        }
    }
    return t;
}

int huff_decode(BitReader& br, const HuffmanTable& t) {
    br.ensure(t.table_bits);
    std::uint32_t packed = t.lookup[br.peek(t.table_bits)];
    if (packed) {
        int len = int(packed >> 16); int sym = int(packed & 0xffffu); br.consume(len); return sym;
    }
    std::uint32_t code = 0;
    for (int len = 1; len <= 16; ++len) {
        code = (code << 1) | br.read(1);
        std::uint64_t key = (std::uint64_t(len) << 32) | code;
        auto it = t.long_codes.find(key);
        if (it != t.long_codes.end()) return it->second;
    }
    throw std::runtime_error("invalid LZX Huffman code");
}

void read_code_lengths(BitReader& br, std::vector<int>& lengths, int first, int last) {
    std::vector<int> pretree(20);
    for (int& x : pretree) x = int(br.read(4));
    auto pt = build_huffman(pretree, 6);
    int x = first;
    while (x < last) {
        int z = huff_decode(br, pt);
        if (z == 17) {
            int run = int(br.read(4)) + 4;
            if (x + run > last) throw std::runtime_error("LZX length run overflow");
            while (run--) lengths[x++] = 0;
        } else if (z == 18) {
            int run = int(br.read(5)) + 20;
            if (x + run > last) throw std::runtime_error("LZX length run overflow");
            while (run--) lengths[x++] = 0;
        } else if (z == 19) {
            int run = int(br.read(1)) + 4;
            int z2 = huff_decode(br, pt);
            z2 = lengths[x] - z2; if (z2 < 0) z2 += 17;
            if (x + run > last) throw std::runtime_error("LZX length run overflow");
            while (run--) lengths[x++] = z2;
        } else {
            int z2 = lengths[x] - z; if (z2 < 0) z2 += 17;
            lengths[x++] = z2;
        }
    }
}

struct LZXState {
    static constexpr int WINDOW_BITS = 17;
    static constexpr int WINDOW_SIZE = 1 << WINDOW_BITS;
    static constexpr int MAIN_ELEMENTS = 256 + ((WINDOW_BITS * 2) << 3);
    std::vector<std::uint8_t> window = std::vector<std::uint8_t>(WINDOW_SIZE);
    std::uint32_t window_posn{};
    std::uint32_t r0{1}, r1{1}, r2{1};
    bool header_read{};
    int block_type{};
    int block_remaining{};
    std::uint32_t frames_read{};
    std::uint32_t intel_filesize{};
    std::uint32_t intel_curpos{};
    bool intel_started{};
    std::vector<int> main_lengths = std::vector<int>(MAIN_ELEMENTS);
    std::vector<int> length_lengths = std::vector<int>(250);
    std::vector<int> aligned_lengths = std::vector<int>(8);
    HuffmanTable main_table = build_huffman(main_lengths, 12);
    HuffmanTable length_table = build_huffman(length_lengths, 12);
    HuffmanTable aligned_table = build_huffman(aligned_lengths, 7);

    std::vector<std::uint8_t> process(const std::uint8_t* src, std::size_t src_size, std::size_t outlen) {
        if (outlen == 0 || outlen > 0x8000) throw std::runtime_error("invalid XMem output block");
        std::vector<std::uint8_t> padded(src, src + src_size);
        padded.resize(src_size + 4u, 0);
        BitReader br{padded.data(), padded.size(), 0, 0, 0};
        auto wp = window_posn; auto rr0=r0, rr1=r1, rr2=r2;
        if (!header_read) {
            bool has_intel = br.read(1) != 0;
            std::uint32_t i=0,j=0; if (has_intel) { i=br.read(16); j=br.read(16); }
            intel_filesize = (i<<16) | j; header_read = true;
        }
        std::size_t togo = outlen;
        while (togo) {
            if (block_remaining == 0) {
                if (block_type == 3) br.align16();
                block_type = int(br.read(3));
                int i=int(br.read(16)); int j=int(br.read(8));
                block_remaining = (i<<8)|j;
                if (!block_remaining) throw std::runtime_error("zero-length LZX block");
                if (block_type == 2) { for (auto &x:aligned_lengths) x=int(br.read(3)); aligned_table=build_huffman(aligned_lengths,7); }
                if (block_type==1 || block_type==2) {
                    read_code_lengths(br, main_lengths, 0, 256);
                    read_code_lengths(br, main_lengths, 256, MAIN_ELEMENTS);
                    main_table=build_huffman(main_lengths,12);
                    if (main_lengths[0xE8] != 0) intel_started=true;
                    read_code_lengths(br, length_lengths, 0, LZX_NUM_SECONDARY_LENGTHS);
                    length_table=build_huffman(length_lengths,12);
                } else if (block_type==3) {
                    intel_started=true; br.align16(); rr0=br.read_u32le(); rr1=br.read_u32le(); rr2=br.read_u32le();
                } else throw std::runtime_error("illegal LZX block type");
            }
            std::size_t this_run=std::min<std::size_t>(std::size_t(block_remaining),togo); togo-=this_run; block_remaining-=int(this_run);
            wp &= WINDOW_SIZE-1; if (wp+this_run>WINDOW_SIZE) throw std::runtime_error("LZX run crosses window");
            if (block_type==3) { if (br.pos+this_run>br.size) throw std::runtime_error("LZX raw block exceeds input"); std::memcpy(window.data()+wp, br.data+br.pos,this_run); br.pos+=this_run; wp+=std::uint32_t(this_run); continue; }
            std::ptrdiff_t run_left = static_cast<std::ptrdiff_t>(this_run);
            while (run_left > 0) {
                int main_element=huff_decode(br,main_table);
                if (main_element<LZX_NUM_CHARS) { window[wp++]=std::uint8_t(main_element); --run_left; continue; }
                main_element-=LZX_NUM_CHARS;
                int match_length=main_element & LZX_NUM_PRIMARY_LENGTHS;
                if (match_length==LZX_NUM_PRIMARY_LENGTHS) match_length+=huff_decode(br,length_table);
                match_length+=LZX_MIN_MATCH;
                int match_offset=main_element>>3;
                if (match_offset>2) {
                    int extra=EXTRA_BITS[match_offset];
                    if (block_type==1) {
                        if (match_offset!=3) match_offset=POSITION_BASE[match_offset]-2+int(br.read(extra)); else match_offset=1;
                    } else {
                        match_offset=POSITION_BASE[match_offset]-2;
                        if (extra>3) { extra-=3; match_offset += int(br.read(extra))<<3; match_offset += huff_decode(br,aligned_table); }
                        else if (extra==3) match_offset += huff_decode(br,aligned_table);
                        else if (extra>0) match_offset += int(br.read(extra));
                        else match_offset=1;
                    }
                    rr2=rr1; rr1=rr0; rr0=std::uint32_t(match_offset);
                } else if (match_offset==0) match_offset=int(rr0);
                else if (match_offset==1) { match_offset=int(rr1); rr1=rr0; rr0=std::uint32_t(match_offset); }
                else { match_offset=int(rr2); rr2=rr0; rr0=std::uint32_t(match_offset); }
                std::size_t dest=wp; long long srcpos=static_cast<long long>(wp)-match_offset; wp += std::uint32_t(match_length); if (wp>WINDOW_SIZE) throw std::runtime_error("LZX match crosses window"); this_run -= std::size_t(match_length);
                run_left -= static_cast<std::ptrdiff_t>(match_length);
                int remain=match_length;
                while (srcpos<0 && remain>0) { window[dest]=window[std::size_t(srcpos)+WINDOW_SIZE]; ++dest; ++srcpos; --remain; }
                while (remain>0) { window[dest]=window[std::size_t(srcpos)]; ++dest; ++srcpos; --remain; }
            }
        }
        std::size_t end=wp==0?WINDOW_SIZE:wp; std::size_t start=end-outlen; if (start>end) throw std::runtime_error("LZX window underflow");
        std::vector<std::uint8_t> out(outlen); std::memcpy(out.data(),window.data()+start,outlen);
        window_posn=wp; r0=rr0;r1=rr1;r2=rr2; ++frames_read;
        if (frames_read<32768 && intel_filesize) {
            if (outlen<=6 || !intel_started) intel_curpos += std::uint32_t(outlen);
            else {
                std::size_t data_end=outlen>10?outlen-10:0; std::uint32_t curpos=intel_curpos;
                std::size_t p=0; while (p<data_end) {
                    if (out[p]!=0xE8) { ++p; ++curpos; continue; }
                    std::int32_t abs_off=std::int32_t(std::uint32_t(out[p+1]) | (std::uint32_t(out[p+2])<<8) | (std::uint32_t(out[p+3])<<16) | (std::uint32_t(out[p+4])<<24));
                    if (-std::int64_t(curpos)<=abs_off && std::uint32_t(abs_off)<intel_filesize) {
                        std::int64_t rel=(abs_off>=0)?std::int64_t(abs_off)-curpos:std::int64_t(abs_off)+intel_filesize;
                        std::uint32_t rv=std::uint32_t(rel); out[p+1]=std::uint8_t(rv);out[p+2]=std::uint8_t(rv>>8);out[p+3]=std::uint8_t(rv>>16);out[p+4]=std::uint8_t(rv>>24);
                    }
                    p+=5;curpos+=5;
                }
                intel_curpos += std::uint32_t(outlen);
            }
        }
        return out;
    }
};

int run(const std::uint8_t* src,std::size_t src_size,std::uint8_t* dst,std::size_t cap,std::size_t expected) {
    if (!src || !dst || expected>cap) return 1;
    try {
        LZXState state; std::size_t pos=0,outpos=0;
        while(pos<src_size && outpos<expected){
            std::uint8_t high=src[pos++]; std::size_t dst_size,src_len; std::size_t suffix=0;
            if(high==0xFF){ if(pos+4>src_size) throw std::runtime_error("XMem header"); dst_size=(std::size_t(src[pos])<<8)|src[pos+1]; src_len=(std::size_t(src[pos+2])<<8)|src[pos+3]; pos+=4; suffix=5; }
            else { if(pos>=src_size) throw std::runtime_error("XMem header"); dst_size=0x8000; src_len=(std::size_t(high)<<8)|src[pos++]; }
            if(!dst_size||!src_len||pos+src_len>src_size) throw std::runtime_error("XMem block bounds");
            auto block=state.process(src+pos,src_len,dst_size);
            pos+=src_len;
            if(outpos+block.size()>expected) throw std::runtime_error("XMem output overflow");
            std::memcpy(dst+outpos,block.data(),block.size()); outpos+=block.size();
            if(suffix){ if(pos+suffix>src_size) throw std::runtime_error("XMem suffix"); pos+=suffix; }
        }
        return outpos==expected?0:2;
    } catch (...) { return 3; }
}

} // namespace

extern "C" int shift_xmem_decompress(const std::uint8_t* src, std::size_t src_size,
                                     std::uint8_t* dst, std::size_t dst_capacity,
                                     std::size_t expected_size) {
    return run(src,src_size,dst,dst_capacity,expected_size);
}
