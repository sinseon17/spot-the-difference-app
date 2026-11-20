#!/usr/bin/env python3
"""Write www/stages.js from the verified difference report.

Each spot stores the normalised centre (x, y) and ellipse radii (rx, ry) of one
verified difference, so the game's hit test and the answer rings land exactly on
the pixels that actually differ.
"""
import json

META = [
    dict(id="stage_01", no=1, title="아늑한 한옥 카페", theme="한옥 카페", difficulty=1, time=90,
         desc="따뜻한 차 한 잔이 생각나는 한옥 카페. 주전자와 소품들을 살펴보세요."),
    dict(id="stage_02", no=2, title="정겨운 과일가게", theme="과일가게", difficulty=1, time=90,
         desc="과일이 가득한 동네 가게. 어느 바구니가 달라졌을까요?"),
    dict(id="stage_03", no=3, title="바닷가 등대 캠핑", theme="등대 캠핑", difficulty=2, time=80,
         desc="노을 지는 바닷가 캠핑장. 텐트와 등대를 자세히 보세요."),
    dict(id="stage_04", no=4, title="고양이 서점", theme="고양이 서점", difficulty=2, time=80,
         desc="고양이가 잠든 동네 서점. 책장과 소품이 조용히 바뀌었어요."),
    dict(id="stage_05", no=5, title="밤하늘 포장마차", theme="포장마차", difficulty=3, time=75,
         desc="별이 쏟아지는 밤의 포장마차. 불빛 사이를 잘 살펴보세요."),
]

MIN_RX, MIN_RY = 0.048, 0.052


def main():
    rep = json.load(open("_review/build_report.json"))
    stages = []
    for m in META:
        r = rep[m["id"]]
        assert r["status"] == "OK" and len(r["regions"]) == 5, m["id"]
        spots = []
        for mk in r["marks"]:
            rx = max(round(mk["rx"], 4), MIN_RX)
            ry = max(round(mk["ry"], 4), MIN_RY)
            spots.append({
                "x": mk["x"], "y": mk["y"],
                "rx": rx, "ry": ry,
                "r": max(rx, ry),
                "label": mk["label"],
            })
        stages.append({
            "id": m["id"], "no": m["no"], "title": m["title"], "theme": m["theme"],
            "difficulty": m["difficulty"], "time": m["time"], "desc": m["desc"],
            "a": f"images/{m['id']}_a.webp",
            "b": f"images/{m['id']}_b.webp",
            "thumb": f"images/thumbs/{m['id']}_a.jpg",
            "spots": spots,
        })

    out = ["// 스테이지 데이터 — 좌표는 원본 이미지 기준으로 픽셀 차이 검증을 거쳐 기록되었습니다.",
           "// x, y : 이미지 폭/높이에 대한 중심 비율 (0~1)",
           "// rx, ry: 이미지 폭/높이에 대한 정답 영역 반지름 비율 (0~1)",
           "const STAGES = " + json.dumps(stages, ensure_ascii=False, indent=2) + ";",
           "window.STAGES = STAGES;", ""]
    open("www/stages.js", "w").write("\n" + "\n".join(out))
    print("www/stages.js written:", len(stages), "stages")


if __name__ == "__main__":
    main()
