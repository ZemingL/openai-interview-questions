#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s23_classify.py — 把题目按 ML Coding / General Coding / Design / HR 四类划分

写入每题的 track 字段，UI 用它做一级分类。
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site", "data.json")

# 明确的归类表（按题目 id）
TRACK = {
 # ── ML Coding：机器学习 / 数值 / 训练相关 ──
 "ml-coding-numpy": "ml-coding",
 "numpy-1nn-wx-b": "ml-coding",
 "autograd-hillis-steele-scan": "ml-coding",
 "transformer-bug-hunt": "ml-coding",
 "masked-cross-entropy-loss": "ml-coding",
 "classifier-noisy-annotators": "ml-coding",
 "sharded-matmul-backprop-debugging": "ml-coding",
 "streaming-entropy": "ml-coding",
 "light-source-sampling-mle": "ml-coding",
 "model-calibration-ace-metric": "ml-coding",
 "math-reasoning-stopping-time": "ml-coding",
 "code-reading-pytorch-refactor": "ml-coding",
 "data-labeling-task-scheduler": "ml-coding",

 # ── Design：系统设计 / ML 系统设计 ──
 "payment-coffee-shop": "design",
 "design-slack": "design",
 "design-chess-game": "design",
 "design-sora-video-generation": "design",
 "design-cloud-ide": "design",
 "design-url-shortener": "design",
 "design-google-calendar": "design",
 "design-ai-chatbot-system": "design",
 "design-typing-race-game": "design",
 "design-steam-game-store-launcher": "design",
 "design-youtube": "design",
 "design-job-scheduler": "design",
 "design-web-crawler": "design",
 "webhook-delivery-system": "design",
 "multi-tenant-ci-cd-workflow": "design",
 "grid-demand-response-dispatch": "design",
 "points-of-interest-yelp": "design",
 "gpt-3-playground": "design",
 "real-time-ai-product-feature": "design",
 "image-sharing-content-deduplication": "design",
 "rag-search-ml-design": "design",
 "chatgpt-enterprise-rag": "design",
 "mining-novel-data-unlabeled-corpus": "design",
 "crossword-puzzle-solver": "design",
 "android-mobile-screen": "design",

 # ── HR：行为面 / 招聘流程 / 软技能 ──
 "recruiter-hr-screen-bq": "hr",
 "hm-bq-why-openai": "hr",
 "cross-functional-collaboration-bq": "hr",
 "engineering-management-fundamentals": "hr",
 "ai-safety-agi": "hr",
 "technical-deep-dive": "hr",

 # ── General Coding：其余全是 ──
}

TRACK_META = [
 {"id": "ml-coding", "zh": "ML Coding", "en": "ML Coding"},
 {"id": "general-coding", "zh": "General Coding", "en": "General Coding"},
 {"id": "design", "zh": "Design", "en": "Design"},
 {"id": "hr", "zh": "HR / 行为面", "en": "HR / Behavioral"},
]


def main():
    d = json.load(open(SITE))
    cnt = {}
    for q in d["questions"]:
        tr = TRACK.get(q["id"], "general-coding")
        q["track"] = tr
        cnt[tr] = cnt.get(tr, 0) + 1
    d["tracks"] = [dict(m, count=cnt.get(m["id"], 0)) for m in TRACK_META]
    json.dump(d, open(SITE, "w"), ensure_ascii=False, separators=(",", ":"))
    print("分类结果：")
    for m in d["tracks"]:
        print(f"  {m['zh']:<16} {m['count']:>3} 道")
    print(f"  {'合计':<16} {sum(cnt.values()):>3} 道")
    # 抽查
    for tr in ("ml-coding", "design", "hr"):
        names = [q["name"] for q in d["questions"] if q["track"] == tr][:6]
        print(f"\n{tr}: " + "、".join(n[:22] for n in names))


if __name__ == "__main__":
    main()
