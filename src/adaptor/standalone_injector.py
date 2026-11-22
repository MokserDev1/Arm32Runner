#!/usr/bin/env python3
"""
standalone_injector.py - Automated Standalone 32-bit to 64-bit IPA Converter
Part of Arm32Runner

Merges the genuine ARM64 JIT launcher and the original ARM32 guest executable
into a Universal Fat Mach-O binary (ARM64 + ARMv7) and embeds the guest RootFS
and translation frameworks directly into the app bundle.

The resulting IPA is a 100% standalone 64-bit iOS application that installs
directly via TrollStore without CoreTrust errors and launches natively from the Home Screen!
"""

import os
import sys
import zipfile
import plistlib
import shutil
import tempfile
import struct

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_IPA = os.path.join(ROOT_DIR, "dist", "LiveExec32_runtime.ipa")

def extract_arm32_slice(binary_bytes):
    """
    Extracts the ARMv7 (or ARMv6) slice from a 32-bit or Fat Mach-O binary.
    """
    if len(binary_bytes) < 8:
        return binary_bytes

    magic = struct.unpack(">I", binary_bytes[:4])[0]
    
    # Universal / Fat Binary
    if magic == 0xCAFEBABE or magic == 0xBEBAFECA:
        need_swap = (magic == 0xBEBAFECA)
        nfat = struct.unpack(">I", binary_bytes[4:8])[0]
        if need_swap:
            nfat = struct.unpack("<I", binary_bytes[4:8])[0]

        armv7_slice = None
        armv6_slice = None

        for i in range(nfat):
            arch_data = binary_bytes[8 + i*20 : 28 + i*20]
            if len(arch_data) < 20:
                break
            if need_swap:
                cputype, cpusubtype, offset, size, align = struct.unpack("<IIIII", arch_data)
            else:
                cputype, cpusubtype, offset, size, align = struct.unpack(">IIIII", arch_data)

            if cputype == 12: # CPU_TYPE_ARM
                slice_data = binary_bytes[offset : offset + size]
                if cpusubtype == 9: # ARMv7
                    armv7_slice = slice_data
                elif cpusubtype == 6: # ARMv6
                    armv6_slice = slice_data
                elif armv7_slice is None:
                    armv7_slice = slice_data

        if armv7_slice:
            return armv7_slice
        if armv6_slice:
            return armv6_slice

    # Single Mach-O (32-bit little endian)
    magic_le = struct.unpack("<I", binary_bytes[:4])[0]
    if magic_le == 0xFEEDFACE:
        return binary_bytes

    return binary_bytes

def create_fat_macho(arm64_bytes, arm32_bytes):
    """
    Creates a Universal Fat Mach-O containing:
      Slice 0: ARM64 (offset aligned to 16KB)
      Slice 1: ARMv7 (offset aligned to 16KB)
    """
    offset_arm64 = 16384 # 16KB page alignment
    size_arm64 = len(arm64_bytes)

    offset_arm32 = (offset_arm64 + size_arm64 + 16383) & ~16383
    size_arm32 = len(arm32_bytes)

    # Fat Header
    header = struct.pack(">II", 0xCAFEBABE, 2)
    arch_arm64 = struct.pack(">IIIII", 0x0100000C, 0, offset_arm64, size_arm64, 14)
    arch_arm32 = struct.pack(">IIIII", 12, 9, offset_arm32, size_arm32, 14)

    total_size = offset_arm32 + size_arm32
    fat_bin = bytearray(total_size)
    fat_bin[0:8] = header
    fat_bin[8:28] = arch_arm64
    fat_bin[28:48] = arch_arm32
    fat_bin[offset_arm64 : offset_arm64 + size_arm64] = arm64_bytes
    fat_bin[offset_arm32 : offset_arm32 + size_arm32] = arm32_bytes

    return bytes(fat_bin)

