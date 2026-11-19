#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s18_add_answers.py — 给 site/data.json 的每道题补 answer 字段（答案折叠区内容）"""
import json, re, sqlite3, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site", "data.json")
DB = os.path.join(BASE, "data", "1p3a.db")

SCORE = re.compile(
    r"解法|思路|答案|实现|代码|复杂度|优化|关键|核心|注意|怎么做|这样写|应该|"
    r"第一问|第二问|第三问|follow.?up|步骤|def |class |return |import ", re.I)
BAD = re.compile(
    r"提升卡|置顶卡|关贴卡|变色卡|千斤顶|狗仔卡|当前离线|使用道具|积分\s*通行证|"
    r"大米\s*颗|鳄梨\s*个|注册时间|最后登录|本帖隐藏|积分高于|您当前积分|"
    r"使用VIP即刻解锁|注册一亩三分地|itemprop|class=\"|&#x?[0-9A-Fa-f]+;|"
    r"给您点个赞|给你点个赞|查看全部评分|相关帖子|上一篇|下一篇|"
    r"does not represent|隐私提醒|禁止发布广告|公众号|hotpot|"
    r"^\s*\d+\s*$|^x$", re.I)


def pick(body, limit=1100):
    """从正文里挑一段最能当答案的（按行聚合到 limit 字）"""
    if not body:
        return None
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    keep = []
    for ln in lines:
        if BAD.search(ln):
            continue
        if len(ln) < 6:
            continue
        keep.append(ln)
    text = "\n".join(keep)
    if len(text) < 120:
        return None
    # 找信息密度最高的起点
    if len(text) <= limit:
        return text
    best, best_sc = 0, -1
    for i in range(0, max(1, len(text) - limit), 200):
        seg = text[i:i + limit]
        sc = len(SCORE.findall(seg))
        if sc > best_sc:
            best_sc, best = sc, i
    return text[best:best + limit]


def main():
    d = json.load(open(SITE))
    con = sqlite3.connect(DB)
    cache = {}
    def body_of(tid):
        if tid not in cache:
            r = con.execute("SELECT body FROM threads WHERE tid=?", (tid,)).fetchone()
            cache[tid] = r[0] if r else ""
        return cache[tid]

    n = 0
    for q in d["questions"]:
        best, best_sc = None, -1
        for p in (q.get("posts") or [])[:15]:
            b = body_of(p["tid"])
            seg = pick(b)
            if not seg:
                continue
            sc = len(SCORE.findall(seg)) * 10 + len(seg) / 100
            if sc > best_sc:
                best_sc, best = sc, {"tid": p["tid"], "text": seg}
        q["answer"] = [best] if best else []
        n += bool(best)

    json.dump(d, open(SITE, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"[+] {n}/{len(d['questions'])} 道题有答案")
    for q in d["questions"][:3]:
        if q["answer"]:
            print(f"\n{q['name']}:")
            print("  " + q["answer"][0]["text"][:200].replace("\n", " / "))


if __name__ == "__main__":
    main()
