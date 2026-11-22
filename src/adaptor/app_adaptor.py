#!/usr/bin/env python3
"""
app_adaptor.py - Automatic 32-bit to 64-bit IPA Adapter
Part of Arm32Runner Jailbreak Tweak for Sileo

Converts pure 32-bit legacy IPAs into modern 64-bit executable bundles
that can launch directly from iOS SpringBoard without kernel 'Bad CPU type' crashes.
"""

import os
import sys
import zipfile
import plistlib
import shutil
import tempfile
import struct

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_arm64_launcher_stub(app_name):
    """
    Uses the genuine compiled ARM64 Mach-O executable as CFBundleExecutable.
    This binary has valid Mach-O segments, sections, and Linkedit that satisfy
    TrollStore's CoreTrust bypass (ChOma / ldid), preventing error 185.
    """
    stub_path = os.path.join(ROOT_DIR, "package", "Applications", "Arm32Runner.app", "Arm32Runner")
    if os.path.exists(stub_path):
        with open(stub_path, "rb") as f:
            return f.read()
            
    # Fallback minimal header
    magic = 0xfeedfacf       # MH_MAGIC_64
    cputype = 0x0100000c     # CPU_TYPE_ARM64
    cpusubtype = 0           # CPU_SUBTYPE_ARM64_ALL
    filetype = 0x2           # MH_EXECUTE
    ncmds = 2
    pz_name = b"__PAGEZERO\x00".ljust(16, b"\x00")
    lc_pagezero = struct.pack("<II16sQQQQIIII", 0x19, 72, pz_name, 0, 0x100000000, 0, 0, 0, 0, 0, 0)
    text_name = b"__TEXT\x00".ljust(16, b"\x00")
    lc_text = struct.pack("<II16sQQQQIIII", 0x19, 72, text_name, 0x100000000, 0x4000, 0, 0x1000, 7, 5, 0, 0)
    sizeofcmds = len(lc_pagezero) + len(lc_text)
    flags = 0x00200085
    header = struct.pack("<IIIIIIII", magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, 0)
    code = b"\xc0\x03\x5f\xd6" * 64
    payload = (header + lc_pagezero + lc_text).ljust(0x1000, b"\x00") + code
    return payload

def adapt_app_bundle(app_dir):
    """Adapts an unzipped .app bundle in-place to 64-bit architecture"""
    plist_path = os.path.join(app_dir, "Info.plist")
    if not os.path.exists(plist_path):
        print(f"Error: Info.plist not found in {app_dir}")
        return False

    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)

    exec_name = plist.get("CFBundleExecutable")
    if not exec_name:
        print("Error: CFBundleExecutable not found in Info.plist")
        return False

    orig_exec_path = os.path.join(app_dir, exec_name)
    if not os.path.exists(orig_exec_path):
        print(f"Error: Executable {orig_exec_path} does not exist")
        return False

    # Check if executable is 32-bit
    with open(orig_exec_path, "rb") as f:
        magic = struct.unpack("<I", f.read(4))[0]
    
    is_32 = (magic == 0xfeedface or magic == 0xcefaedfe)
    print(f"Analyzing {exec_name}: Magic = 0x{magic:08X} ({'32-bit ARM' if is_32 else 'Other/Fat'})")

    # 1. Rename original 32-bit binary to payload
    payload_name = f"{exec_name}.arm32"
    payload_path = os.path.join(app_dir, payload_name)
    if not os.path.exists(payload_path):
        shutil.move(orig_exec_path, payload_path)
        print(f"  Preserved 32-bit payload as: {payload_name}")

    # 2. Generate and write 64-bit launcher stub
    stub_data = generate_arm64_launcher_stub(exec_name)
    with open(orig_exec_path, "wb") as f:
        f.write(stub_data)
    os.chmod(orig_exec_path, 0o755)
    print(f"  Injected native 64-bit launcher stub: {orig_exec_path}")

    # 3. Modify Info.plist to satisfy iOS 15/16 installd and SpringBoard
    plist["CFBundleSupportedPlatforms"] = ["iPhoneOS"]
    plist["UIDeviceFamily"] = [1, 2] # iPhone & iPad
    if "UIRequiredDeviceCapabilities" in plist:
        # Remove armv7 hardware requirement
        req = plist["UIRequiredDeviceCapabilities"]
        if isinstance(req, list):
            plist["UIRequiredDeviceCapabilities"] = [c for c in req if c not in ["armv7", "armv6"]]
        elif isinstance(req, dict):
            req.pop("armv7", None)
            req.pop("armv6", None)

    # Add marker for Arm32Runner
    plist["Arm32RunnerCompatible"] = True
    plist["Arm32PayloadBinary"] = payload_name

    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)
    print("  Updated Info.plist for 64-bit SpringBoard registration")

    return True

import os
import sys
from .standalone_injector import convert_to_standalone

def adapt_ipa(input_ipa, output_ipa=None):
    return convert_to_standalone(input_ipa, output_ipa)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python app_adaptor.py <path_to_32bit.ipa> [output_path.ipa]")
        sys.exit(1)
    
    in_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    ok = adapt_ipa(in_file, out_file)
    sys.exit(0 if ok else 1)
