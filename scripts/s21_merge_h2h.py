#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s21_merge_h2h.py — 把 Hack2Hire 抓到的英文原题合并进 openai_statements.json"""
import json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "h2h_raw.jsonl")
STMT = os.path.join(BASE, "data", "openai_statements.json")

# Hack2Hire 题名 -> 本站题 id
MAP = {
 "GPU Credits II": "gpu-credits",
 "Toy Language Grammar": "toy-language-type-inference",
 "Cellular Infection Spreading": "infection-spread-cellular-automata",
 "Data Labeling Task Scheduler": "data-labeling-task-scheduler",
 "Chat Message Events Aggregation": "chat-activity-message-aggregation",
 "Maximum Grid Jumping Path": "maximum-score-grid-path-limited-jumps",
 "Design Card Game III": "poker-simulation",
 "Fault-Tolerant Work Queue": "fault-tolerant-work-queue",
 "Guess Number with Delay": "guess-number-with-delay",
 "Design a Rectangle Board": "rectangle-board-with-undo",
}

def clean(t):
    lines = [x.rstrip() for x in t.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank > 1: continue
            out.append("")
        else:
            blank = 0
            out.append(ln.strip())
    s = "\n".join(out).strip()
    # 砍掉尾部无关块
    for stop in ("Discussion", "Submissions", "Ask AI", "Related Questions", "Question Bank"):
        i = s.find(stop)
        if i > 300: s = s[:i].rstrip()
    return s

def main():
    stmts = json.load(open(STMT))
    rows = [json.loads(l) for l in open(RAW)]
    n = 0
    for r in rows:
        title = r["title"].split("|")[0].strip()
        qid = MAP.get(title)
        if not qid:
            print(f"  ? 未映射: {title}"); continue
        body = clean(r["text"])
        cur = stmts.get(qid, {})
        cur["original"] = body
        cur["original_src"] = "Hack2Hire · OpenAI"
        cur["title_h2h"] = title
        stmts[qid] = cur
        n += 1
        print(f"  ✓ {title:<36} → {qid}  ({len(body)} 字)")
    json.dump(stmts, open(STMT, "w"), ensure_ascii=False, indent=1)
    print(f"\n合并 {n} 道英文原题")

if __name__ == "__main__":
    main()
