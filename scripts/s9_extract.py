#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s9_extract.py — 从已抓的帖子正文 + 楼层里，把 hide 掉的字段反推出来。

背景：隐藏的是「结构化字段表」（base salary / RSU / 签字费 那几行）。
但楼主在正文自由文本里、以及回复楼层里报的 dp，**不走 hide 判断**。
所以对每个帖子做一遍字段抽取，能补回多少算多少。

用法:
  python3 s9_extract.py --fid 237
  python3 s9_extract.py --fid 237 --out data/packages_237.csv
  python3 s9_extract.py --all

产出: data/packages_<fid>.csv  + 屏幕上的覆盖率统计
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")

MONEY = r"(?:\$|USD\s*)?(\d[\d,]*(?:\.\d+)?)\s*([kKwW万千]?)"
UNIT = {"k": 1e3, "K": 1e3, "w": 1e4, "W": 1e4, "万": 1e4, "千": 1e3, "": 1}


def to_num(v, u):
    try:
        n = float(v.replace(",", ""))
    except Exception:
        return None
    return int(n * UNIT.get(u, 1))


def first(patterns, text, flags=re.I):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m
    return None


def extract(title, body):
    """返回 dict：level / base / rsu / signon / bonus / tc / company"""
    out = {}
    t = body.replace("\u200b", "")

    # 公司（标题里通常带 xx工资）
    m = re.search(r"\|([a-zA-Z0-9\-\. ]{2,24})工资", title or "")
    if m:
        out["company"] = m.group(1).strip()
    else:
        m = re.search(r"公司名称[:：]\s*([^\n]{2,30})", t)
        if m:
            out["company"] = m.group(1).strip()

    # 级别
    m = re.search(r"(?:^|\n)\s*级别的数字Level[:：]\s*([^\n]{1,20})", t)
    if m and "积分不足" not in m.group(1):
        out["level"] = m.group(1).strip()
    else:
        m = re.search(r"\b(L[3-8]|E[3-7]|IC[1-5]|SDE\s*[IV]+|Senior|Staff|Principal|Sr\.?)\b", t)
        if m:
            out["level"] = m.group(1)

    # base salary
    for p in (r"base\s*(?:salary)?\s*[:：]?\s*" + MONEY,
              r"底薪\s*[:：]?\s*" + MONEY,
              r"base\s*到\s*" + MONEY):
        m = re.search(p, t, re.I)
        if m:
            out["base"] = to_num(m.group(1), m.group(2))
            break

    # RSU / 股票
    for p in (r"(?:rsu|股票|equity|股权)[^\n]{0,30}?" + MONEY,
              r"(\d{2,6})\s*(?:股|shares?)"):
        m = re.search(p, t, re.I)
        if m:
            out["rsu"] = to_num(m.group(1), m.group(2) if m.lastindex and m.lastindex > 1 else "")
            break

    # 签字费
    for p in (r"sign[\s\-]*on[^\n]{0,40}?" + MONEY,
              r"签字费[^\n]{0,30}?" + MONEY,
              r"签字费\s*[:：]\s*" + MONEY):
        m = re.search(p, t, re.I)
        if m:
            out["signon"] = to_num(m.group(1), m.group(2))
            break

    # 年终 / bonus
    m = re.search(r"(?:bonus|年终奖|年终)[^\n]{0,30}?" + MONEY, t, re.I)
    if m:
        out["bonus"] = to_num(m.group(1), m.group(2))

    # 总包 TC
    for p in (r"(?:tc|总包|包裹|年包|总数字)[^\n]{0,24}?" + r"(\d[\d,\.]*)\s*([kKwW万])",
              r"每年\s*" + r"(\d[\d,\.]*)\s*([kKwW万])"):
        m = re.search(p, t, re.I)
        if m:
            out["tc"] = to_num(m.group(1), m.group(2))
            break

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fid", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    if a.all:
        rows = con.execute("SELECT tid,title,body FROM threads").fetchall()
        tag = "all"
    else:
        rows = con.execute(
            "SELECT tid,title,body FROM threads WHERE channel=?",
            (f"fid{a.fid}",)).fetchall()
        tag = str(a.fid)

    print(f"[*] {len(rows)} 帖")
    if not rows:
        print("    没数据，先跑 s8_forum_harvest.py --fid", a.fid)
        return

    recs, filled = [], {k: 0 for k in ("company", "level", "base", "rsu", "signon", "bonus", "tc")}
    for tid, title, body in rows:
        d = extract(title or "", body or "")
        d["tid"] = tid
        d["title"] = (title or "")[:60]
        d["chars"] = len(body or "")
        recs.append(d)
        for k in filled:
            if d.get(k):
                filled[k] += 1

    n = len(rows)
    print("\n=== 字段补全率（被 hide 的那几个字段，从正文+楼层反推）===")
    for k, v in filled.items():
        print(f"  {k:<8} {v:>4}/{n}  {v/n*100:>5.1f}%")

    out = a.out or os.path.join(DATA, f"packages_{tag}.csv")
    cols = ["tid", "company", "level", "base", "rsu", "signon", "bonus", "tc", "chars", "title"]
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(recs, key=lambda x: -(x.get("tc") or 0)):
            w.writerow(r)
    print(f"\n[+] -> {out}")

    print("\n=== 抽到的包（按 TC 排序，前 15）===")
    print(f"{'公司':<14}{'级别':<8}{'Base':>9}{'RSU':>10}{'签字费':>9}{'TC':>10}")
    for r in sorted(recs, key=lambda x: -(x.get("tc") or 0))[:15]:
        if not any(r.get(k) for k in ("base", "rsu", "tc", "signon")):
            continue
        print(f"{str(r.get('company'))[:13]:<14}{str(r.get('level'))[:7]:<8}"
              f"{r.get('base') or '-':>9}{r.get('rsu') or '-':>10}"
              f"{r.get('signon') or '-':>9}{r.get('tc') or '-':>10}")


if __name__ == "__main__":
    main()
