#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s22_merge_sd.py — 合并 Hack2Hire 的 16 道 System Design 题"""
import json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "h2h_sd.json")
STMT = os.path.join(BASE, "data", "openai_statements.json")

MAP = {
 "Design Payment System": "payment-coffee-shop",
 "Design Slack-like Chat System": "design-slack",
 "Design CICD System": "multi-tenant-ci-cd-workflow",
 "Design Online Chess Game": "design-chess-game",
 "Design AI Chatbot App": "design-ai-chatbot-system",
 "Design Webhook Delivery System": "webhook-delivery-system",
 "Design TinyURL": "design-url-shortener",
 "Design Youtube": "design-youtube",
 "Design Job Scheduler": "design-job-scheduler",
 "Design Google Calendar": "design-google-calendar",
 "Design ChatGPT": "gpt-3-playground",
 "Design GPU Scheduling Platform": "design-sora-video-generation",
 "Design Distributed Web Crawler": "design-web-crawler",
 "Design A Nearby POI Service": "points-of-interest-yelp",
 "Design a Distributed Power Grid Control System": "grid-demand-response-dispatch",
 "Design a Sandboxed Cloud IDE": "design-cloud-ide",
}

def demd(t):
    """Markdown -> 可读纯文本"""
    t = re.sub(r"::::?\w*(\[[^\]]*\])?", "", t)          # :::qa-item / :::you[You]
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)          # 标题
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)                # 粗体
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", t)    # 斜体
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)         # 链接 -> 文字
    t = re.sub(r"`([^`]+)`", r"\1", t)                       # 行内代码
    t = re.sub(r"^\s*[-*]\s+", "· ", t, flags=re.M)       # 列表
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def main():
    stmts = json.load(open(STMT))
    rows = json.load(open(RAW))
    n = 0
    for p in rows:
        title = p.get("title", "")
        qid = MAP.get(title)
        if not qid:
            print(f"  ? 未映射: {title}"); continue
        body = demd(p.get("contentPreview") or "")
        if len(body) < 200:
            print(f"  ! 内容过短: {title}"); continue
        cur = stmts.get(qid, {})
        cur["original"] = body
        cur["original_src"] = "Hack2Hire · OpenAI System Design"
        cur["title_h2h"] = title
        stmts[qid] = cur
        n += 1
        print(f"  ✓ {title[:44]:<46} → {qid[:32]:<34} {len(body)}字")
    json.dump(stmts, open(STMT, "w"), ensure_ascii=False, indent=1)
    print(f"\n合并 {n} 道 SD 题")

if __name__ == "__main__":
    main()
