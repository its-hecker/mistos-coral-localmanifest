#!/usr/bin/env python3
"""Prepare missing MistOS Settings UI helpers for the Android 17 build.

Only modifies the build checkout, never the user's GitHub upstream repositories.
The UI sources are fetched from an immutable Evolution X commit and retain
their original SPDX headers and license notices.
"""
from pathlib import Path
from urllib.request import urlopen
import sys

root = Path.cwd()
settings = root / "packages/apps/Settings"
mistify_candidates = [
    settings / "Mistify/src/org/mist/settings/preferences/SwitchPreviewView.kt",
    root / "packages/apps/Mistify/src/org/mist/settings/preferences/SwitchPreviewView.kt",
]
if not (settings / "Android.bp").is_file():
    sys.exit("Missing packages/apps/Settings/Android.bp; sync the MistOS sources first.")

evox_commit = "ea2ede56f48a1019c0ea580c004b009b0016e290"
for filename, signature in (
    ("Scrollbar.kt", "fun Modifier.scrollbar("),
    ("InsetFocusRing.kt", "fun Modifier.insetFocusRing("),
):
    target = settings / "src/com/android/settings/widget" / filename
    if target.exists():
        print(f"[MistOS Settings] Already exists: {target}")
        continue
    url = (f"https://raw.githubusercontent.com/Evolution-X/packages_apps_Settings/"
           f"{evox_commit}/src/com/android/settings/widget/{filename}")
    print(f"[MistOS Settings] Restoring {filename} from pinned Evolution X source")
    try:
        with urlopen(url, timeout=40) as response:
            content = response.read().decode("utf-8")
    except Exception as exc:
        sys.exit(f"Cannot retrieve {filename}: {exc}")
    if "package com.android.settings.widget" not in content or signature not in content:
        sys.exit(f"Unexpected {filename} download; refusing to install it")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

preview = next((p for p in mistify_candidates if p.is_file()), None)
if preview is None:
    sys.exit("Missing Mistify SwitchPreviewView.kt; sync packages/apps/Mistify")
text = preview.read_text(encoding="utf-8")
old_import = "import com.android.settingslib.widget.SwitchThumbIconDrawable"
old_expr = "onIcon = SwitchThumbIconDrawable.createPreview(context, bitmap).apply { setTint(trackOn) }"
if old_import in text or old_expr in text:
    if old_import not in text or old_expr not in text:
        sys.exit("Unexpected SwitchPreviewView.kt format; avoiding a partial replacement")
    text = text.replace(old_import, "import android.graphics.drawable.BitmapDrawable")
    text = text.replace(
        old_expr,
        """onIcon = (bitmap?.let { BitmapDrawable(resources, it) }
            ?: context.getDrawable(R.drawable.ic_switch_icon_check))
            ?.mutate()?.apply { setTint(trackOn) }""",
    )
    preview.write_text(text, encoding="utf-8")
    print("[MistOS Settings] Replaced unavailable switch preview drawable dependency")
else:
    print("[MistOS Settings] Switch preview dependency already handled")

# A partial MistOS framework checkout can contain the earlier Android 17
# implementations while Mistify expects the current 17.0 APIs. Restore only
# incompatible source files from one pinned MistOS framework commit.
# Back up the previous working-tree copy before replacing it.
import hashlib
import shutil

framework_commit = "640ea0b2e8021fc66da1a781397aa00dab24191f"
checks = {
    "core/java/com/android/internal/util/mist/PixelDeviceRepository.java": (
        "404a56d93e4b6488203e556a6f6d6165cde51b9a",
        ["getDefaultPifCodename(", "PIF_DEFAULT_CODENAME", "PICKER_ORDER", "getInitialSdkInt("],
    ),
    "core/java/android/security/trickystore/KeyBoxManager.java": (
        "d97f9f326aa9fc213cc4264af427d556e16dec08",
        ["validate(", "sanitizeXml("],
    ),
    "core/java/android/security/trickystore/TrickyStoreService.java": (
        "0894d2f9c421b0ff0b74f6702d1a6655a6331826",
        ["decodeKeybox(", "resolvePatchTemplate(", "isValidPatchValue(", "UNNECESSARY_PACKAGES"],
    ),
}
for rel, (expected_git_blob, names) in checks.items():
    path = root / "frameworks/base" / rel
    if not path.is_file():
        sys.exit(f"Missing framework source: {path}. Run repo sync frameworks/base")
    existing = path.read_text(encoding="utf-8")
    missing = [name for name in names if name not in existing]
    if not missing:
        print(f"[MistOS Settings] Framework APIs present: {path.name}")
        continue

    print(f"[MistOS Settings] Restoring framework APIs in {path.name}: {missing}")
    url = (
        "https://raw.githubusercontent.com/Project-Mist-OS/frameworks_base_qpr2/"
        + framework_commit + "/" + rel
    )
    try:
        with urlopen(url, timeout=45) as response:
            data = response.read()
    except Exception as exc:
        sys.exit(f"Cannot retrieve pinned MistOS framework source {rel}: {exc}")

    # Git blob SHA verifies exact tracked content, not just the URL.
    blob = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if blob != expected_git_blob:
        sys.exit(f"Unexpected source revision for {rel}: {blob}")

    replacement = data.decode("utf-8")
    if any(name not in replacement for name in names):
        sys.exit(f"Downloaded MistOS source is still missing required methods: {rel}")

    backup = root / "out/mistos-settings-compat-backup/frameworks/base" / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_bytes(data)
    print(f"[MistOS Settings] Installed matched source; backup at {backup}")

# Pin the nullable result type explicitly. Older Kotlin builds can cascade into
# misleading ELVIS_CALL inference errors when a framework API was previously missing.
dialog_path = settings / "Mistify/src/org/mist/settings/fragments/miscellaneous/TrickyStoreContent.kt"
if dialog_path.is_file():
    dialog_text = dialog_path.read_text(encoding="utf-8")
    before = "    val resolved = remember(text) {"
    after = "    val resolved: String? = remember(text) {"
    if before in dialog_text:
        dialog_path.write_text(dialog_text.replace(before, after, 1), encoding="utf-8")
        print("[MistOS Settings] Explicitly typed TrickyStore patch-date resolution")
    elif after in dialog_text:
        print("[MistOS Settings] TrickyStore patch-date resolution already typed")
    else:
        sys.exit("Unexpected TrickyStoreContent.kt; refusing to modify it")
else:
    sys.exit(f"Missing MistOS TrickyStore content: {dialog_path}")

print("[MistOS Settings] UI helpers repaired and framework APIs verified")
