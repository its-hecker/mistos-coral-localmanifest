#!/usr/bin/env bash
set -euo pipefail

mist_build_error() {
    local status="$1" line="$2" command="$3"
    printf '[MistOS] Build command failed (exit %s) at line %s: %s\n' "$status" "$line" "$command" >&2
}
trap 'mist_build_error "$?" "$LINENO" "$BASH_COMMAND"' ERR

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

# Android envsetup.sh and ROM build frontends expect ordinary interactive Bash
# options. In particular, internal pipelines may return SIGPIPE (141) when
# pipefail + errexit are inherited, even while initialization is successful.
# Keep strict failure checking for the preparation above, then explicitly
# check the return status of each Android build step below.
trap - ERR
set +e
set +u
set +o pipefail

echo "[MistOS] Sourcing Android environment"
source build/envsetup.sh
setup_status=$?
if (( setup_status != 0 )); then
    echo "[MistOS] Android environment setup failed (exit ${setup_status})" >&2
    exit "$setup_status"
fi

echo "[MistOS] Selecting coral ${MIST_BUILD_VARIANT:-userdebug}"
mistify coral "${MIST_BUILD_VARIANT:-userdebug}"
selection_status=$?
if (( selection_status != 0 )); then
    echo "[MistOS] mistify coral failed (exit ${selection_status})" >&2
    exit "$selection_status"
fi

echo "[MistOS] Starting ROM compilation"
mist b
build_status=$?
if (( build_status != 0 )); then
    echo "[MistOS] ROM compilation failed (exit ${build_status})" >&2
    exit "$build_status"
fi
echo "[MistOS] Compilation command completed successfully"
