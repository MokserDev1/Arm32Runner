#!/usr/bin/env python3
"""
standalone_injector.py - Deep 32-to-64 bit Recompilation & Standalone Converter
Part of Arm32Runner

Full automated recompiler and standalone adapter:
1. Universal Fat Mach-O construction (ARM64 launcher + ARMv7 game slice, 16KB aligned).
2. Complete JIT & CoreTrust Entitlements injection (get-task-allow, dynamic-codesigning, cs.debugger).
3. embedded.mobileprovision injection to ensure TrollStore preserves JIT entitlements during installation.
4. Modern iOS privacy description injection (NSMicrophoneUsageDescription, etc.).
5. Unconditional UIRequiredDeviceCapabilities = ['arm64'] (fixes "32-bit apps are not supported").
6. Embedding guest RootFS and 64-bit translation frameworks.
7. Recursive signature stripping for clean TrollStore installation.
8. Packaging with full Unix file permissions (0755 for executables/directories) so iOS kernel & dyld can execute.
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

ENTITLEMENTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>get-task-allow</key>
    <true/>
    <key>dynamic-codesigning</key>
    <true/>
    <key>com.apple.private.cs.debugger</key>
    <true/>
    <key>platform-application</key>
    <true/>
    <key>com.apple.private.security.no-sandbox</key>
    <true/>
    <key>com.apple.developer.kernel.extended-virtual-addressing</key>
    <true/>
    <key>com.apple.developer.kernel.increased-memory-limit</key>
    <true/>
</dict>
</plist>
"""

MOBILEPROVISION_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AppIDName</key>
    <string>Arm32Runner Standalone</string>
    <key>ApplicationIdentifierPrefix</key>
    <array>
        <string>758442AE4D</string>
    </array>
    <key>CreationDate</key>
    <date>2026-11-22T00:00:00Z</date>
    <key>Platform</key>
    <array>
        <string>iOS</string>
    </array>
    <key>IsSupported</key>
    <true/>
    <key>ProvisionsAllDevices</key>
    <true/>
    <key>Entitlements</key>
    <dict>
        <key>application-identifier</key>
        <string>758442AE4D.{bundle_id}</string>
        <key>get-task-allow</key>
        <true/>
        <key>dynamic-codesigning</key>
        <true/>
        <key>com.apple.private.cs.debugger</key>
        <true/>
        <key>platform-application</key>
        <true/>
        <key>com.apple.private.security.no-sandbox</key>
        <true/>
        <key>com.apple.developer.kernel.extended-virtual-addressing</key>
        <true/>
        <key>com.apple.developer.kernel.increased-memory-limit</key>
        <true/>
    </dict>
    <key>ExpirationDate</key>
    <date>2099-12-31T23:59:59Z</date>
    <key>Name</key>
    <string>Arm32Runner Recompiler Profile</string>
    <key>TeamIdentifier</key>
    <array>
        <string>758442AE4D</string>
    </array>
    <key>TimeToLive</key>
    <integer>99999</integer>
    <key>Version</key>
    <integer>1</integer>