def convert_to_standalone(input_ipa, output_ipa=None):
    if not os.path.exists(RUNTIME_IPA):
        print(f"Error: Runtime IPA not found at {RUNTIME_IPA}")
        return False

    if not output_ipa:
        base, ext = os.path.splitext(input_ipa)
        output_ipa = f"{base}_standalone_arm64{ext}"

    print(f"===========================================================")
    print(f"  Arm32Runner Universal Fat Standalone Converter           ")
    print(f"  Input IPA:  {os.path.basename(input_ipa)}                ")
    print(f"  Output IPA: {os.path.basename(output_ipa)}               ")
    print(f"===========================================================\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        game_extract = os.path.join(tmp_dir, "game")
        runtime_extract = os.path.join(tmp_dir, "runtime")

        print("[1/5] Extracting 32-bit game archive...")
        with zipfile.ZipFile(input_ipa, "r") as z_game:
            z_game.extractall(game_extract)

        payload_dir = os.path.join(game_extract, "Payload")
        if not os.path.exists(payload_dir):
            print("Error: IPA missing Payload directory")
            return False

        app_dirs = [d for d in os.listdir(payload_dir) if d.endswith(".app")]
        if not app_dirs:
            print("Error: No .app found inside Payload")
            return False

        game_app = os.path.join(payload_dir, app_dirs[0])
        plist_path = os.path.join(game_app, "Info.plist")
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)

        orig_exec = plist.get("CFBundleExecutable")
        print(f"  Detected Game Executable: {orig_exec}")

        orig_bin_path = os.path.join(game_app, orig_exec)
        if not os.path.exists(orig_bin_path):
            print(f"Error: Original executable {orig_bin_path} not found")
            return False

        with open(orig_bin_path, "rb") as f:
            orig_bin_bytes = f.read()

        arm32_slice = extract_arm32_slice(orig_bin_bytes)
        print(f"  Extracted ARM32 slice: {len(arm32_slice)} bytes")

        print("[2/5] Extracting ARM64 launcher and guest RootFS from runtime...")
        with zipfile.ZipFile(RUNTIME_IPA, "r") as z_run:
            z_run.extractall(runtime_extract)

        run_payload = os.path.join(runtime_extract, "Payload")
        run_app = os.path.join(run_payload, [d for d in os.listdir(run_payload) if d.endswith(".app")][0])

        run_bin = os.path.join(run_app, "LiveExec32")
        with open(run_bin, "rb") as f:
            arm64_slice = f.read()
        print(f"  Extracted ARM64 launcher slice: {len(arm64_slice)} bytes")

        print("[3/5] Building Universal Fat Mach-O binary (ARM64 + ARMv7)...")
        fat_binary = create_fat_macho(arm64_slice, arm32_slice)
        with open(orig_bin_path, "wb") as f:
            f.write(fat_binary)
        os.chmod(orig_bin_path, 0o755)
        print(f"  Wrote Universal Fat binary: {len(fat_binary)} bytes to {orig_exec}")

        print("[4/5] Injecting guest RootFS and 64-bit translation frameworks...")
        # Inject Frameworks
        run_frameworks = os.path.join(run_app, "Frameworks")
        game_frameworks = os.path.join(game_app, "Frameworks")
        os.makedirs(game_frameworks, exist_ok=True)
        if os.path.exists(run_frameworks):
            for item in os.listdir(run_frameworks):
                s = os.path.join(run_frameworks, item)
                d = os.path.join(game_frameworks, item)
                if not os.path.exists(d):
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            print("  Injected 64-bit translation frameworks")

        # Inject RootFS
        run_rootfs = os.path.join(run_app, "RootFS")
        game_rootfs = os.path.join(game_app, "RootFS")
        if os.path.exists(run_rootfs) and not os.path.exists(game_rootfs):
            shutil.copytree(run_rootfs, game_rootfs)
            print("  Injected guest RootFS and dyld emulation libraries")

        # Update Info.plist
        plist["CFBundleSupportedPlatforms"] = ["iPhoneOS"]
        plist["UIDeviceFamily"] = [1, 2] # iPhone & iPad
        if "UIRequiredDeviceCapabilities" in plist:
            req = plist["UIRequiredDeviceCapabilities"]
            if isinstance(req, list):
                plist["UIRequiredDeviceCapabilities"] = [c for c in req if c not in ["armv7", "armv6"]]
                if "arm64" not in plist["UIRequiredDeviceCapabilities"]:
                    plist["UIRequiredDeviceCapabilities"].append("arm64")
            elif isinstance(req, dict):
                req.pop("armv7", None)
                req.pop("armv6", None)
                req["arm64"] = True

        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        print("  Updated Info.plist (marked as arm64 compatible)")

        # Strip old signatures so TrollStore applies CoreTrust bypass cleanly
        sig_dir = os.path.join(game_app, "_CodeSignature")
        if os.path.exists(sig_dir):
            shutil.rmtree(sig_dir)

        print("[5/5] Re-packaging into standalone 64-bit IPA...")
        with zipfile.ZipFile(output_ipa, "w", zipfile.ZIP_DEFLATED) as z_out:
            for root, _, files in os.walk(game_extract):
                for file in files:
                    full = os.path.join(root, file)
                    rel = os.path.relpath(full, game_extract)
                    z_out.write(full, rel)

    out_size_mb = os.path.getsize(output_ipa) / (1024.0 * 1024.0)
    print(f"\n===========================================================")
    print(f"  SUCCESS! Created Standalone 64-bit IPA:                 ")
    print(f"  {output_ipa} ({out_size_mb:.2f} MB)")
    print(f"===========================================================\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python standalone_injector.py <path_to_game.ipa> [output.ipa]")
        sys.exit(1)
    in_ipa = sys.argv[1]
    out_ipa = sys.argv[2] if len(sys.argv) > 2 else None
    ok = convert_to_standalone(in_ipa, out_ipa)
    sys.exit(0 if ok else 1)
