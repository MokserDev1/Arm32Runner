/**
 * arch_checker.c - Mach-O Architecture & Compatibility Inspector
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include "arch_checker.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <winsock2.h>
#else
#include <arpa/inet.h>
#endif

static uint32_t swap_uint32(uint32_t val) {
    return ((val >> 24) & 0xff) |
           ((val << 8)  & 0xff0000) |
           ((val >> 8)  & 0xff00) |
           ((val << 24) & 0xff000000);
}

typedef struct {
    uint32_t magic;
    uint32_t cputype;
    uint32_t cpusubtype;
    uint32_t filetype;
    uint32_t ncmds;
    uint32_t sizeofcmds;
    uint32_t flags;
} MachHeader32;

typedef struct {
    uint32_t magic;
    uint32_t cputype;
    uint32_t cpusubtype;
    uint32_t filetype;
    uint32_t ncmds;
    uint32_t sizeofcmds;
    uint32_t flags;
    uint32_t reserved;
} MachHeader64;

typedef struct {
    uint32_t magic;
    uint32_t nfat_arch;
} FatHeader;

typedef struct {
    uint32_t cputype;
    uint32_t cpusubtype;
    uint32_t offset;
    uint32_t size;
    uint32_t align;
} FatArch;

typedef struct {
    uint32_t cmd;
    uint32_t cmdsize;
} LoadCommand;

typedef struct {
    uint32_t cmd;
    uint32_t cmdsize;
    uint32_t cryptoff;
    uint32_t cryptsize;
    uint32_t cryptid;
} EncryptionInfoCommand;

typedef struct {
    uint32_t cmd;
    uint32_t cmdsize;
    uint32_t name_offset;
    uint32_t timestamp;
    uint32_t current_version;
    uint32_t compatibility_version;
} DylibCommand;

typedef struct {
    uint32_t cmd;
    uint32_t cmdsize;
    uint64_t entryoff;
    uint64_t stacksize;
} EntryPointCommand;

static bool parse_mach_slice(const uint8_t *buffer, size_t slice_size, MachOAnalysisResult *result, bool is_64) {
    if (slice_size < sizeof(MachHeader32)) {
        snprintf(result->error_message, sizeof(result->error_message), "Slice size too small for Mach-O header");
        return false;
    }

    const MachHeader32 *header32 = (const MachHeader32 *)buffer;
    bool need_swap = (header32->magic == MACHO_CIGAM_32 || header32->magic == MACHO_CIGAM_64);
    uint32_t cputype = need_swap ? swap_uint32(header32->cputype) : header32->cputype;
    uint32_t cpusubtype = need_swap ? swap_uint32(header32->cpusubtype) : header32->cpusubtype;
    uint32_t ncmds = need_swap ? swap_uint32(header32->ncmds) : header32->ncmds;
    uint32_t sizeofcmds = need_swap ? swap_uint32(header32->sizeofcmds) : header32->sizeofcmds;

    if (cputype == CPU_TYPE_ARM) {
        if (cpusubtype == CPU_SUBTYPE_ARM_V7) {
            result->has_armv7 = true;
        } else if (cpusubtype == CPU_SUBTYPE_ARM_V7S) {
            result->has_armv7s = true;
        } else {
            result->has_armv7 = true; // generic armv6 / armv7
        }
    } else if (cputype == CPU_TYPE_ARM64) {
        if ((cpusubtype & 0xff) == CPU_SUBTYPE_ARM64E) {
            result->has_arm64e = true;
        } else {
            result->has_arm64 = true;
        }
    }

    size_t header_size = is_64 ? sizeof(MachHeader64) : sizeof(MachHeader32);
    if (slice_size < header_size + sizeofcmds) {
        snprintf(result->error_message, sizeof(result->error_message), "Commands size exceeds slice bounds");
        return false;
    }

    const uint8_t *cmd_ptr = buffer + header_size;
    for (uint32_t i = 0; i < ncmds; i++) {
        if ((size_t)(cmd_ptr - buffer) + sizeof(LoadCommand) > slice_size) {
            break;
        }

        const LoadCommand *lc = (const LoadCommand *)cmd_ptr;
        uint32_t cmd = need_swap ? swap_uint32(lc->cmd) : lc->cmd;
        uint32_t cmdsize = need_swap ? swap_uint32(lc->cmdsize) : lc->cmdsize;

        if (cmdsize == 0 || (size_t)(cmd_ptr - buffer) + cmdsize > slice_size) {
            break;
        }

        if (cmd == LC_ENCRYPTION_INFO || cmd == LC_ENCRYPTION_INFO_64) {
            if (cmdsize >= sizeof(EncryptionInfoCommand)) {
                const EncryptionInfoCommand *enc = (const EncryptionInfoCommand *)cmd_ptr;
                uint32_t cryptid = need_swap ? swap_uint32(enc->cryptid) : enc->cryptid;
                result->crypt_id = cryptid;
                if (cryptid != 0) {
                    result->is_encrypted = true;
                }
            }
        } else if (cmd == LC_LOAD_DYLIB) {
            if (cmdsize >= sizeof(DylibCommand) && result->dylib_count < 64) {
                const DylibCommand *dylib = (const DylibCommand *)cmd_ptr;
                uint32_t name_offset = need_swap ? swap_uint32(dylib->name_offset) : dylib->name_offset;
                if (name_offset < cmdsize) {
                    const char *dylib_name = (const char *)cmd_ptr + name_offset;
                    strncpy(result->linked_dylibs[result->dylib_count], dylib_name, 255);
                    result->linked_dylibs[result->dylib_count][255] = '\0';
                    result->dylib_count++;
                }
            }
        } else if (cmd == LC_MAIN) {
            if (cmdsize >= sizeof(EntryPointCommand)) {
                const EntryPointCommand *ep = (const EntryPointCommand *)cmd_ptr;
                result->entry_point = (uint32_t)(need_swap ? swap_uint32((uint32_t)ep->entryoff) : (uint32_t)ep->entryoff);
            }
        }

        cmd_ptr += cmdsize;
    }

    return true;
}

bool analyze_macho_buffer(const uint8_t *buffer, size_t size, MachOAnalysisResult *result) {
    if (!buffer || !result || size < 4) {
        if (result) {
            snprintf(result->error_message, sizeof(result->error_message), "Invalid buffer or size < 4");
        }
        return false;
    }

    memset(result, 0, sizeof(MachOAnalysisResult));
    uint32_t magic = *(const uint32_t *)buffer;

    if (magic == FAT_MAGIC_UNIVERSAL || magic == FAT_CIGAM_UNIVERSAL) {
        result->is_fat = true;
        bool need_swap = (magic == FAT_CIGAM_UNIVERSAL);
        if (size < sizeof(FatHeader)) {
            snprintf(result->error_message, sizeof(result->error_message), "Buffer too small for Fat header");
            return false;
        }

        const FatHeader *fat = (const FatHeader *)buffer;
        uint32_t nfat_arch = need_swap ? swap_uint32(fat->nfat_arch) : fat->nfat_arch;

        if (size < sizeof(FatHeader) + nfat_arch * sizeof(FatArch)) {
            snprintf(result->error_message, sizeof(result->error_message), "Buffer too small for Fat architectures");
            return false;
        }

        const FatArch *archs = (const FatArch *)(buffer + sizeof(FatHeader));
        for (uint32_t i = 0; i < nfat_arch; i++) {
            uint32_t cputype = need_swap ? swap_uint32(archs[i].cputype) : archs[i].cputype;
            uint32_t offset = need_swap ? swap_uint32(archs[i].offset) : archs[i].offset;
            uint32_t slice_size = need_swap ? swap_uint32(archs[i].size) : archs[i].size;

            if (offset + slice_size > size) {
                continue;
            }

            if (cputype == CPU_TYPE_ARM) {
                result->arm32_offset = offset;
                result->arm32_size = slice_size;
                parse_mach_slice(buffer + offset, slice_size, result, false);
            } else if (cputype == CPU_TYPE_ARM64) {
                parse_mach_slice(buffer + offset, slice_size, result, true);
            }
        }
        return true;
    } else if (magic == MACHO_MAGIC_32 || magic == MACHO_CIGAM_32) {
        result->is_fat = false;
        result->arm32_offset = 0;
        result->arm32_size = (uint32_t)size;
        return parse_mach_slice(buffer, size, result, false);
    } else if (magic == MACHO_MAGIC_64 || magic == MACHO_CIGAM_64) {
        result->is_fat = false;
        return parse_mach_slice(buffer, size, result, true);
    }

    snprintf(result->error_message, sizeof(result->error_message), "Unknown magic header: 0x%08X", magic);
    return false;
}

bool analyze_macho_file(const char *filepath, MachOAnalysisResult *result) {
    if (!filepath || !result) return false;

    FILE *f = fopen(filepath, "rb");
    if (!f) {
        snprintf(result->error_message, sizeof(result->error_message), "Cannot open file: %s", filepath);
        return false;
    }

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (fsize <= 0 || fsize > 1024 * 1024 * 512) { // Max 512 MB safety limit
        fclose(f);
        snprintf(result->error_message, sizeof(result->error_message), "File too large or empty: %ld bytes", fsize);
        return false;
    }

    uint8_t *buf = (uint8_t *)malloc((size_t)fsize);
    if (!buf) {
        fclose(f);
        snprintf(result->error_message, sizeof(result->error_message), "Memory allocation failure");
        return false;
    }

    size_t read_bytes = fread(buf, 1, (size_t)fsize, f);
    fclose(f);

    if (read_bytes != (size_t)fsize) {
        free(buf);
        snprintf(result->error_message, sizeof(result->error_message), "Failed to read entire file");
        return false;
    }

    bool ok = analyze_macho_buffer(buf, (size_t)fsize, result);
    free(buf);
    return ok;
}

void print_compatibility_report(const MachOAnalysisResult *result) {
    printf("================ Mach-O Compatibility Report ================\n");
    printf("  Binary Format:      %s\n", result->is_fat ? "Universal / Fat Binary" : "Single Architecture");
    printf("  ARMv7 Slice:        %s\n", result->has_armv7 ? "YES" : "NO");
    printf("  ARMv7s Slice:       %s\n", result->has_armv7s ? "YES" : "NO");
    printf("  ARM64 Slice:        %s\n", result->has_arm64 ? "YES" : "NO");
    printf("  ARM64e Slice:       %s\n", result->has_arm64e ? "YES" : "NO");
    printf("  FairPlay DRM:       %s (cryptid: %u)\n", result->is_encrypted ? "ENCRYPTED [Action Required: Decrypt IPA]" : "DECRYPTED / CLEAN", result->crypt_id);
    if (result->has_armv7 || result->has_armv7s) {
        printf("  32-bit Slice Size:  %u bytes (offset: 0x%X)\n", result->arm32_size, result->arm32_offset);
        printf("  Entry Point Offset: 0x%X\n", result->entry_point);
    }
    printf("  Linked Frameworks (%u):\n", result->dylib_count);
    for (uint32_t i = 0; i < result->dylib_count; i++) {
        printf("    [%02u] %s\n", i + 1, result->linked_dylibs[i]);
    }
    printf("-------------------------------------------------------------\n");
    if (result->is_encrypted) {
        printf("  [VERDICT] Binary has FairPlay DRM. Decrypt with Clutch/bfdecrypt before launching.\n");
    } else if (result->has_arm64 || result->has_arm64e) {
        printf("  [VERDICT] Binary has native 64-bit slice! Will launch directly via iOS native dyld.\n");
    } else if (result->has_armv7 || result->has_armv7s) {
        printf("  [VERDICT] Pure 32-bit (ARMv7/s). Will execute via Arm32Runner Bridge on iOS 12-16.\n");
    } else {
        printf("  [VERDICT] Incompatible binary: No ARMv7 or ARM64 slices found.\n");
    }
    printf("=============================================================\n");
}
