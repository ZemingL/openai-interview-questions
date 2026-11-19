#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s3_crawl.py — 带登录态批量抓一亩三分地帖子正文，SQLite 落盘。

单条帖子的取数策略（自动降级，命中即停）：
  1. 正常页  thread-TID-1-1.html          ← 有 200+ 积分时内容最全
  2. 手机版  forum.php?mod=viewthread&tid=TID&mobile=yes
  3. 打印页  forum.php?mod=viewthread&action=printable&tid=TID
  4. Archiver archiver/tid-TID.html
  5. 翻页    thread-TID-1-{page}.html      （第 1 种拿到正文后按 posts_n 续翻）

用法:
  python3 s3_crawl.py --limit 100
  python3 s3_crawl.py --resume                     # 断点续跑
  python3 s3_crawl.py --tid 4428 --tid 1000016     # 只抓指定
  python3 s3_crawl.py --rate 1.5                   # 每秒请求数（默认 1.2，别飙）

产出: data/1p3a.db  threads(tid, url, title, body, posts_n, pages, channel, fetched_at)
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys
import time

try:
    from curl_cffi import requests as creq
    HAVE_CFFI = True
except ImportError:
    HAVE_CFFI = False

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
TIDS = os.path.join(DATA, "tids.txt")
SESS = os.path.join(DATA, "session.json")
os.makedirs(DATA, exist_ok=True)

HOST = "https://www.1point3acres.com"
UA_DEFAULT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

CHANNELS = [
    ("normal",   "{H}/bbs/thread-{T}-1-1.html", "pc"),
    ("mobile",   "{H}/bbs/forum.php?mod=viewthread&tid={T}&mobile=yes", "mobile"),
    ("print",    "{H}/bbs/forum.php?mod=viewthread&action=printable&tid={T}", "pc"),
    ("archiver", "{H}/bbs/archiver/tid-{T}.html", "pc"),
]


def load_session():
    if os.path.exists(SESS):
        s = json.load(open(SESS))
        return s.get("cookies", ""), s.get("ua") or UA_DEFAULT
    return "", UA_DEFAULT


