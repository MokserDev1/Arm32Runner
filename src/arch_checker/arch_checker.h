/**
 * arch_checker.h - Mach-O Architecture & Compatibility Inspector
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef ARCH_CHECKER_H
#define ARCH_CHECKER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define MACHO_MAGIC_32       0xfeedface
#define MACHO_CIGAM_32       0xcefaedfe
#define MACHO_MAGIC_64       0xfeedfacf
#define MACHO_CIGAM_64       0xcffaedfe
#define FAT_MAGIC_UNIVERSAL  0xcafebabe
#define FAT_CIGAM_UNIVERSAL  0xbebafeca

#define CPU_TYPE_ARM         12
#define CPU_TYPE_ARM64       0x0100000c

#define CPU_SUBTYPE_ARM_ALL  0
#define CPU_SUBTYPE_ARM_V6   6
#define CPU_SUBTYPE_ARM_V7   9
#define CPU_SUBTYPE_ARM_V7S  11
#define CPU_SUBTYPE_ARM_V7K  12
#define CPU_SUBTYPE_ARM64_ALL 0
#define CPU_SUBTYPE_ARM64_V8 1
#define CPU_SUBTYPE_ARM64E   2

#define LC_SEGMENT_32        0x00000001
#define LC_SYMTAB            0x00000002
#define LC_DYSYMTAB          0x0000000b
#define LC_LOAD_DYLIB        0x0000000c
#define LC_ID_DYLIB          0x0000000d
#define LC_SEGMENT_64        0x00000019
#define LC_ENCRYPTION_INFO   0x00000021
#define LC_MAIN              0x80000028
#define LC_ENCRYPTION_INFO_64 0x0000002c

typedef struct {
    bool has_armv7;
    bool has_armv7s;
    bool has_arm64;
    bool has_arm64e;
    bool is_fat;
    bool is_encrypted; // FairPlay DRM flag
    uint32_t crypt_id;
    uint32_t arm32_offset;
    uint32_t arm32_size;
    uint32_t entry_point;
    char linked_dylibs[64][256];
    uint32_t dylib_count;
    char error_message[256];
} MachOAnalysisResult;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Parses and analyzes a Mach-O file from disk.
 * Returns true if parsing succeeded, false if invalid format or file unreadable.
 */
bool analyze_macho_file(const char *filepath, MachOAnalysisResult *result);

/**
 * Parses and analyzes a Mach-O buffer from memory.
 */
bool analyze_macho_buffer(const uint8_t *buffer, size_t size, MachOAnalysisResult *result);

/**
 * Checks if the hardware/system can run the parsed binary.
 * Explains requirements and compatibility verdict.
 */
void print_compatibility_report(const MachOAnalysisResult *result);

#ifdef __cplusplus
}
#endif

#endif /* ARCH_CHECKER_H */
