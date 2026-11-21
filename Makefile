# Theos Makefile for Arm32Runner
TARGET := iphone:clang:latest:12.0
INSTALL_TARGET_PROCESSES := SpringBoard installd

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = Arm32Runner

Arm32Runner_FILES = \
    src/tweak/Tweak.x \
    src/tweak/installd_hook.x \
    src/tweak/springboard_hook.x \
    src/arch_checker/arch_checker.c \
    src/syscall_bridge/syscall_bridge.c \
    src/runtime/macho_loader.c \
    src/runtime/arm32_core.c \
    src/runtime/ui_bridge.c

Arm32Runner_CFLAGS = -fobjc-arc -Isrc/arch_checker -Isrc/syscall_bridge -Isrc/runtime
Arm32Runner_FRAMEWORKS = UIKit Foundation CoreGraphics

include $(THEOS_MAKE_PATH)/tweak.mk

TOOL_NAME = arm32-check
arm32_check_FILES = src/arch_checker/main.c src/arch_checker/arch_checker.c
arm32_check_CFLAGS = -Isrc/arch_checker
arm32_check_INSTALL_PATH = /usr/bin

include $(THEOS_MAKE_PATH)/tool.mk
