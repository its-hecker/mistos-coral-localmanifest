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

# Missing framework functions must come from the matched MistOS 17.0
# framework tree. Do not synthesize implementations or silently disable them.
checks = {
    "core/java/com/android/internal/util/mist/PixelDeviceRepository.java":
        ["getDefaultPifCodename(", "PIF_DEFAULT_CODENAME", "PICKER_ORDER", "getInitialSdkInt("],
    "core/java/android/security/trickystore/KeyBoxManager.java":
        ["validate(", "sanitizeXml("],
    "core/java/android/security/trickystore/TrickyStoreService.java":
        ["decodeKeybox(", "resolvePatchTemplate(", "isValidPatchValue(", "UNNECESSARY_PACKAGES"],
}
for rel, names in checks.items():
    path = root / "frameworks/base" / rel
    if not path.is_file():
        sys.exit(f"Missing framework source: {path}. Run repo sync frameworks/base")
    content = path.read_text(encoding="utf-8")
    missing = [name for name in names if name not in content]
    if missing:
        sys.exit(
            f"Framework source revision is incompatible: {rel} lacks {missing}. "
            "Run repo sync -c --fail-fast frameworks/base packages/apps/Mistify packages/apps/Settings"
        )
print("[MistOS Settings] UI helpers repaired and framework APIs verified")
