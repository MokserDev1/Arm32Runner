#!/usr/bin/env python3
"""
standalone_injector.py - Automated Standalone 32-bit to 64-bit IPA Converter
Part of Arm32Runner

Binds the genuine 64-bit JIT runtime, RootFS, and guest dynamic linker directly
into any legacy 32-bit IPA, creating a 100% standalone 64-bit iOS application
that installs via TrollStore with its own home screen icon and name!
"""

import os
import sys
import zipfile
import plistlib
import shutil
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_IPA = os.path.join(ROOT_DIR, "dist", "LiveExec32_runtime.ipa")

def convert_to_standalone(input_ipa, output_ipa=None):
    if not os.path.exists(RUNTIME_IPA):
        print(f"Error: Runtime IPA not found at {RUNTIME_IPA}")
        return False

    if not output_ipa:
        base, ext = os.path.splitext(input_ipa)
        output_ipa = f"{base}_standalone_arm64{ext}"

    print(f"===========================================================")
    print(f"  Arm32Runner Standalone Converter                        ")
    print(f"  Converting: {os.path.basename(input_ipa)}               ")
    print(f"  Target:     {os.path.basename(output_ipa)}              ")
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

        print("[2/5] Extracting 64-bit ARM64 runtime and guest RootFS...")
        with zipfile.ZipFile(RUNTIME_IPA, "r") as z_run:
            z_run.extractall(runtime_extract)

        run_payload = os.path.join(runtime_extract, "Payload")
        run_app = os.path.join(run_payload, [d for d in os.listdir(run_payload) if d.endswith(".app")][0])

        print("[3/5] Injecting 64-bit execution engine and guest libraries...")
        # 3.1 Preserve 32-bit executable
        orig_bin_path = os.path.join(game_app, orig_exec)
        payload_bin_path = os.path.join(game_app, f"{orig_exec}.arm32")
        if not os.path.exists(payload_bin_path) and os.path.exists(orig_bin_path):
            shutil.move(orig_bin_path, payload_bin_path)
            print(f"  Preserved 32-bit binary as: {os.path.basename(payload_bin_path)}")

        # 3.2 Copy 64-bit launcher into CFBundleExecutable
        run_bin = os.path.join(run_app, "LiveExec32")
        if not os.path.exists(run_bin):
            run_bin = [os.path.join(run_app, f) for f in os.listdir(run_app) if os.path.isfile(os.path.join(run_app, f)) and not f.endswith(".plist")][0]
        
        shutil.copy2(run_bin, orig_bin_path)
        os.chmod(orig_bin_path, 0o755)
        print(f"  Injected native 64-bit launcher: {orig_exec}")

        # 3.3 Inject Frameworks
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

        # 3.4 Inject RootFS
        run_rootfs = os.path.join(run_app, "RootFS")
        game_rootfs = os.path.join(game_app, "RootFS")
        if os.path.exists(run_rootfs) and not os.path.exists(game_rootfs):
            shutil.copytree(run_rootfs, game_rootfs)
            print("  Injected guest RootFS and dyld emulation libraries")

        print("[4/5] Updating Info.plist and removing obsolete signatures...")
        plist["CFBundleSupportedPlatforms"] = ["iPhoneOS"]
        plist["UIDeviceFamily"] = [1, 2]
        plist["LiveExecGuestBinary"] = f"{orig_exec}.arm32"
        if "UIRequiredDeviceCapabilities" in plist:
            plist["UIRequiredDeviceCapabilities"] = [c for c in plist.get("UIRequiredDeviceCapabilities", []) if c not in ["armv7", "armv6"]]

        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)

        # Remove old code signature
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
    print(f"\nSUCCESS! Created Standalone 64-bit IPA:\n  {output_ipa} ({out_size_mb:.2f} MB)")
    print("Ready to install directly via TrollStore!\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python standalone_injector.py <path_to_game.ipa> [output.ipa]")
        sys.exit(1)
    in_ipa = sys.argv[1]
    out_ipa = sys.argv[2] if len(sys.argv) > 2 else None
    ok = convert_to_standalone(in_ipa, out_ipa)
    sys.exit(0 if ok else 1)
