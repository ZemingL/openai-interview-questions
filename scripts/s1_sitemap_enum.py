#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s1_sitemap_enum.py — 枚举一亩三分地全站帖子 URL。

三条清单来源，建议全跑，合并去重：
  1. sitemap.php?page=1..N        （robots 里 2018 年就分到 3057 页，现在更多）
  2. sitemapindex.xml             （递归子 sitemap）
  3. tid 区间枚举 1..MAX           （兜底，配合 404 短路）

用法:
  python3 s1_sitemap_enum.py --sitemap --max-page 6000
  python3 s1_sitemap_enum.py --sitemapindex
  python3 s1_sitemap_enum.py --brute --max-tid 1500000 --workers 4

产出: data/tids.txt   tid<TAB>ts<TAB>url   （与 s6 格式兼容）
      data/urls.txt  全部原始 URL
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse

try:
    from curl_cffi import requests as creq
    HAVE_CFFI = True
except ImportError:
    HAVE_CFFI = False

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
TIDS = os.path.join(DATA, "tids.txt")
URLS = os.path.join(DATA, "urls.txt")
SESS = os.path.join(DATA, "session.json")

HOST = "https://www.1point3acres.com"
UA_DEFAULT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def load_session():
    if os.path.exists(SESS):
        s = json.load(open(SESS))
        return s.get("cookies", ""), s.get("ua") or UA_DEFAULT
    return "", UA_DEFAULT


def get(url, cookie, ua, timeout=25, tries=3):
    headers = {"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9"}
    if cookie:
        headers["Cookie"] = cookie
    for i in range(tries):
        try:
            if HAVE_CFFI:
                r = creq.get(url, headers=headers, impersonate="chrome124", timeout=timeout)
            else:
                import requests
                r = requests.get(url, headers=headers, timeout=timeout)
            return r.status_code, r.content
        except Exception as e:
            if i == tries - 1:
                return -1, str(e).encode()
            time.sleep(2 + i * 2)


def decode(raw):
    for enc in ("gbk", "gb18030", "utf-8"):
        try:
            h = raw.decode(enc)
        except Exception:
            continue
        if "thread-" in h:
            return h
    return raw.decode("utf-8", "ignore")


def extract_tids(html):
    out = set()
    for m in re.finditer(r"thread-(\d+)-\d+-\d+\.html", html):
        out.add(int(m.group(1)))
    for m in re.finditer(r"<loc>[^<]*?(?:thread|tid)[=-](\d+)", html):
        out.add(int(m.group(1)))
    return out


# ---------------------------------------------------------------- 1. sitemap.php
def run_sitemap(cookie, ua, max_page, start=1, sleep=0.8):
    print(f"[*] sitemap.php 翻页 {start}..{max_page}")
    allt, empty_streak = set(), 0
    for p in range(start, max_page + 1):
        code, raw = get(f"{HOST}/bbs/sitemap.php?page={p}", cookie, ua)
        if code == 403:
            print(f"\n[!] 第 {p} 页 CF 403 —— cookie 掉了，去跑 s2_cf_session.py")
            break
        if code != 200:
            print(f"\n[!] 第 {p} 页 HTTP {code}，停")
            break
        tids = extract_tids(decode(raw))
        if not tids:
            empty_streak += 1
            if empty_streak >= 5:
                print(f"\n[+] 连续 5 页空，sitemap 到底了，最后一页 {p-5}")
                break
        else:
            empty_streak = 0
        allt |= tids
        print(f"    页 {p}  +{len(tids):>4}  累计 {len(allt)}", end="\r", flush=True)
        if p % 100 == 0:
            save(allt)
        time.sleep(sleep)
    save(allt)
    return allt


# ---------------------------------------------------------------- 2. sitemapindex
def run_sitemapindex(cookie, ua, sleep=0.6):
    print("[*] sitemapindex.xml 递归")
    allt = set()
    queue, seen = [f"{HOST}/bbs/sitemapindex.xml"], set()
    while queue:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        code, raw = get(u, cookie, ua)
        if code != 200:
            print(f"    [!] {u} -> {code}")
            continue
        txt = decode(raw)
        print(f"    [sitemap] {u}  ({len(txt)}b)")
        # index 里的子 sitemap 继续入队
        for m in re.finditer(r"<loc>([^<]+)</loc>", txt):
            sub = m.group(1).strip()
            if sub.endswith((".xml", ".xml.gz")) and sub not in seen:
                queue.append(sub)
        allt |= extract_tids(txt)
        time.sleep(sleep)
    save(allt)
    return allt


# ---------------------------------------------------------------- 3. tid 枚举
def run_brute(cookie, ua, max_tid, start=1, workers=4, sleep=0.35):
    """并发探 tid 是否存在。只看 200/404，不解析正文。"""
    from concurrent.futures import ThreadPoolExecutor
    print(f"[*] tid 枚举 {start}..{max_tid}  workers={workers}")

    def probe(tid):
        code, _ = get(f"{HOST}/bbs/thread-{tid}-1-1.html", cookie, ua, timeout=15, tries=1)
        time.sleep(sleep)
        return tid, code

    alive = set()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (tid, code) in enumerate(ex.map(probe, range(start, max_tid + 1)), 1):
            if code == 200:
                alive.add(tid)
            if code == 403:
                print(f"\n[!] tid={tid} 被 CF 拦，降速/换 cookie")
            if i % 200 == 0:
                print(f"    {i}/{max_tid}  存活 {len(alive)}", end="\r", flush=True)
                save(alive)
    save(alive)
    return alive


def save(tids, url_map=None):
    """合并写入 tids.txt（保留已有，不覆盖历史成果）。"""
    old = {}
    if os.path.exists(TIDS):
        for line in open(TIDS):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                old[int(p[0])] = (p[1], p[2])
    for t in tids:
        if t not in old:
            # 用 tid 反推规范 URL，ts 留空（s3 会实时抓）
            old[t] = ("", f"https://www.1point3acres.com/bbs/thread-{t}-1-1.html")
    with open(TIDS, "w") as f:
        for tid in sorted(old):
            f.write(f"{tid}\t{old[tid][0]}\t{old[tid][1]}\n")
    with open(URLS, "w") as f:
        for tid in sorted(old):
            f.write(old[tid][1] + "\n")
    print(f"\n[+] {len(old)} 个 tid -> {TIDS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sitemap", action="store_true")
    ap.add_argument("--sitemapindex", action="store_true")
    ap.add_argument("--brute", action="store_true")
    ap.add_argument("--max-page", type=int, default=6000)
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-tid", type=int, default=1500000)
    ap.add_argument("--start-tid", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    cookie, ua = load_session()
    if not cookie:
        print("[!] 无 session.json，游客身份。CF 大概率 403，先去跑 s2_cf_session.py\n")

    if a.sitemapindex:
        run_sitemapindex(cookie, ua)
    if a.sitemap:
        run_sitemap(cookie, ua, a.max_page, a.start_page)
    if a.brute:
        run_brute(cookie, ua, a.max_tid, a.start_tid, a.workers)
    if not (a.sitemap or a.sitemapindex or a.brute):
        ap.print_help()


if __name__ == "__main__":
    main()
