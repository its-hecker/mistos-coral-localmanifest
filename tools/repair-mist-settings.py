#!/usr/bin/env python3
"""Resolve MistOS 17.0 lock-screen preference keys missing from framework API stubs.

The keys below are defined in the upstream Mistify lock-screen preferences XML.
Use their actual SettingsProvider names rather than compiled-in framework constants
that may be absent from the framework API jar in some 17.0 checkouts.
"""

from pathlib import Path
import re

TARGET = Path(
    "packages/apps/Settings/Mistify/src/org/mist/settings/fragments/lockscreen/LockScreen.java"
)
KEYS = {
    "Settings.Secure.LOCK_SCREEN_STACKED_NOTIFICATIONS": "lock_screen_stacked_notifications",
    "Settings.Secure.LOCK_SCREEN_MOTO_COMPACT_NOTIFICATIONS": "lock_screen_moto_compact_notifications",
    "Settings.System.NOTIFICATION_ICONS_CENTER_ALIGNED": "notification_icons_center_aligned",
}


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"MistOS lock-screen source not found: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    updated = source
    changed = 0
    for symbol, key in KEYS.items():
        literal = f'"{key}"'
        if symbol in updated:
            if updated.count(symbol) != 1:
                raise SystemExit(f"Unexpected duplicate references to {symbol} in {TARGET}")
            updated = updated.replace(symbol, literal)
            changed += 1
        # Fail closed when upstream changes the source rather than silently skipping.
        if not re.search(r"findPreference\(\s*" + re.escape(literal) + r"\s*\)", updated):
            raise SystemExit(f"Missing or changed preference lookup for {key} in {TARGET}")

    if updated != source:
        TARGET.write_text(updated, encoding="utf-8")
    print(f"MistOS lock-screen preference keys OK ({changed} substitutions)")


if __name__ == "__main__":
    main()
