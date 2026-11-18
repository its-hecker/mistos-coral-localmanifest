# MistOS Android 17 — Pixel 4 XL (coral)

Maintainer: **Hecker**  
Source: [Project MistOS](https://github.com/Project-Mist-OS/manifest), branch `17.0`.

## Source integration

- [mistos-coral-device-tree](https://github.com/its-hecker/mistos-coral-device-tree) — Evolution X hardware tree adapted to MistOS product flags.
- [mistos-coral-vendor](https://github.com/its-hecker/mistos-coral-vendor) — Pixel 4 XL proprietary vendor blobs and stock signed GCam payload.
- [mistos-coral-kernel](https://github.com/its-hecker/mistos-coral-kernel) — floral Linux 4.14 with KernelSU Next Git submodule.
- [vendor_lunaris_dolby](https://github.com/its-hecker/vendor_lunaris_dolby) — Lunaris Dolby.
- [LineageOS ElmyraService](https://github.com/LineageOS/android_packages_apps_ElmyraService) — Pixel gesture service.

Pixel features inherited from the Evolution X source: **IR 3D Face HAL**, calibration/legacy NDK/Keymaster compatibility libraries, **Oslo Motion Sense** overlays and vendor services, **original signed GCam 8.7**, and **Dolby**. MistOS's own software FaceUnlock is prevented by setting `TARGET_SUPPORTS_GFU := true`; no generic camera face unlock is substituted. MistOS `mistify` uses the product name `lineage_coral`.

Do not assume the kernel, hardware features or resulting ROM are boot-tested on MistOS merely because the source import or compilation succeeds.

## ServerHive: clean checkout

```bash
mkdir -p ~/mistos-coral
cd ~/mistos-coral
repo init -u https://github.com/Project-Mist-OS/manifest.git -b 17.0 --git-lfs
git clone -b main https://github.com/its-hecker/mistos-coral-localmanifest.git .repo/local_manifests
repo sync -c --fail-fast --no-clone-bundle --no-tags -j4
USE_RBE=true MIST_BUILD_VARIANT=userdebug bash .repo/local_manifests/build.sh 2>&1 | tee ~/mistos-coral-build.log
```

The helper checks source paths, initializes KernelSU submodule, attempts vendor LFS retrieval, verifies original GCam APK assets, verifies any missing Google-services Git LFS blobs, runs guarded Face HIDL challenge/pose fixes, then calls `mistify coral userdebug` and `mist b`.

## Existing checkout

```bash
cd ~/mistos-coral
git -C .repo/local_manifests pull --ff-only
repo sync -c --fail-fast --no-clone-bundle --no-tags -j4
USE_RBE=true MIST_BUILD_VARIANT=userdebug bash .repo/local_manifests/build.sh 2>&1 | tee ~/mistos-coral-build.log
```

For a `user` target set `MIST_BUILD_VARIANT=user`.

## Known limitations

- Stock Face unlock needs the guarded framework patch to match the current MistOS framework; it fails safely if upstream code changes. Check enrollment, unlock, and model removal on a phone after flashing.
- The vendor's external Git LFS endpoint comes from the Evolution X source. GitHub mirroring can preserve Git LFS pointers but cannot guarantee the original external objects are accessible.
- KernelSU Next must be built and runtime tested.
- Motion Sense, GCam and Dolby need actual device validation. Do not ship as verified without tests.
- No other ROM repositories were changed.

## Verification after boot

```bash
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell getprop ro.product.device
adb logcat -b all -d > mistos-coral-logcat.txt
adb shell dmesg > mistos-coral-dmesg.txt
```
