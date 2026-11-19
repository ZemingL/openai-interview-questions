#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s8_forum_harvest.py — 按版块全量抓取，重点打抖包袱/面经版。

这些版块是 hide 最密集的地方。已经确认：结构化字段被服务端拦，
但**正文自由文本 + 全部回复楼层不受 hide 影响** —— 作者自己写出来的数字、
以及回复里别人报的 dp，全在。

用法:
  python3 s8_forum_harvest.py --fid 237 --pages 30            # 抖包袱版
  python3 s8_forum_harvest.py --fid 145 --pages 20            # 海外面经
  python3 s8_forum_harvest.py --fid 259 --pages 20            # 数科面经
  python3 s8_forum_harvest.py --fid 237 --pages 5 --max-posts 100

产出: data/threads_<fid>.jsonl   每行一条帖子（标题/正文/楼层/是否含hide）
      data/1p3a.db 同步 upsert
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import random

try:
    from curl_cffi import requests as creq
except ImportError:
    sys.exit("先 pip3 install curl_cffi")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
SESS = os.path.join(DATA, "session.json")
HOST = "https://www.1point3acres.com"


def load_session():
    if os.path.exists(SESS):
        s = json.load(open(SESS))
        return s.get("cookies", ""), s.get("ua")
    return "", None


def dec(b):
    for e in ("gb18030", "gbk", "utf-8"):
        try:
            return b.decode(e)
        except Exception:
            pass
    return b.decode("utf-8", "ignore")


