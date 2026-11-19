#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s16_qa.py — 站点数据 QA：完整性 / 去重 / 原帖一致性 / 摘录溯源"""
import json, os, re, sqlite3, collections, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
SITE = os.path.join(BASE, "site", "data.json")

PASS, FAIL, WARN = [], [], []
def ok(m): PASS.append(m); print(f"  ✓ {m}")
def bad(m): FAIL.append(m); print(f"  ✗ {m}")
def warn(m): WARN.append(m); print(f"  ! {m}")

d = json.load(open(SITE))
q = d["questions"]
con = sqlite3.connect(DB)
db = {r[0]: r for r in con.execute("SELECT tid,title,body,posts_n FROM threads")}

print(f"\n{'='*68}\n1. 结构完整性  ({len(q)} 道题)\n{'='*68}")
need = ["id", "name", "name_en", "category", "roles", "stages", "heat",
        "runnable", "snippets", "posts"]
miss = [(x.get("id"), k) for x in q for k in need if k not in x]
ok("所有题含全部必需字段") if not miss else bad(f"缺字段: {miss[:5]}")

nulls = [x["id"] for x in q if not x.get("name") or not x.get("name_en")]
ok("name / name_en 无空值") if not nulls else bad(f"空名: {nulls[:5]}")

cats = collections.Counter(x["category"] for x in q)
ok(f"分类分布合理: {dict(cats)}") if set(cats) <= {"coding","system-design","behavioral","other"} \
    else bad(f"非法分类: {set(cats)}")

print(f"\n{'='*68}\n2. 去重校验\n{'='*68}")
dup_id = [k for k, v in collections.Counter(x["id"] for x in q).items() if v > 1]
ok("题目 id 无重复") if not dup_id else bad(f"重复 id: {dup_id}")
dup_name = [k for k, v in collections.Counter(x["name"] for x in q).items() if v > 1]
ok("中文名无重复") if not dup_name else bad(f"重复中文名: {dup_name}")
dup_en = [k for k, v in collections.Counter(x["name_en"] for x in q).items() if v > 1]
ok("英文名无重复") if not dup_en else bad(f"重复英文名: {dup_en}")
# 语义重复：中英文名互相包含
near = []
for i, a in enumerate(q):
    for b in q[i+1:]:
        na, nb = a["name"].lower(), b["name"].lower()
        if len(na) > 5 and (na in nb or nb in na):
            near.append((a["name"], b["name"]))
ok("无名称互相包含的疑似重复") if not near else warn(f"疑似重复 {len(near)} 组: {near[:3]}")

print(f"\n{'='*68}\n3. 原帖一致性（对库核验）\n{'='*68}")
bad_tid, bad_title, bad_meta, orphan = [], [], [], []
for x in q:
    for p in x["posts"]:
        t = p["tid"]
        if t not in db:
            bad_tid.append((x["id"], t)); continue
        dbtitle, dbbody, dbposts = db[t][1], db[t][2], db[t][3]
        # 标题一致性（允许 html 实体差异）
        a = re.sub(r"&\w+;|\s+", "", (p["title"] or ""))
        b = re.sub(r"&\w+;|\s+", "", (dbtitle or ""))
        if a != b:
            bad_title.append((x["id"], t, p["title"][:30], (dbtitle or "")[:30]))
        if p["chars"] != len(dbbody or ""):
            bad_meta.append((x["id"], t, "chars", p["chars"], len(dbbody or "")))
        if p["floors"] != (dbposts or 0):
            bad_meta.append((x["id"], t, "floors", p["floors"], dbposts))
    # 摘录必须来自该题的关联帖
    ptids = {p["tid"] for p in x["posts"]}
    for s in x["snippets"]:
        if s["tid"] not in ptids:
            orphan.append((x["id"], s["tid"]))

ok(f"所有关联 tid 存在于库") if not bad_tid else bad(f"库中不存在的 tid: {bad_tid[:5]}")
ok(f"标题与库完全一致") if not bad_title else bad(f"标题不一致 {len(bad_title)} 处: {bad_title[:3]}")
ok(f"字数/楼层数与库一致") if not bad_meta else bad(f"元数据不一致 {len(bad_meta)} 处: {bad_meta[:3]}")
ok(f"摘录 tid 均属于该题关联帖") if not orphan else bad(f"摘录来源越界: {orphan[:5]}")

print(f"\n{'='*68}\n4. 摘录溯源（内容真在原帖里）\n{'='*68}")
notfound = []
for x in q:
    for s in x["snippets"]:
        if s["tid"] not in db: continue
        body = db[s["tid"]][2] or ""
        probe = re.sub(r"\s+", "", s["text"])[:24]
        if probe and probe not in re.sub(r"\s+", "", body):
            notfound.append((x["id"], s["tid"], s["text"][:40]))
ok(f"全部摘录能在原帖原文中找到") if not notfound else bad(f"摘录对不上原文 {len(notfound)} 处: {notfound[:3]}")

print(f"\n{'='*68}\n5. 业务规则\n{'='*68}")
runn_ok = all((x["runnable"] == (x["category"] == "coding")) for x in q)
ok(f"runnable 与 category 严格对应（{sum(1 for x in q if x['runnable'])} 道 coding 题带编辑器）") \
    if runn_ok else bad("有 coding 题不带编辑器，或非 coding 题带了编辑器")

zero = [x["name"] for x in q if x["heat"] == 0]
ok(f"零热度题 {len(zero)} 道（题库里有但帖子未提及）") if len(zero) <= 20 else warn(f"零热度过多: {len(zero)}")

nosnip = [x["name"] for x in q if not x["snippets"]]
warn(f"{len(nosnip)} 道题无题面摘录: {nosnip[:6]}") if nosnip else ok("所有题都有题面摘录")

nopost = [x["name"] for x in q if not x["posts"]]
warn(f"{len(nopost)} 道题无关联原帖: {nopost[:6]}") if nopost else ok("所有题都有关联原帖")

# heat 与 posts 数量一致性（posts 上限 40）
over = [(x["name"], x["heat"], len(x["posts"])) for x in q if len(x["posts"]) > x["heat"]]
ok("关联帖数不超过热度") if not over else bad(f"关联帖多于热度: {over[:3]}")

print(f"\n{'='*68}\n6. 站内统计 vs 数据\n{'='*68}")
html = open(os.path.join(BASE, "site", "index.html"), encoding="utf-8").read()
for label, val in (("道题/questions", d["meta"]["questions"]),
                   ("篇原帖/posts", d["meta"]["posts"])):
    ok(f"{label} = {val} 已写入页面") if str(val) in html else bad(f"{label} 未写入页面")

embedded = json.loads(re.search(r'<script id="DATA" type="application/json">(.*?)</script>',
                                html, re.S).group(1))
ok("页面内嵌 JSON 与 data.json 完全一致") if embedded == d else bad("页面内嵌数据与 data.json 不一致")

print(f"\n{'='*68}\n汇总\n{'='*68}")
print(f"  PASS {len(PASS)}   FAIL {len(FAIL)}   WARN {len(WARN)}")
if FAIL:
    print("\n  失败项：")
    for f in FAIL: print("   ✗", f)
    sys.exit(1)
print("\n  数据层全绿")
