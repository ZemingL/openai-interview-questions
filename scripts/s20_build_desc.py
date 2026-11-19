#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s20_build_desc.py — 为每道题聚合「完整题目描述」

思路：把该题在所有相关帖子里出现的窗口全部收集 → 句子级去重 → 过滤噪声 →
coding 题拼成尽可能完整的题面，design/behavioral 题只留一句话。

输出：site/data.json 里每题新增
  desc     中文完整描述（字符串）
  desc_en  英文原题片段（若有）
  desc_src 来源 tid 列表
"""
import json, os, re, sqlite3, hashlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site", "data.json")
DB = os.path.join(BASE, "data", "1p3a.db")

# 句子必须带这些才算「在讲题」
CORE = re.compile(
    r"题目|题意|要求|实现|给定|输入|输出|返回|参数|边界|约束|条件|规则|复杂度|"
    r"follow[\s-]?up|追问|第[一二三四五1-5]问|part\s*\d|设计|写一个|写个|"
    r"需要支持|支持以下|请实现|比如|例如|example|样例|"
    r"数组|链表|树|图|队列|栈|哈希|堆|字符串|矩阵|网格|线程|锁|事务|索引|缓存|"
    r"class\s|def\s|return\s|import\s|```|O\(", re.I)
# 出现就丢的句子
NOISE = re.compile(
    r"recruiter|\bHR\b|约面|排期|多久|几周|几天|回复|timeline|时间线|流程|几轮|轮次|加面|"
    r"挂了|被拒|拒信|reject|fail|offer|包裹|薪资|工资|签字费|\bTC\b|\bbase\b|\bRSU\b|"
    r"求米|加米|大米|积分|私聊|评论区|补充内容|编辑于|更新于|"
    r"team[\s-]?match|内推|referral|冷冻期|\bHC\b|headcount|招人|"
    r"感觉|可惜|难受|心态|发挥|郁闷|遗憾|反思|祝|加油|好运|感谢|谢谢|patpat|安慰|"
    r"放水|吐槽|无语|服了|后悔|懊悔|离谱|"
    r"面试官|体验|感受|氛围|"
    r"刷题|复习|mock|备考|正在准备|准备了|分享给|指正|"
    r"\bBQ\b|behavioral|行为面|"
    r"楼主|匿名|发表于|浏览|收藏|"
    r"我做了|只做了|没做完|时间不够|来不及|"
    r"以上|仅供参考|自行判断|不确定|"
    r"gas furnace|德国|unpaid|\bPIP\b|does not represent|地里新农|1Point3Acres|"
    r"面经\s*\||挂经\s*\||求捞|请愿|效仿|"
    r"We'll cover|You will need|Please let us know|invitation|"
    r"公众号|论坛|版块|隐私提醒|禁止发布", re.I)


def split_sents(t):
    return [x.strip() for x in re.split(r"(?<=[。！？；!?;])\s*|\n+", t or "") if x and x.strip()]


def key(s):
    """句子指纹：去标点后取前 40 字，用于去重"""
    n = re.sub(r"[^\w\u4e00-\u9fff]", "", s).lower()
    return hashlib.md5(n[:40].encode()).hexdigest()[:12]


def collect(q, body_of):
    """收集该题所有相关句子"""
    pat = re.compile(q["_pat"], re.I) if q.get("_pat") else None
    sents, seen, src = [], set(), []
    for p in (q.get("posts") or [])[:30]:
        b = body_of(p["tid"])
        if not b:
            continue
        hit = False
        for m in (pat.finditer(b) if pat else []):
            hit = True
            s0, e0 = max(0, m.start() - 200), min(len(b), m.end() + 400)
            for s in split_sents(b[s0:e0]):
                if len(s) < 10 or NOISE.search(s):
                    continue
                # 句子本身必须沾这道题，否则不要（防串题）
                if not (pat.search(s) if pat else False):
                    continue
                if not CORE.search(s) and len(s) < 30:
                    continue
                k = key(s)
                if k in seen:
                    continue
                seen.add(k)
                sents.append(s)
        if hit:
            src.append(p["tid"])
    return sents, src


def build(q, body_of):
    sents, src = collect(q, body_of)
    if not sents:
        return {"desc": "", "desc_en": "", "desc_src": []}

    # 打分：技术密度高、含题目特征的优先
    def score(s):
        c = len(CORE.findall(s))
        return c * 10 + min(len(s), 200) / 20

    sents.sort(key=score, reverse=True)

    if q["category"] == "coding":
        limit = 1600
    else:
        limit = 400            # design / behavioral：一句话级别

    out, ln = [], 0
    zh, en = [], []
    for s in sents:
        if ln >= limit:
            break
        # 中英分流
        if len(re.findall(r"[\u4e00-\u9fff]", s)) >= 6:
            zh.append(s)
        else:
            en.append(s)
        ln += len(s)
        out.append(s)

    # ---- 结构化：把碎片按「第X问 / follow-up / 约束」归类 ----
    PARTS = re.compile(r"第[一二三四五1-5]问|part\s*\d", re.I)
    FOLLOW = re.compile(r"follow[\s-]?up|追问|接着问|然后问|会问", re.I)
    CONS = re.compile(r"要求|约束|边界|条件|复杂度|注意|必须|不能|只能", re.I)
    buckets = {"parts": [], "follow": [], "cons": [], "other": []}
    seen2 = set()
    for x in out:
        k = key(x)
        if k in seen2:
            continue
        seen2.add(k)
        if FOLLOW.search(x):
            buckets["follow"].append(x)
        elif PARTS.search(x):
            buckets["parts"].append(x)
        elif CONS.search(x):
            buckets["cons"].append(x)
        else:
            buckets["other"].append(x)

    seg = []
    if buckets["parts"]:
        seg.append("【题目分解】")
        seg += ["· " + x for x in sorted(buckets["parts"])[:8]]
    if buckets["cons"]:
        seg.append("【约束 / 注意】")
        seg += ["· " + x for x in buckets["cons"][:5]]
    if buckets["follow"]:
        seg.append("【追问方向】")
        seg += ["· " + x for x in buckets["follow"][:5]]
    if buckets["other"]:
        seg.append("【原帖其他描述】")
        seg += ["· " + x for x in buckets["other"][:8]]
    if seg:
        desc = "\n".join(seg)[:limit]
    else:
        desc = "\n".join(out)[:limit]
    desc_en = "\n".join(en)[:700]
    return {"desc": desc, "desc_en": desc_en, "desc_src": src[:12]}


# 复现 s14 的题目匹配正则（按 id）
def load_pat():
    src = open(os.path.join(BASE, "scripts", "s14_build_site_data.py"), encoding="utf-8").read()
    pats = {}
    for m in re.finditer(r'"([a-z0-9\-]+)":\s*\("([^"]*)",\s*r?"([^"]+)"', src):
        pats[m.group(1)] = m.group(3)
    return pats


STMTS = {}
_sp = os.path.join(BASE, "data", "openai_statements.json")
if os.path.exists(_sp):
    STMTS = json.load(open(_sp))


def main():
    d = json.load(open(SITE))
    con = sqlite3.connect(DB)
    cache = {}
    def body_of(tid):
        if tid not in cache:
            r = con.execute("SELECT body FROM threads WHERE tid=?", (tid,)).fetchone()
            cache[tid] = (r[0] if r else "") or ""
        return cache[tid]

    pats = load_pat()
    ok = 0
    for q in d["questions"]:
        q["_pat"] = pats.get(q["id"], "")
        r = build(q, body_of)
        q.update(r)
        q.pop("_pat", None)
        ok += bool(r["desc"])

    # 合并人工整理的结构化题面
    n_stmt = 0
    for q in d["questions"]:
        st = STMTS.get(q["id"])
        if st:
            lines = []
            if st.get("original"):
                lines.append(st["original"])
                lines.append("")
            if st.get("stmt"):  lines.append("【题目】" + st["stmt"])
            if st.get("input"): lines.append("【输入】" + st["input"])
            if st.get("output"):lines.append("【输出】" + st["output"])
            if st.get("notes"): lines.append("【要点】" + st["notes"])
            q["stmt"] = "\n".join(lines)
            q["stmt_src"] = ("题面原文：Hack2Hire · " + (st.get("title_h2h") or "") + "　｜　中文要点为整理版"
                             if st.get("original") else
                             "整理版（原帖未给完整题面，依据题名与面经片段整理）")
            n_stmt += 1
        else:
            q["stmt"] = ""
            q["stmt_src"] = ""

    json.dump(d, open(SITE, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"[+] {ok}/{len(d['questions'])} 道题有原帖描述，{n_stmt} 道有整理题面")
    for q in d["questions"][:3]:
        if q["desc"]:
            print(f"\n【{q['name']}】{q['category']}  {len(q['desc'])}字")
            print("  " + q["desc"][:400].replace("\n", " / "))


if __name__ == "__main__":
    main()