class Client:
    def __init__(self, cookie, ua, rate=1.5):
        self.cookie = cookie
        self.ua = ua or ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        self.iv = 1.0 / rate
        self.last = 0.0
        self.cf = 0

    def get(self, url, timeout=25):
        dt = time.time() - self.last
        if dt < self.iv:
            time.sleep(self.iv - dt + random.uniform(0, 0.25))
        self.last = time.time()
        h = {"Cookie": self.cookie, "User-Agent": self.ua,
             "Accept-Language": "zh-CN,zh;q=0.9",
             "Referer": f"{HOST}/bbs/"}
        try:
            r = creq.get(url, headers=h, impersonate="chrome124", timeout=timeout)
        except Exception as e:
            return -1, ""
        if r.status_code == 403 and b"Just a moment" in r.content:
            self.cf += 1
        return r.status_code, dec(r.content)

    # -------- 版块帖子列表 --------
    def list_fids(self, fid, pages=10):
        out = []
        for p in range(1, pages + 1):
            st, h = self.get(f"{HOST}/bbs/forum.php?mod=forumdisplay&fid={fid}&page={p}")
            if st != 200:
                print(f"   [!] 列表第 {p} 页 HTTP {st}")
                break
            rows = re.findall(
                r'id="normalthread_(\d+)".*?thread-\1-\d+-\d+\.html[^>]*>([^<]{3,80})</a>', h, re.S)
            if not rows:
                print(f"   列表第 {p} 页无新帖，停")
                break
            out += [(int(t), re.sub(r"\s+", " ", ti).strip()) for t, ti in rows]
            print(f"   列表 第 {p} 页 +{len(rows)}  累计 {len(out)}", end="\r", flush=True)
        print()
        # 去重
        seen, uniq = set(), []
        for t, ti in out:
            if t not in seen:
                seen.add(t)
                uniq.append((t, ti))
        return uniq

    # -------- 单帖 --------
    def thread(self, tid, pages=3):
        floors, title, has_hide = [], "", False
        for p in range(1, pages + 1):
            url = (f"{HOST}/bbs/thread-{tid}-1-1.html" if p == 1
                   else f"{HOST}/bbs/thread-{tid}-{p}-1.html")
            st, h = self.get(url)
            if st != 200:
                break
            if "积分不足" in h or "阅读权限" in h:
                has_hide = True
            if not title:
                m = re.search(r"<title>(.*?)</title>", h, re.S)
                if m:
                    title = re.sub(r"\s+", " ", m.group(1)).strip()
                    title = re.sub(r"\s*[-|]\s*(一亩三分地|Powered by Discuz).*$", "", title)
            authors = re.findall(r'class="xw1"[^>]*>(.*?)</a>', h, re.S)
            for i, m in enumerate(re.finditer(
                    r'id="postmessage_(\d+)"(.*?)(?=id="postmessage_|</body>|$)', h, re.S)):
                body = m.group(2)
                body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S | re.I)
                body = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</blockquote>", "\n", body, flags=re.I)
                body = re.sub(r"<[^>]+>", "", body)
                body = (body.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                        .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
                body = re.sub(r"[ \t]+", " ", body)
                body = re.sub(r"\n\s*\n+", "\n", body).strip()
                if len(body) < 3:
                    continue
                a = authors[i] if i < len(authors) else ""
                a = re.sub(r"<[^>]+>", "", a).strip()
                floors.append({"pid": int(m.group(1)), "author": a, "text": body})
            # 没有下一页就停
            if f"thread-{tid}-{p+1}-1.html" not in h:
                break
        return title, floors, has_hide


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS threads(
        tid INTEGER PRIMARY KEY, url TEXT, title TEXT, body TEXT,
        posts_n INTEGER, channel TEXT, pages INTEGER, fetched_at TEXT)""")
    have = {r[1] for r in con.execute("PRAGMA table_info(threads)")}
    for c, d in (("channel", "TEXT"), ("pages", "INTEGER"), ("url", "TEXT"),
                 ("ts", "TEXT"), ("posts_n", "INTEGER")):
        if c not in have:
            con.execute(f"ALTER TABLE threads ADD COLUMN {c} {d}")
    con.commit()
    return con


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fid", type=int, required=True)
    ap.add_argument("--pages", type=int, default=10, help="列表翻几页")
    ap.add_argument("--max-posts", type=int, default=0, help="最多抓几个帖子")
    ap.add_argument("--pages-per-post", type=int, default=3)
    ap.add_argument("--rate", type=float, default=1.5)
    a = ap.parse_args()

    cookie, ua = load_session()
    if not cookie:
        print("[!] 无 session.json，CF 会拦。先跑 s2_cf_session.py\n")

    cli = Client(cookie, ua, a.rate)
    print(f"[*] 拉 fid={a.fid} 帖子列表 ...")
    items = cli.list_fids(a.fid, a.pages)
    print(f"[+] {len(items)} 个帖子")
    if a.max_posts:
        items = items[:a.max_posts]

    out = os.path.join(DATA, f"threads_{a.fid}.jsonl")
    con = init_db()
    ok = hide_n = 0
    with open(out, "w") as f:
        for i, (tid, ti) in enumerate(items, 1):
            title, floors, has_hide = cli.thread(tid, a.pages_per_post)
            if not floors:
                print(f"  {i}/{len(items)} tid={tid} 空", end="\r", flush=True)
                continue
            body = "\n\n".join(f"[{x['author']}] {x['text']}" if x['author'] else x['text']
                               for x in floors)
            rec = {"tid": tid, "fid": a.fid, "title": title, "floors": len(floors),
                   "has_hide": has_hide, "body": body}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            con.execute(
                "INSERT OR REPLACE INTO threads(tid,url,title,body,posts_n,channel,pages,fetched_at) "
                "VALUES(?,?,?,?,?,?,?,datetime('now'))",
                (tid, f"{HOST}/bbs/thread-{tid}-1-1.html", title, body,
                 len(floors), f"fid{a.fid}", a.pages_per_post))
            con.commit()
            ok += 1
            hide_n += has_hide
            print(f"  {i}/{len(items)} ok={ok} 含hide={hide_n}  {tid} '{title[:34]}' "
                  f"楼层={len(floors)} 字数={len(body)}", end="\r", flush=True)
            if cli.cf >= 3:
                print(f"\n[!] 连续被 CF 拦，停。重跑 s2_cf_session.py")
                break
    print(f"\n[+] 完成 {ok} 帖（其中 {hide_n} 帖含权限提示）-> {out}")
    print(f"[*] 库内总数:")
    print("   ", con.execute("select count(*), sum(length(body)) from threads").fetchone())


if __name__ == "__main__":
    main()
