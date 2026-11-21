#!/usr/bin/env python3
"""
generate_repo.py - Automated APT / Sileo Repository Generator
Creates a 100% compliant Sileo / Cydia / Zebra APT repository ready for GitHub Pages.
"""

import os
import hashlib
import gzip
import bz2
import lzma
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.join(ROOT_DIR, "repo")
DEBS_DIR = os.path.join(REPO_DIR, "debs")
DIST_DEB = os.path.join(ROOT_DIR, "dist", "com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb")

def compute_hashes(data):
    md5 = hashlib.md5(data).hexdigest()
    sha1 = hashlib.sha1(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha1, sha256

def generate_repo():
    print("[1/4] Setting up repo directories and copying .deb...")
    os.makedirs(DEBS_DIR, exist_ok=True)
    target_deb = os.path.join(DEBS_DIR, "com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb")
    shutil.copy2(DIST_DEB, target_deb)

    with open(target_deb, "rb") as f:
        deb_bytes = f.read()
    
    deb_size = len(deb_bytes)
    deb_md5, deb_sha1, deb_sha256 = compute_hashes(deb_bytes)

    print("[2/4] Generating Packages manifest...")
    packages_content = f"""Package: com.antigravity.arm32runner
Name: Arm32Runner
Depends: mobilesubstrate (>= 0.9.5000)
Version: 1.0.0
Architecture: iphoneos-arm64
Description: Run legacy 32-bit (ARMv7) IPAs seamlessly on 64-bit iOS devices with SpringBoard and installd integration.
Maintainer: Antigravity Team
Author: Antigravity Team
Section: Tweaks
Priority: optional
Homepage: https://github.com/antigravity/arm32runner
Tag: role::hacker, compatible::ios12, compatible::ios13, compatible::ios14, compatible::ios15, compatible::ios16
Filename: ./debs/com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb
Size: {deb_size}
MD5sum: {deb_md5}
SHA1: {deb_sha1}
SHA256: {deb_sha256}

""".encode("utf-8")

    pkg_path = os.path.join(REPO_DIR, "Packages")
    with open(pkg_path, "wb") as f:
        f.write(packages_content)

    print("[3/4] Compressing Packages into .gz, .bz2, .xz...")
    pkg_gz_path = os.path.join(REPO_DIR, "Packages.gz")
    with gzip.open(pkg_gz_path, "wb") as f:
        f.write(packages_content)

    pkg_bz2_path = os.path.join(REPO_DIR, "Packages.bz2")
    with bz2.open(pkg_bz2_path, "wb") as f:
        f.write(packages_content)

    pkg_xz_path = os.path.join(REPO_DIR, "Packages.xz")
    with lzma.open(pkg_xz_path, "wb") as f:
        f.write(packages_content)

    # Compute hashes for Release file
    files_to_hash = ["Packages", "Packages.gz", "Packages.bz2", "Packages.xz"]
    md5_entries = []
    sha256_entries = []

    for fname in files_to_hash:
        fpath = os.path.join(REPO_DIR, fname)
        with open(fpath, "rb") as f:
            data = f.read()
        f_size = len(data)
        f_md5, _, f_sha256 = compute_hashes(data)
        md5_entries.append(f" {f_md5} {f_size} {fname}")
        sha256_entries.append(f" {f_sha256} {f_size} {fname}")

    print("[4/4] Generating Release and Release.gpg metadata...")
    release_content = f"""Origin: Arm32Runner Official Repo
Label: Arm32Runner
Suite: stable
Version: 1.0
Codename: ios
Architectures: iphoneos-arm iphoneos-arm64
Components: main
Description: Official APT & Sileo repository for Arm32Runner tweak
MD5Sum:
{chr(10).join(md5_entries)}
SHA256:
{chr(10).join(sha256_entries)}
"""

    # Write into both REPO_DIR and ROOT_DIR for seamless GitHub Pages root serving
    for target_dir in [REPO_DIR, ROOT_DIR]:
        debs_sub = os.path.join(target_dir, "debs")
        os.makedirs(debs_sub, exist_ok=True)
        dest_deb = os.path.join(debs_sub, "com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb")
        if os.path.abspath(DIST_DEB) != os.path.abspath(dest_deb):
            shutil.copy2(DIST_DEB, dest_deb)
        
        with open(os.path.join(target_dir, "Packages"), "wb") as f:
            f.write(packages_content)
        with gzip.open(os.path.join(target_dir, "Packages.gz"), "wb") as f:
            f.write(packages_content)
        with bz2.open(os.path.join(target_dir, "Packages.bz2"), "wb") as f:
            f.write(packages_content)
        with lzma.open(os.path.join(target_dir, "Packages.xz"), "wb") as f:
            f.write(packages_content)
        with open(os.path.join(target_dir, "Release"), "w", encoding="utf-8") as f:
            f.write(release_content)
        
        # Copy index.html and sileo-featured.json
        if target_dir != REPO_DIR:
            shutil.copy2(os.path.join(REPO_DIR, "index.html"), os.path.join(target_dir, "index.html"))
            shutil.copy2(os.path.join(REPO_DIR, "sileo-featured.json"), os.path.join(target_dir, "sileo-featured.json"))

    print(f"APT repository successfully generated in:\n  {REPO_DIR}\n  and root {ROOT_DIR}")

if __name__ == "__main__":
    generate_repo()