class Crawler:
    def __init__(self, cookie, ua, rate=1.2, pages=3):
        self.cookie = cookie
        self.ua = ua
        self.interval = 1.0 / max(rate, 0.1)
        self.pages = pages
        self.last = 0.0
        self.cf_hits = 0

    def _throttle(self):
        dt = time.time() - self.last
        if dt < self.interval:
            time.sleep(self.interval - dt + random.uniform(0, 0.3))
        self.last = time.time()

    def get(self, url, mobile=False, timeout=25):
        self._throttle()
        headers = {
            "User-Agent": UA_MOBILE if mobile else self.ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.1point3acres.com/bbs/",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        try:
            if HAVE_CFFI:
                r = creq.get(url, headers=headers, impersonate="chrome124",
                             timeout=timeout, allow_redirects=True)
            else:
                import requests
                r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        except Exception as e:
            return -1, b"", str(e)
        if r.status_code == 403 and b"Just a moment" in r.content:
            self.cf_hits += 1
        return r.status_code, r.content, ""

    @staticmethod
    def decode(raw):
        """utf-8 严格解码优先；gbk 页面会在这里抛异常自动落到 gb18030。"""
        if not raw:
            return ""
        try:
            return raw.decode("utf-8")
        except Exception:
            pass
        for enc in ("gb18030", "gbk"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", "ignore")

    @staticmethod
    def parse(html):
        """返回 (title, [(author, floor_text), ...])"""
        title = ""
        m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            title = re.sub(r"\s*-\s*(一亩三分地|Powered by Discuz).*$", "", title, flags=re.I)
        floors = []
        # 作者
        authors = re.findall(r'class="xw1"[^>]*>(.*?)</a>', html, re.S)
        for i, m in enumerate(re.finditer(r'id="postmessage_(\d+)"[^>]*>(.*?)</td>', html, re.S | re.I)):
            t = m.group(2)
            t = re.sub(r"<script.*?</script>", "", t, flags=re.S | re.I)
            t = re.sub(r"<br\s*/?>|</p>|</div>|</blockquote>", "\n", t, flags=re.I)
            t = re.sub(r"<[^>]+>", "", t)
            t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                  .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
            t = re.sub(r"[ \t]+", " ", t)
            t = re.sub(r"\n{3,}", "\n\n", t).strip()
            if t:
                a = authors[i] if i < len(authors) else ""
                a = re.sub(r"<[^>]+>", "", a).strip()
                floors.append((a, t))
        if not floors:
            # printable / archiver 的纯文本结构
            for m in re.finditer(r"<pre[^>]*>(.*?)</pre>", html, re.S | re.I):
                t = re.sub(r"<[^>]+>", "", m.group(1))
                t = re.sub(r"\n{3,}", "\n\n", t).strip()
                if len(t) > 20:
                    floors.append(("", t))
        return title, floors

    def one(self, tid, want_pages=3):
        """返回 dict 或 None"""
        best = None
        for name, tpl, kind in CHANNELS:
            url = tpl.format(H=HOST, T=tid)
            code, raw, err = self.get(url, mobile=(kind == "mobile"))
            if code != 200 or not raw:
                continue
            html = self.decode(raw)
            title, floors = self.parse(html)
            if not floors:
                continue
            if best is None or len(floors) > len(best["floors"]):
                best = {"tid": tid, "url": url, "title": title,
                        "floors": floors, "channel": name}
            if len(floors) >= 10:      # 首页满 10 楼，不用再试别的通道
                break

        if best and best["channel"] == "normal" and want_pages > 1:
            # 续翻第 2..N 页
            for p in range(2, want_pages + 1):
                url = f"{HOST}/bbs/thread-{tid}-{p}-1.html"
                code, raw, err = self.get(url)
                if code != 200 or not raw:
                    break
                _, floors = self.parse(self.decode(raw))
                if not floors:
                    break
                best["floors"] += floors
        return best


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS threads(
        tid INTEGER PRIMARY KEY,
        url TEXT, title TEXT, body TEXT,
        posts_n INTEGER, channel TEXT, pages INTEGER, fetched_at TEXT
    )""")
    # 兼容 s6 先建过的表：缺列就补
    have = {r[1] for r in con.execute("PRAGMA table_info(threads)")}
    for col, ddl in (("channel", "TEXT"), ("pages", "INTEGER"), ("url", "TEXT"),
                     ("ts", "TEXT"), ("posts_n", "INTEGER")):
        if col not in have:
            con.execute(f"ALTER TABLE threads ADD COLUMN {col} {ddl}")
    con.commit()
    return con


def save(con, r, pages):
    body = "\n\n".join(f"[{a}] {t}" if a else t for a, t in r["floors"])
    con.execute(
        "INSERT OR REPLACE INTO threads(tid,url,title,body,posts_n,channel,pages,fetched_at) "
        "VALUES(?,?,?,?,?,?,?,datetime('now'))",
        (r["tid"], r["url"], r["title"], body, len(r["floors"]), r["channel"], pages))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--tid", action="append", default=[])
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--rate", type=float, default=1.2, help="每秒请求数")
    ap.add_argument("--pages", type=int, default=3, help="每个帖子翻几页")
    a = ap.parse_args()

    cookie, ua = load_session()
    if not cookie:
        print("[!] 没有 session.json。CF 会拦，先去跑 s2_cf_session.py\n")

    con = init_db()
    if a.tid:
        tids = [int(t) for t in a.tid]
    else:
        if not os.path.exists(TIDS):
            print("[!] 没有 data/tids.txt，先跑 s1_sitemap_enum.py --sitemap")
            return
        tids = []
        for line in open(TIDS):
            p = line.split("\t")
            if p and p[0].strip().isdigit():
                tids.append(int(p[0]))
    if a.resume:
        done = {r[0] for r in con.execute("SELECT tid FROM threads WHERE body IS NOT NULL AND body!=''")}
        before = len(tids)
        tids = [t for t in tids if t not in done]
        print(f"[*] 断点续跑：{before} -> {len(tids)}")
    if a.limit:
        tids = tids[:a.limit]

    cr = Crawler(cookie, ua, rate=a.rate, pages=a.pages)
    ok = fail = 0
    t0 = time.time()
    for i, tid in enumerate(tids, 1):
        r = cr.one(tid, a.pages)
        if not r:
            fail += 1
        else:
            save(con, r, a.pages)
            ok += 1
        speed = i / max(time.time() - t0, 1e-6)
        print(f"  {i}/{len(tids)}  ok={ok} fail={fail}  {speed:.2f}/s  '{tid}'",
              end="\r", flush=True)
        if cr.cf_hits >= 3:
            print(f"\n[!] 连续被 CF 拦 {cr.cf_hits} 次 —— 停。重跑 s2_cf_session.py 换 cookie。")
            break
    print(f"\n[+] 完成 ok={ok} fail={fail}  库={DB}")

    rows = con.execute("SELECT count(*), sum(length(body)) FROM threads").fetchone()
    print(f"[*] 库内帖子 {rows[0]} 条，正文合计 {rows[1] or 0} 字")


if __name__ == "__main__":
    main()
