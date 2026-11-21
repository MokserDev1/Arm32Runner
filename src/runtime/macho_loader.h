/**
 * macho_loader.h - Mach-O 32-bit Binary In-Memory Loader
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef MACHO_LOADER_H
#define MACHO_LOADER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../arch_checker/arch_checker.h"

typedef struct {
    uint8_t *virtual_memory; /* Allocated 32-bit execution space */
    size_t memory_size;      /* Total size */
    uint32_t text_vmaddr;
    uint32_t text_vmsize;
    uint32_t data_vmaddr;
    uint32_t data_vmsize;
    uint32_t entry_point;
    uint32_t stack_base;
    uint32_t stack_size;
    bool is_loaded;
    char error_desc[256];
} LoadedAppImage;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Initializes and reserves virtual memory space for the 32-bit application.
 */
bool macho_loader_init(LoadedAppImage *image, size_t reserve_size);

/**
 * Loads a 32-bit Mach-O binary (or slice from a Fat binary) into memory.
 */
bool macho_loader_load(LoadedAppImage *image, const char *binary_path, const MachOAnalysisResult *meta);

/**
 * Frees allocated execution memory.
 */
void macho_loader_destroy(LoadedAppImage *image);

#ifdef __cplusplus
}
#endif

#endif /* MACHO_LOADER_H */
