#!/usr/bin/env python3
"""Check that every file the app references really exists, and that JSON is valid."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []
checked = 0


def exists(rel, origin):
    global checked
    checked += 1
    p = os.path.join(ROOT, rel.lstrip("./"))
    if not os.path.exists(p):
        problems.append(f"{origin}: missing {rel}")


def check_html():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    for m in re.finditer(r'(?:src|href)="([^"#:]+)"', html):
        url = m.group(1)
        if url.startswith("http") or url.startswith("data:"):
            continue
        if url in ("manifest.json",) or url.endswith((".css", ".js", ".png", ".jpg", ".webp", ".json")):
            exists(url, "index.html")


def check_json():
    for name in ("manifest.json", "capacitor.config.json", "package.json"):
        path = os.path.join(ROOT, name)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            problems.append(f"{name}: invalid JSON ({e})")
            continue
        if name == "manifest.json":
            for icon in data.get("icons", []):
                exists(icon["src"], "manifest.json")


def check_sw():
    sw = open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
    block = sw.split("const PRECACHE = [", 1)[1].split("];", 1)[0]
    for m in re.finditer(r"'([^']+)'", block):
        url = m.group(1)
        if url == "./":
            exists("index.html", "sw.js")
            continue
        exists(url, "sw.js")


def check_stages():
    src = open(os.path.join(ROOT, "stages.js"), encoding="utf-8").read()
    data = json.loads(src.split("const STAGES = ", 1)[1].rstrip().rstrip(";").split(";\nwindow.STAGES")[0])
    assert len(data) == 5, "expected 5 stages"
    for st in data:
        for key in ("a", "b", "thumb"):
            exists(st[key], f"stages.js {st['id']}")
        assert len(st["spots"]) == 5, f"{st['id']} spots != 5"
        for sp in st["spots"]:
            assert 0 <= sp["x"] <= 1 and 0 <= sp["y"] <= 1, f"{st['id']} spot out of range"
            assert sp["rx"] > 0 and sp["ry"] > 0, f"{st['id']} radius invalid"
            assert sp["x"] - sp["rx"] >= -0.05 and sp["x"] + sp["rx"] <= 1.05, f"{st['id']} spot off canvas"
    print(f"stages: {len(data)} × 5 spots, coordinates in range")


def check_js_syntax():
    """Rough brace/paren balance check — catches truncation and stray characters."""
    for name in ("app.js", "sw.js", "stages.js"):
        s = open(os.path.join(ROOT, name), encoding="utf-8").read()
        for open_c, close_c in (("{", "}"), ("(", ")"), ("[", "]")):
            if s.count(open_c) != s.count(close_c):
                problems.append(f"{name}: unbalanced {open_c}{close_c} "
                                f"({s.count(open_c)} vs {s.count(close_c)})")


if __name__ == "__main__":
    check_html()
    check_json()
    check_sw()
    check_stages()
    check_js_syntax()
    print(f"references checked: {checked}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("all references OK")
