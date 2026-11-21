#!/usr/bin/env python3
"""
test_macho_parser.py - Tests for Mach-O Architecture & Slice Parser
Part of Arm32Runner Jailbreak Tweak for Sileo
"""

import os
import struct
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER_EXE = os.path.join(ROOT_DIR, "package", "usr", "bin", "arm32-check.exe")
if not os.path.exists(CHECKER_EXE):
    CHECKER_EXE = os.path.join(ROOT_DIR, "package", "usr", "bin", "arm32-check")

def create_synthetic_armv7_macho(path, encrypted=False):
    """Generates a valid synthetic 32-bit Mach-O binary (ARMv7) with load commands"""
    with open(path, "wb") as f:
        # mach_header (32-bit)
        magic = 0xfeedface      # MH_MAGIC
        cputype = 12            # CPU_TYPE_ARM
        cpusubtype = 9          # CPU_SUBTYPE_ARM_V7
        filetype = 2            # MH_EXECUTE
        ncmds = 2 if not encrypted else 3
        
        # Load commands data
        cmds = bytearray()
        
        # 1. LC_SEGMENT (__TEXT)
        # cmd(4), cmdsize(4), segname(16), vmaddr(4), vmsize(4), fileoff(4), filesize(4), maxprot(4), initprot(4), nsects(4), flags(4)
        seg_name = b"__TEXT\x00".ljust(16, b"\x00")
        lc_segment = struct.pack("<II16sIIIIIIII", 0x1, 56, seg_name, 0x4000, 0x8000, 0, 0x2000, 7, 5, 0, 0)
        cmds.extend(lc_segment)
        
        # 2. LC_LOAD_DYLIB (/System/Library/Frameworks/UIKit.framework/UIKit)
        dylib_path = b"/System/Library/Frameworks/UIKit.framework/UIKit\x00"
        aligned_path_len = (len(dylib_path) + 3) & ~3
        dylib_path_padded = dylib_path.ljust(aligned_path_len, b"\x00")
        cmdsize_dylib = 24 + len(dylib_path_padded)
        lc_dylib = struct.pack("<IIIIII", 0xc, cmdsize_dylib, 24, 0, 0x010000, 0x010000) + dylib_path_padded
        cmds.extend(lc_dylib)
        
        # 3. LC_ENCRYPTION_INFO (optional)
        if encrypted:
            # cmd(4), cmdsize(4), cryptoff(4), cryptsize(4), cryptid(4)
            lc_enc = struct.pack("<IIIII", 0x21, 20, 0x1000, 0x1000, 1)
            cmds.extend(lc_enc)
        
        sizeofcmds = len(cmds)
        flags = 0x00200085
        header = struct.pack("<IIIIIII", magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags)
        
        f.write(header)
        f.write(cmds)
        # Pad to file size
        current = f.tell()
        if current < 0x2000:
            f.write(b"\x00" * (0x2000 - current))

def create_synthetic_fat_macho(path, armv7_path):
    """Creates a Universal Fat binary containing ARMv7 slice"""
    with open(armv7_path, "rb") as f_arm:
        arm_data = f_arm.read()
        
    with open(path, "wb") as f:
        # fat_header: magic(4), nfat_arch(4) (Big Endian)
        magic = 0xcafebabe
        nfat = 1
        f.write(struct.pack(">II", magic, nfat))
        
        # fat_arch: cputype(4), cpusubtype(4), offset(4), size(4), align(4)
        cputype = 12
        cpusubtype = 9
        offset = 4096
        size = len(arm_data)
        align = 12
        f.write(struct.pack(">IIIII", cputype, cpusubtype, offset, size, align))
        
        # Pad to offset
        cur = f.tell()
        f.write(b"\x00" * (offset - cur))
        f.write(arm_data)

def run_tests():
    print("Running Mach-O Architecture Parser Tests...")
    tmp_arm32 = os.path.join(ROOT_DIR, "tests", "sample_armv7.bin")
    tmp_arm32_enc = os.path.join(ROOT_DIR, "tests", "sample_armv7_enc.bin")
    tmp_fat = os.path.join(ROOT_DIR, "tests", "sample_fat.bin")

    create_synthetic_armv7_macho(tmp_arm32, encrypted=False)
    create_synthetic_armv7_macho(tmp_arm32_enc, encrypted=True)
    create_synthetic_fat_macho(tmp_fat, tmp_arm32)

    # Test 1: armv7 clean binary
    res = subprocess.run([CHECKER_EXE, tmp_arm32], capture_output=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"Checker failed on armv7: {res.stderr}"
    assert "ARMv7 Slice:        YES" in res.stdout
    assert "DECRYPTED / CLEAN" in res.stdout
    assert "UIKit.framework" in res.stdout
    print("  [PASS] Single 32-bit ARMv7 Mach-O parsing & UIKit dependency detected")

    # Test 2: armv7 encrypted binary
    res_enc = subprocess.run([CHECKER_EXE, tmp_arm32_enc], capture_output=True, encoding="utf-8", errors="replace")
    assert res_enc.returncode == 0
    assert "ENCRYPTED" in res_enc.stdout
    assert "cryptid: 1" in res_enc.stdout
    print("  [PASS] FairPlay DRM encryption detection verified")

    # Test 3: Fat Universal binary
    res_fat = subprocess.run([CHECKER_EXE, tmp_fat], capture_output=True, encoding="utf-8", errors="replace")
    assert res_fat.returncode == 0
    assert "Universal / Fat Binary" in res_fat.stdout
    assert "ARMv7 Slice:        YES" in res_fat.stdout
    print("  [PASS] Fat / Universal Mach-O archive parsing verified")

    # Cleanup temp test files
    for p in [tmp_arm32, tmp_arm32_enc, tmp_fat]:
        if os.path.exists(p):
            os.remove(p)

    print("All Mach-O Parser Tests Passed Successfully!")

if __name__ == "__main__":
    run_tests()
