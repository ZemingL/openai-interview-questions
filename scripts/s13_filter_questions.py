#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s13_filter_questions.py — 从 openai 帖子池里挑出真正含题面/题解的，输出干净原题清单。"""
import json, re, sqlite3, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data/1p3a.db")
OUT_J = os.path.join(BASE, "data/openai_questions.jsonl")
OUT_MD = os.path.join(BASE, "openai_原题清单.md")

# 非面经：招聘流程/内推/team match/八卦
DROP = re.compile(r"内推|team\s*match|求捞|工作强度|timeline|price|涨|靠谱吗|多久.*回复|"
                  r"reach\s*out|约谈|怎么才能|如何拿到|冷冻|headcount|包比|待遇|"
                  r"公司评价|裁员|上市|股票|面试材料prompt|ghost|排期", re.I)
# 真面经
KEEP = re.compile(r"面经|挂经|过经|面筋|电面|店面|昂赛|onsite|VO|OA|题目|原题|"
                  r"coding|system\s*design|\bSD\b|voiced|面镜|虚拟现场|表演|技术面", re.I)

# 题目签名（名称 -> 正则）
TOPICS = {
 "植物感染 / 细胞自动机": r"植物感染|感染|infect|cellular.?automata|传染病|plant",
 "GPU Credits": r"gpu\s*credit|gpu\s*额度|credit.*(grant|subtract|balance)",
 "Monster Battle": r"monster\s*battle|怪兽",
 "Poker / Card Game": r"poker|扑克|card\s*game|牌型|同花|三条|踢脚",
 "Payment / Coffee Shop": r"payment|coffee\s*shop|咖啡店|支付系统",
 "KV Store / In-memory DB": r"kv\s*store|key.?value|内存数据库|in-?memory\s*(db|database|kv)",
 "ModalLock / 多线程": r"modal\s*lock|modallock|线程|threading|并发",
 "Machine Topology": r"topology|拓扑",
 "Spreadsheet / OpenSheet": r"spreadsheet|opensheet|电子表格",
 "Chess / 棋类": r"chess|国际象棋",
 "Sora / 视频生成": r"sora|视频生成|video\s*generat",
 "Webhook": r"webhook",
 "URL Shortener / 短链": r"url\s*shortener|短链",
 "Resumable Iterator": r"resumable|迭代器|iterator",
 "IPv4 / CIDR Iterator": r"cidr|ipv4|ip\s*地址",
 "Autograd / Backprop": r"autograd|backprop|反向传播|梯度",
 "Transformer Bug Hunt": r"transformer.*bug|bug\s*hunt|pytorch.*refactor",
 "Cross Entropy / Label Smoothing": r"cross.?entropy|label\s*smooth|交叉熵",
 "Work Queue": r"work\s*queue|任务队列|reserve.*complete.*fail",
 "Rate Limiter": r"rate\s*limit|限流",
 "Refactoring 重构": r"refactor|重构",
 "Behavioral / BQ": r"\bBQ\b|behavioral|行为面|leadership|why\s*openai",
 "Design Slack": r"design\s*slack|slack",
 "Cloud IDE": r"cloud\s*ide|云端\s*ide",
 "Distributed / Shard": r"分片|shard|一致性|distributed",
 "AI Safety / AGI": r"ai\s*safety|agi",
 "消息聚合 / 聊天": r"message\s*aggregat|chat.*(aggregat|activity)|消息聚合",
 "ML Coding (numpy/数值)": r"numpy|数值稳定|ml\s*coding|colab",
 "Deep Dive 项目深挖": r"deep\s*dive|深挖|technical\s*deep",
 "Spotify/其他设计题": r"design\s*(spotify|youtube|google\s*calendar|trivia|大逃杀)",
 "Tag/HTML 解析": r"html\s*tag|tag\s*parser|解析\s*html|strip\s*tag",
}


def main():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT tid,title,body FROM threads WHERE channel='openai'").fetchall()
    keep, drop = [], []
    for tid, title, body in rows:
        t = title or ""
        if DROP.search(t) and not KEEP.search(t):
            drop.append((tid, t)); continue
        if not KEEP.search(t):
            drop.append((tid, t)); continue
        topics = [k for k, p in TOPICS.items() if re.search(p, t + "\n" + (body or ""), re.I)]
        keep.append({"tid": tid, "title": t, "chars": len(body or ""),
                     "hide": "积分高于" in (body or ""), "topics": topics})

    keep.sort(key=lambda x: -x["chars"])
    with open(OUT_J, "w") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cnt = collections.Counter()
    for r in keep:
        for t in r["topics"]:
            cnt[t] += 1

    lines = ["# OpenAI 面经原题清单（一亩三分地）", "",
             f"帖子池 {len(rows)} 篇 → 剔除 {len(drop)} 篇非面经 → **保留 {len(keep)} 篇**",
             f"总字数 {sum(r['chars'] for r in keep):,}", "",
             "## 一、题目频次（按命中帖子数）", "", "| 帖数 | 题目 |", "|---:|---|"]
    for k, v in cnt.most_common():
        lines.append(f"| {v} | {k} |")
    lines += ["", "## 二、按字数排序的帖子（前 40）", "", "| tid | 字数 | 楼层内容 | 命中题目 |", "|---:|---:|---|---|"]
    for r in keep[:40]:
        ti = (r['title'][:44]).replace("|", "\\|")
        lines.append(f"| {r['tid']} | {r['chars']:,} | {ti} | {', '.join(r['topics']) or '-'} |")
    lines += ["", "## 三、被剔除的非面经帖（前 20）", ""]
    for tid, t in drop[:20]:
        lines.append(f"- {tid} {t[:60].replace(chr(124), chr(92)+chr(124))}")
    open(OUT_MD, "w").write("\n".join(lines))

    print(f"帖子池 {len(rows)}  保留 {len(keep)}  剔除 {len(drop)}")
    print(f"-> {OUT_J}\n-> {OUT_MD}\n")
    print("题目频次：")
    for k, v in cnt.most_common(30):
        print(f"  {v:>3}  {k}")


if __name__ == "__main__":
    main()
