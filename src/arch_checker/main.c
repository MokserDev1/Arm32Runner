/**
 * main.c - arm32-check CLI Tool for iOS Terminal & Diagnostic Inspection
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include <stdio.h>
#include <stdlib.h>
#include "arch_checker.h"

int main(int argc, char *argv[]) {
    printf("Arm32Runner: Mach-O Architecture & Compatibility Checker v1.0.0\n");
    printf("Designed for Sileo Jailbreak Environments (iOS 12 - 16)\n\n");

    if (argc < 2) {
        printf("Usage: %s <path_to_binary_or_app_executable>\n", argv[0]);
        printf("Example: %s /Applications/ClassicGame.app/ClassicGame\n", argv[0]);
        return 1;
    }

    const char *target = argv[1];
    printf("Analyzing: %s\n\n", target);

    MachOAnalysisResult result;
    if (!analyze_macho_file(target, &result)) {
        fprintf(stderr, "Error analyzing binary: %s\n", result.error_message);
        return 2;
    }

    print_compatibility_report(&result);
    return 0;
}
