#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s21_merge_h2h.py — 把 Hack2Hire 抓到的 22 道英文原题合并进 openai_statements.json"""
import json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "h2h_full.jsonl")
STMT = os.path.join(BASE, "data", "openai_statements.json")

MAP = {
 "GPU Credits": "gpu-credits", "GPU Credits II": "gpu-credits",
 "Cellular Infection Spreading": "infection-spread-cellular-automata",
 "Toy Language Grammar": "toy-language-type-inference",
 "Data Labeling Task Scheduler": "data-labeling-task-scheduler",
 "Chat Message Events Aggregation": "chat-activity-message-aggregation",
 "Maximum Grid Jumping Path": "maximum-score-grid-path-limited-jumps",
 "Design Card Game II": "poker-simulation", "Design Card Game III": "poker-simulation",
 "Fault-Tolerant Work Queue": "fault-tolerant-work-queue",
 "Guess Number with Delay": "guess-number-with-delay",
 "Design a Rectangle Board": "rectangle-board-with-undo",
 "Design a Spreadsheet with Formula Evaluation": "opensheet-spreadsheet",
 "Snapshot Social Graph": "social-network-follow-graph",
 "Design IP Range Iterator": "ip-address-cidr-iterator",
 "Shard Rebalancing": "shard-rebalance",
 "Monster Team Battle": "monster-battle-system",
 "Design In-Memory SQL": "in-memory-database-sql",
 "Design ChatBot System": "design-ai-chatbot-system",
 "Design Cluster Message Aggregation": "distributed-cluster-count-topology",
 "Design Persistent Key-Value Store": "durable-kv-store-serialization",
 "Dependency Version Check": "version-dependency",
}

# 页面 UI 噪声（逐行丢弃）
UI_TOKENS = [
 "NEW","Question Bank","Learning","Pricing","Blog","Forum","HOT","JobRadar","Log In","Join for free",
 "OpenAI","Coding Question","No questions available","Description","Solution","Discussion",
 "Submissions","Ask AI","Collapse","Common Patterns","AI Insights","Quick Summary",
 "What This Tests","×","-","Design","Graph","DFS","BFS","DP","Heap","Sorting","Hashing","Greedy",
 "Array","String","Tree","Queue","Stack","Binary Search","Two Pointers","Sliding Window",
 "Union Find","Topological Sort","Prefix Sum","Segment Tree","Trie","Math","Bit Manipulation",
 "Recursion","Simulation","Interview Stages","Frequency","Asked By","Last Reported",
 "HARD","MEDIUM","EASY","Screening","Onsite","Phone Screen","OA","Team Match","Behavioral",
 "Easy","Medium","Hard",
]
UI_SET = set(UI_TOKENS)
MORE_RE = re.compile(r"^\+\d+ ?more$")
AGO_RE  = re.compile(r"^[\d.]+\s*(months?|days?|weeks?|years?)\s*ago$")
NUM_RE  = re.compile(r"^\d+$")
PROJ_RE = re.compile(r"^Project Coding is here")

def is_ui(ln):
    s = ln.strip()
    if s in UI_SET: return True
    if MORE_RE.match(s) or AGO_RE.match(s) or NUM_RE.match(s) or PROJ_RE.match(s): return True
    return False


def clean(t, title):
    lines=[x.strip() for x in t.split("\n")]
    # 定位起点：标题第二次出现之后（第一次是页面标题）
    idx=0
    seen=0
    for i,ln in enumerate(lines):
        if ln == title:
            seen+=1
            if seen>=2: idx=i+1; break
    else:
        for i,ln in enumerate(lines):
            if "AI Insights" in ln: idx=i; break
    lines=lines[idx:]
    # 找到第一段真正的题面（跳过元数据块）
    for i,ln in enumerate(lines):
        if len(ln) > 60 and not is_ui(ln):
            idx2 = i
            break
    else:
        idx2 = 0
    lines = lines[idx2:]
    out=[]
    for ln in lines:
        if not ln: 
            if out and out[-1]!="": out.append("")
            continue
        if is_ui(ln): continue
        out.append(ln)
    s="\n".join(out).strip()
    # 砍尾部无关
    for stop in ("Discussion","Submissions","Ask AI","Related Questions","Was this helpful"):
        i=s.find(stop)
        if i>400: s=s[:i].rstrip()
    return re.sub(r"\n{3,}","\n\n",s)

def main():
    stmts=json.load(open(STMT))
    rows=[json.loads(l) for l in open(RAW)]
    by={}
    for r in rows:
        title=r["title"].split("|")[0].strip()
        body=clean(r["text"], title)
        qid=MAP.get(title)
        if not qid:
            print(f"  ? 未映射: {title}"); continue
        # 同题多版本（Card Game II/III、GPU Credits/II）取内容更长的
        if qid not in by or len(body)>len(by[qid][1]):
            by[qid]=(title, body)
    for qid,(title,body) in by.items():
        cur=stmts.get(qid,{})
        cur["original"]=body
        cur["original_src"]="Hack2Hire · OpenAI"
        cur["title_h2h"]=title
        stmts[qid]=cur
        print(f"  ✓ {title[:42]:<44} → {qid[:34]:<36} {len(body)}字")
    json.dump(stmts, open(STMT,"w"), ensure_ascii=False, indent=1)
    print(f"\n合并 {len(by)} 道英文原题")

if __name__=="__main__":
    main()
