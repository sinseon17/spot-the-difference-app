#!/usr/bin/env python3
"""Drive the real app in headless Chromium and capture verification screenshots.

Usage: python3 scripts/shoot.py [base_url]
Outputs: _review/shots/*.png (home, game, found, clear, gameover) and console log.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/index.html"
OUT = "_review/shots"
os.makedirs(OUT, exist_ok=True)

VIEWPORT = {"width": 390, "height": 844}


def tap_spot(page, panel, st, index):
    box = page.locator(panel).bounding_box()
    sp = st["spots"][index]
    page.mouse.click(box["x"] + sp["x"] * box["width"], box["y"] + sp["y"] * box["height"])


def main():
    errors = []
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2,
                                  is_mobile=True, has_touch=True,
                                  locale="ko-KR")
        page = ctx.new_page()
        page.on("console", lambda m: (logs.append(f"{m.type}: {m.text}"), errors.append(m.text) if m.type == "error" else None))
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/01_home.png")

        stages = page.evaluate("window.STAGES")
        print("stages:", [s["id"] for s in stages])

        # 스테이지 1 시작
        page.locator(".stage-card").first.click()
        page.wait_for_timeout(900)
        page.screenshot(path=f"{OUT}/02_game.png")

        st = stages[0]
        # 정답 1개 + 확실한 오답 1개 (빈 벽면)
        tap_spot(page, "#panelA", st, 2)
        page.wait_for_timeout(350)
        box = page.locator("#panelB").bounding_box()
        page.mouse.click(box["x"] + 0.08 * box["width"], box["y"] + 0.55 * box["height"])
        page.wait_for_timeout(200)
        page.screenshot(path=f"{OUT}/03_found_and_wrong.png")
        page.wait_for_timeout(900)

        # 힌트
        page.locator("#hintBtn").click()
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/04_hint.png")

        # 나머지 정답 모두 (아래 그림에서)
        for i in [0, 1, 3, 4]:
            tap_spot(page, "#panelB", st, i)
            page.wait_for_timeout(260)
        page.wait_for_timeout(900)
        page.screenshot(path=f"{OUT}/05_clear_modal.png")
        print("modal visible:", page.locator("#modalRoot").is_visible())

        # 목록으로
        page.locator('[data-act="home"]').first.click()
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/06_home_after_clear.png")

        # 게임오버: 3번 오답을 연속으로
        page.locator(".stage-card").nth(1).click()
        page.wait_for_timeout(700)
        box = page.locator("#panelA").bounding_box()
        for _ in range(3):
            page.mouse.click(box["x"] + 0.5 * box["width"], box["y"] + 0.95 * box["height"])
            page.wait_for_timeout(420)
        page.wait_for_timeout(700)
        page.screenshot(path=f"{OUT}/07_gameover.png")
        print("gameover modal:", page.locator("#modalRoot").is_visible())

        # PWA 확인용: manifest / sw 등록 / 오프라인
        print("manifest:", page.evaluate("document.querySelector('link[rel=manifest]').href"))
        print("sw:", page.evaluate("navigator.serviceWorker.controller ? 'controlled' : 'not-controlled'"))

        # 오프라인 재방문 테스트
        ctx.set_offline(True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        ok_offline = page.locator("#screenHome").is_visible()
        page.screenshot(path=f"{OUT}/08_offline.png")
        print("offline home visible:", ok_offline)
        ctx.set_offline(False)

        # 다른 화면 크기 / 마지막 스테이지 확인
        for w, h in [(375, 667), (430, 932)]:
            p2 = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2,
                                     is_mobile=True, has_touch=True, locale="ko-KR").new_page()
            p2.goto(BASE, wait_until="networkidle")
            p2.locator(".stage-card").nth(4).click()
            p2.wait_for_timeout(900)
            p2.screenshot(path=f"{OUT}/09_stage5_{w}x{h}.png")
            p2.close()

        browser.close()

    print("console errors:", errors if errors else "none")
    open("_review/console.txt", "w").write("\n".join(logs))
    print("shots ->", OUT)


if __name__ == "__main__":
    main()
