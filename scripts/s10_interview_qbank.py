#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s10_interview_qbank.py — 抓 /interview/ 面经题库全量元数据。

一亩三分地把论坛面经重组成了一个独立产品（Next.js + tRPC，SSR 直出）：
  https://www.1point3acres.com/interview/

这个产品**不需要论坛积分、不受 [hide] 影响**。它的付费墙是另一套（is_locked）。
公开能拿到的：
  · 1228 家公司（416 家有题）
  · 3473 道题：title / slug / category / frequency / tags / 面试阶段 /
    岗位 / 首次报告日期 / 最近考到日期 / 时长 / 来源数
  · 未锁的 briefing 全文（Markdown 正文）

锁着的是每题的精讲 body / sections。

用法:
  python3 s10_interview_qbank.py --companies            # 全部公司清单
  python3 s10_interview_qbank.py --qbank --limit 50     # 前 50 家公司的题库
  python3 s10_interview_qbank.py --qbank --resume       # 断点续跑
  python3 s10_interview_qbank.py --briefings            # 只要公开的 briefing 正文

产出: data/interview_companies.jsonl
      data/interview_qbank.jsonl
      data/interview_briefings.jsonl
"""
import argparse
import json
import os
import re
import sys
import time
import random

try:
    from curl_cffi import requests as creq
except ImportError:
    sys.exit("先 pip3 install curl_cffi")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SESS = os.path.join(DATA, "session.json")
os.makedirs(DATA, exist_ok=True)

SITE = "https://www.1point3acres.com"
COMP = os.path.join(DATA, "interview_companies.jsonl")
QBANK = os.path.join(DATA, "interview_qbank.jsonl")
BRIEF = os.path.join(DATA, "interview_briefings.jsonl")


def load_headers():
    ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    ck = ""
    if os.path.exists(SESS):
        s = json.load(open(SESS))
        ck, ua = s.get("cookies", ""), s.get("ua") or ua
    return {"Cookie": ck, "User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": f"{SITE}/interview/"}


class C:
    def __init__(self, rate=1.6):
        self.h = load_headers()
        self.iv = 1.0 / rate
        self.last = 0.0

    def next_data(self, url):
        dt = time.time() - self.last
        if dt < self.iv:
            time.sleep(self.iv - dt + random.uniform(0, 0.2))
        self.last = time.time()
        for _ in range(2):
            try:
                r = creq.get(url, headers=self.h, impersonate="chrome124", timeout=30)
                if r.status_code != 200:
                    return None, r.status_code
                m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                              r.content.decode("utf-8", "ignore"), re.S)
                if not m:
                    return None, "no_next_data"
                return json.loads(m.group(1)), 200
            except Exception as e:
                time.sleep(3)
        return None, "err"

    @staticmethod
    def queries(d):
        try:
            return d["props"]["pageProps"]["trpcState"]["json"]["queries"]
        except Exception:
            return []

    def payload(self, d, name):
        for q in self.queries(d):
            if name in json.dumps(q.get("queryKey", [])):
                return q.get("state", {}).get("data")
        return None


def dump_companies(cli, pages=60):
    seen, n = set(), 0
    with open(COMP, "w") as f:
        for p in range(1, pages + 1):
            d, st = cli.next_data(f"{SITE}/interview/problems?page={p}")
            cs = cli.payload(d, "getCombinedCompanyList") if d else None
            if not cs or not cs.get("items"):
                print(f"  页 {p} 无数据，停")
                break
            for it in cs["items"]:
                if it["company"] in seen:
                    continue
                seen.add(it["company"])
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
            total = cs.get("total")
            print(f"  已收 {n} / {total}", end="\r", flush=True)
            if total and n >= total:
                break
            time.sleep(0.3)
    print(f"\n[+] {n} 家公司 -> {COMP}")


def load_companies():
    if not os.path.exists(COMP):
        return []
    out = []
    for line in open(COMP):
        try:
            out.append(json.loads(line)["company"])
        except Exception:
            pass
    return out


def dump_qbank(cli, limit=0):
    comps = load_companies()
    if not comps:
        sys.exit("先跑 --companies")
    done = set()
    if os.path.exists(QBANK):
        for line in open(QBANK):
            try:
                done.add(json.loads(line)["company"])
            except Exception:
                pass
    todo = [c for c in comps if c not in done]
    if limit:
        todo = todo[:limit]
    print(f"[*] {len(comps)} 家公司，待抓 {len(todo)}")

    ok = 0
    with open(QBANK, "a") as f:
        for i, co in enumerate(todo, 1):
            d, st = cli.next_data(f"{SITE}/interview/problems/company/{co}")
            if not d:
                print(f"  {i} {co} HTTP {st}")
                continue
            qb = cli.payload(d, "getQbankCompany")
            oj = cli.payload(d, "getOJProblemList")
            if not qb:
                continue
            rec = {
                "company": co,
                "display_name": qb.get("display_name"),
                "status": qb.get("status"),
                "description": qb.get("description"),
                "question_count": len(qb.get("questions") or []),
                "questions": [
                    {k: q.get(k) for k in
                     ("slug", "title", "category", "frequency", "tags", "roles", "stages",
                      "reported_from", "reported_to", "last_asked", "duration_minutes",
                      "source_count", "is_locked", "is_public", "overview", "status")}
                    for q in (qb.get("questions") or [])
                ],
                "oj_total": (oj or {}).get("total"),
                "oj_items": [{"title": x.get("title"), "slug": x.get("slug"),
                              "difficulty": x.get("difficulty")}
                             for x in ((oj or {}).get("items") or [])],
                "briefings": [{"slug": b.get("slug"), "title": b.get("title"),
                               "is_locked": b.get("is_locked"), "body": b.get("body")}
                              for b in (qb.get("briefings") or [])],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            ok += 1
            print(f"  {i}/{len(todo)} {co:<18} 题{rec['question_count']:>4} "
                  f"OJ{rec['oj_total'] or 0:>5} briefing{len(rec['briefings'])}", end="\r", flush=True)
    print(f"\n[+] 完成 {ok} 家 -> {QBANK}")


def dump_briefings():
    if not os.path.exists(QBANK):
        sys.exit("先跑 --qbank")
    n = 0
    with open(BRIEF, "w") as f:
        for line in open(QBANK):
            rec = json.loads(line)
            for b in rec.get("briefings") or []:
                if b.get("body"):
                    f.write(json.dumps({"company": rec["company"], **b}, ensure_ascii=False) + "\n")
                    n += 1
    print(f"[+] {n} 篇公开 briefing -> {BRIEF}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", action="store_true")
    ap.add_argument("--pages", type=int, default=60)
    ap.add_argument("--qbank", action="store_true")
    ap.add_argument("--briefings", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rate", type=float, default=1.6)
    a = ap.parse_args()
    cli = C(a.rate)
    if a.companies:
        dump_companies(cli, a.pages)
    if a.qbank:
        dump_qbank(cli, a.limit)
    if a.briefings:
        dump_briefings()


if __name__ == "__main__":
    main()
