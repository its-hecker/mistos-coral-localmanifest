#!/usr/bin/env bash
set -euo pipefail

[[ -f build/envsetup.sh ]] || { echo "Run from the MistOS Android 17 checkout root" >&2; exit 1; }
[[ -f device/google/coral/lineage_coral.mk ]] || { echo "MistOS coral device tree missing" >&2; exit 1; }
[[ -f vendor/google/coral/coral-vendor.mk ]] || { echo "Coral vendor sources missing" >&2; exit 1; }
[[ -f kernel/google/msm-4.14/Makefile ]] || { echo "Floral kernel sources missing" >&2; exit 1; }
[[ -f vendor/lunaris/dolby/dolby.mk ]] || { echo "Lunaris Dolby source missing" >&2; exit 1; }
[[ -f vendor/google/coral/camera/tools/prepare_camera.py ]] || { echo "Signed GCam payload helper missing" >&2; exit 1; }
[[ -f device/google/coral/faceunlock/tools/apply_framework_fixes.py ]] || { echo "3D Face framework compatibility helper missing" >&2; exit 1; }

grep -Fq 'MISTOS_MAINTAINER := "Hecker"' device/google/coral/lineage_coral.mk
grep -Fq 'TARGET_SUPPORTS_GFU := true' device/google/coral/lineage_coral.mk
grep -Fq 'TARGET_PROVIDES_FACE_UNLOCK_HAL := true' device/google/coral/lineage_coral.mk

echo "Checking MistOS TrickyStore framework compatibility"
attestation_relative="core/java/android/security/trickystore/AttestationUtils.java"
attestation_source="frameworks/base/$attestation_relative"
[[ -f "$attestation_source" ]] || { echo "Missing $attestation_source" >&2; exit 1; }

if ! grep -Fq 'public static void invalidateFallbackBootState()' "$attestation_source" ||
   ! grep -Fq 'public static boolean isValidPatchLevel(String value)' "$attestation_source"; then
    echo "Mismatched TrickyStore API; restoring the matching MistOS AttestationUtils.java"
    mkdir -p out/mist-framework-backups
    candidate="$(mktemp out/trickystore-attestation.XXXXXX)"
    trap 'rm -f "$candidate"' EXIT

    if git -C frameworks/base show "HEAD:$attestation_relative" > "$candidate" &&
       grep -Fq 'public static void invalidateFallbackBootState()' "$candidate" &&
       grep -Fq 'public static boolean isValidPatchLevel(String value)' "$candidate"; then
        echo "Using the file from the current frameworks/base checkout HEAD"
    else
        echo "Fetching the correct file from Project-Mist-OS/frameworks_base_qpr2 17.0"
        git -C frameworks/base fetch --no-tags https://github.com/Project-Mist-OS/frameworks_base_qpr2.git refs/heads/17.0
        git -C frameworks/base show "FETCH_HEAD:$attestation_relative" > "$candidate"
        grep -Fq 'public static void invalidateFallbackBootState()' "$candidate"
        grep -Fq 'public static boolean isValidPatchLevel(String value)' "$candidate"
    fi

    backup="out/mist-framework-backups/AttestationUtils.$(date -u +%Y%m%dT%H%M%SZ).java"
    cp -p "$attestation_source" "$backup"
    cp "$candidate" "$attestation_source"
    rm -f "$candidate"
    trap - EXIT
    echo "Restored TrickyStore API compatibility; original backed up to $backup"
fi

echo "Preparing floral kernel and KernelSU Next"
git -C kernel/google/msm-4.14 submodule update --init --recursive

echo "Fetching original coral vendor Git LFS assets"
git -C vendor/google/coral lfs pull

echo "Validating Google Camera coral split APK payloads"
python3 vendor/google/coral/camera/tools/prepare_camera.py --check-hashes

echo "Checking GMS Git LFS objects, where applicable"
python3 .repo/local_manifests/repair-gms-lfs.py

echo "Checking and applying guarded native IR Face HAL framework fixes"
python3 device/google/coral/faceunlock/tools/apply_framework_fixes.py --check
python3 device/google/coral/faceunlock/tools/apply_framework_fixes.py --apply
python3 device/google/coral/faceunlock/tools/apply_framework_fixes.py --check

export WITH_GMS=true
export MISTOS_MAINTAINER=Hecker

source build/envsetup.sh
mistify coral "${MIST_BUILD_VARIANT:-userdebug}"
mist b
