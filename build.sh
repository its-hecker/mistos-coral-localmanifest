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

echo "Preparing MistOS Settings compilation compatibility"
python3 .repo/local_manifests/tools/repair_mist_settings.py

export WITH_GMS=true
export MISTOS_MAINTAINER=Hecker

source build/envsetup.sh
mistify coral "${MIST_BUILD_VARIANT:-userdebug}"
mist b
