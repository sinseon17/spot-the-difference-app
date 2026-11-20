#!/usr/bin/env python3
"""Add a release signing config to the Capacitor-generated android/app/build.gradle.

Capacitor's Android template ships a release build type without a signing config, so
`bundleRelease` would produce an unsigned bundle that Google Play rejects. This script
injects a signingConfigs block that reads the keystore from environment variables and
attaches it to the release build type.

Run after `npx cap add android`. Safe to run twice.
"""
import os
import re
import sys

GRADLE = os.path.join("android", "app", "build.gradle")

SIGNING_BLOCK = """    signingConfigs {
        release {
            def ksPath = System.getenv("SPOTDIFF_KEYSTORE") ?: "spotdiff-release.keystore"
            storeFile file(ksPath)
            storePassword System.getenv("SPOTDIFF_STORE_PASSWORD") ?: "spotdiff123"
            keyAlias System.getenv("SPOTDIFF_KEY_ALIAS") ?: "spotdiff"
            keyPassword System.getenv("SPOTDIFF_KEY_PASSWORD") ?: "spotdiff123"
        }
    }
"""


def find_block(text, header):
    """Return (start, end) index of the brace block that follows `header`."""
    m = re.search(header, text)
    if not m:
        return None
    i = text.find("{", m.end() - 1)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return (i, j)
    return None


def patch(path=GRADLE):
    if not os.path.exists(path):
        print(f"!! {path} not found — run `npx cap add android` first")
        return 1
    src = open(path, encoding="utf-8").read()

    if "SPOTDIFF_KEYSTORE" in src:
        print("signing config already present")
        return 0

    # 1) insert signingConfigs right before buildTypes
    if "signingConfigs" not in src:
        m = re.search(r"^(\s*)buildTypes\s*\{", src, flags=re.M)
        if not m:
            print("!! could not find buildTypes block")
            return 1
        src = src[:m.start()] + SIGNING_BLOCK + src[m.start():]

    # 2) attach it to the release build type
    bt = find_block(src, r"buildTypes\s*\{")
    if not bt:
        print("!! could not locate buildTypes braces")
        return 1
    start, end = bt
    body = src[start:end]
    rel = re.search(r"release\s*\{", body)
    if not rel:
        print("!! no release build type inside buildTypes")
        return 1
    insert_at = start + rel.end()
    if "signingConfig" not in body[rel.end():rel.end() + 400]:
        src = src[:insert_at] + "\n            signingConfig signingConfigs.release" + src[insert_at:]

    open(path, "w", encoding="utf-8").write(src)
    print(f"patched {path}: release signing config attached")
    return 0


if __name__ == "__main__":
    sys.exit(patch(*sys.argv[1:]))