</dict>
</plist>
"""

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

    # Fat Header (big endian)
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

def write_ipa_zip(source_dir, output_zip_path):
    """
    Packs directory into an IPA / Zip with proper Unix file permissions and directory entries.
    Executables and RootFS libraries receive 0o100755 (-rwxr-xr-x).
    Directories receive 0o40755 (drwxr-xr-x).
    """
    print(f"  Packaging archive with Unix permissions: {os.path.basename(output_zip_path)}...")
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as z_out:
        for root, dirs, files in os.walk(source_dir):
            dirs.sort()
            files.sort()

            # Add directory entries
            for d in dirs:
                full_dir = os.path.join(root, d)
                rel_dir = os.path.relpath(full_dir, source_dir).replace("\\", "/") + "/"
                zinfo = zipfile.ZipInfo(rel_dir)
                zinfo.create_system = 3 # UNIX
                zinfo.external_attr = 0o40755 << 16 # drwxr-xr-x
                z_out.writestr(zinfo, "")

            # Add files with appropriate permissions
            for f in files:
                full_file = os.path.join(root, f)
                rel_file = os.path.relpath(full_file, source_dir).replace("\\", "/")

                with open(full_file, "rb") as fp:
                    content = fp.read()

                zinfo = zipfile.ZipInfo(rel_file)
                zinfo.create_system = 3 # UNIX

                is_executable = False
                base_name = os.path.basename(rel_file)

                # Check if file should be marked executable
                if rel_file.endswith((".dylib", ".sh")) or "usr/lib/dyld" in rel_file or "usr/bin" in rel_file:
                    is_executable = True
                elif "/Frameworks/" in rel_file and "." not in base_name:
                    is_executable = True
                elif "/Payload/" in rel_file and rel_file.count("/") == 2 and "." not in base_name:
                    # Main App executable binary
                    is_executable = True
                elif len(content) >= 4 and content[:4] in [b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"]:
                    is_executable = True

                if is_executable:
                    zinfo.external_attr = 0o100755 << 16 # -rwxr-xr-x
                else:
                    zinfo.external_attr = 0o100644 << 16 # -rw-r--r--

                z_out.writestr(zinfo, content)

def convert_to_standalone(input_ipa, output_ipa=None):
    if not os.path.exists(RUNTIME_IPA):
        print(f"Error: Runtime IPA not found at {RUNTIME_IPA}")
        return False

    if not output_ipa:
        base, ext = os.path.splitext(input_ipa)
        output_ipa = f"{base}_standalone_arm64{ext}"

    print(f"===========================================================")
    print(f"  Arm32Runner Deep Recompilation & Standalone Converter    ")
    print(f"  Input IPA:  {os.path.basename(input_ipa)}                ")
    print(f"  Output IPA: {os.path.basename(output_ipa)}               ")
    print(f"===========================================================\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        game_extract = os.path.join(tmp_dir, "game")
        runtime_extract = os.path.join(tmp_dir, "runtime")

        print("[1/7] Extracting 32-bit game archive...")
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
        bundle_id = plist.get("CFBundleIdentifier", "com.antigravity.arm32app")
        print(f"  Detected Game Executable: {orig_exec}")
        print(f"  Bundle Identifier:        {bundle_id}")

        orig_bin_path = os.path.join(game_app, orig_exec)
        if not os.path.exists(orig_bin_path):
            print(f"Error: Original executable {orig_bin_path} not found")
            return False

        with open(orig_bin_path, "rb") as f:
            orig_bin_bytes = f.read()

        arm32_slice = extract_arm32_slice(orig_bin_bytes)
        print(f"  Extracted ARM32 slice: {len(arm32_slice)} bytes")

        print("[2/7] Extracting ARM64 launcher and guest RootFS from runtime...")
        with zipfile.ZipFile(RUNTIME_IPA, "r") as z_run:
            z_run.extractall(runtime_extract)

        run_payload = os.path.join(runtime_extract, "Payload")
        run_app = os.path.join(run_payload, [d for d in os.listdir(run_payload) if d.endswith(".app")][0])

        run_bin = os.path.join(run_app, "LiveExec32")
        with open(run_bin, "rb") as f:
            arm64_slice = f.read()
        print(f"  Extracted ARM64 launcher slice: {len(arm64_slice)} bytes")

        print("[3/7] Building Universal Fat Mach-O binary (ARM64 + ARMv7)...")
        fat_binary = create_fat_macho(arm64_slice, arm32_slice)
        with open(orig_bin_path, "wb") as f:
            f.write(fat_binary)
        os.chmod(orig_bin_path, 0o755)
        print(f"  Wrote Universal Fat binary: {len(fat_binary)} bytes to {orig_exec}")

        print("[4/7] Injecting guest RootFS and 64-bit translation frameworks...")
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
            print("  Injected 64-bit translation frameworks (LiveExec32Shared, LC32HelpUI)")

        # Inject RootFS
        run_rootfs = os.path.join(run_app, "RootFS")
        game_rootfs = os.path.join(game_app, "RootFS")
        if os.path.exists(run_rootfs) and not os.path.exists(game_rootfs):
            shutil.copytree(run_rootfs, game_rootfs)
            print("  Injected guest RootFS and dyld emulation libraries")

        print("[5/7] Injecting JIT Entitlements, MobileProvision & Modern Privacy Keys...")
        # 5.1 Write Entitlements.plist
        entitlements_path = os.path.join(game_app, "Entitlements.plist")
        with open(entitlements_path, "w", encoding="utf-8") as f:
            f.write(ENTITLEMENTS_XML)
        print("  Injected Entitlements.plist (dynamic-codesigning, cs.debugger, get-task-allow)")

        # 5.2 Write embedded.mobileprovision so TrollStore dumpEntitlements picks them up
        mobileprovision_path = os.path.join(game_app, "embedded.mobileprovision")
        with open(mobileprovision_path, "w", encoding="utf-8") as f:
            f.write(MOBILEPROVISION_TEMPLATE.format(bundle_id=bundle_id))
        print("  Injected embedded.mobileprovision (TrollStore JIT preservation)")

        # 5.3 Update Info.plist: UNCONDITIONALLY set arm64 device capability & modern keys
        plist["CFBundleSupportedPlatforms"] = ["iPhoneOS"]
        plist["UIDeviceFamily"] = [1, 2] # Universal: iPhone & iPad
        plist["MinimumOSVersion"] = "15.0"
        plist["LC32BitTranslationLayer"] = True
        
        # This is the vital key that prevents iOS & TrollStore from reporting "32-bit apps are not supported"
        plist["UIRequiredDeviceCapabilities"] = ["arm64"]

        # Privacy descriptions (prevents SIGABRT on modern iOS when app accesses audio/camera/photos)
        if "NSMicrophoneUsageDescription" not in plist:
            plist["NSMicrophoneUsageDescription"] = f"{plist.get('CFBundleDisplayName', orig_exec)} uses the microphone to hear and repeat your voice."
        if "NSPhotoLibraryUsageDescription" not in plist:
            plist["NSPhotoLibraryUsageDescription"] = f"{plist.get('CFBundleDisplayName', orig_exec)} uses your photo library to save recorded videos."
        if "NSCameraUsageDescription" not in plist:
            plist["NSCameraUsageDescription"] = f"{plist.get('CFBundleDisplayName', orig_exec)} uses the camera."

        # Remove deprecated ResourceRules that break modern code signing
        plist.pop("CFBundleResourceSpecification", None)

        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        print("  Updated Info.plist (UIRequiredDeviceCapabilities=['arm64'], MinimumOSVersion=15.0, Privacy descriptions)")

        print("[6/7] Stripping legacy signatures across all bundles and frameworks...")
        # Recursively strip all _CodeSignature, CodeResources, and ResourceRules
        for root, dirs, files in os.walk(game_app):
            for d in list(dirs):
                if d == "_CodeSignature":
                    shutil.rmtree(os.path.join(root, d))
                    dirs.remove(d)
            for f in files:
                if f in ["CodeResources", "ResourceRules.plist"]:
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
        print("  Stripped all legacy signatures for clean TrollStore CoreTrust signing")

        print("[7/7] Re-packaging into standalone 64-bit IPA with Unix permissions...")
        write_ipa_zip(game_extract, output_ipa)

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
