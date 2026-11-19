#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s11_openai_hunt.py — 全量定位某个公司的面经帖，然后抓正文+楼层。

一亩三分地面经版的每个帖子行里有公司标记：
    <u><b><font color="green">码农类General</font><font color="#00B2E8">全职</font></b>
    @<b><font color="#FF6600">openai</font></b></u>
翻版块列表页 → 抓 tid + 标题 + 公司 → 本地筛 → 再逐帖抓正文。

用法:
  python3 s11_openai_hunt.py --scan --fid 145 --pages 1200     # 只扫列表
  python3 s11_openai_hunt.py --scan --fid 259 --pages 400
  python3 s11_openai_hunt.py --scan --fid 28  --pages 400
  python3 s11_openai_hunt.py --fetch --company openai          # 抓正文
  python3 s11_openai_hunt.py --fetch --company openai --pages-per-post 3
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
    sys.exit("pip3 install curl_cffi")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
SESS = os.path.join(DATA, "session.json")
INDEX = os.path.join(DATA, "thread_index.jsonl")
HOST = "https://www.1point3acres.com"


def load_sess():
    if os.path.exists(SESS):
        s = json.load(open(SESS))
        return {"Cookie": s.get("cookies", ""), "User-Agent": s.get("ua") or
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9"}
    return {"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"}


def dec(b):
    for e in ("gb18030", "gbk", "utf-8"):
        try:
            return b.decode(e)
        except Exception:
            pass
    return b.decode("utf-8", "ignore")


class C:
    def __init__(self, rate=1.4):
        self.h = load_sess()
        self.iv = 1.0 / rate
        self.last = 0.0
        self.cf = 0

    def get(self, url):
        dt = time.time() - self.last
        if dt < self.iv:
            time.sleep(self.iv - dt + random.uniform(0, 0.2))
        self.last = time.time()
        try:
            r = creq.get(url, headers=self.h, impersonate="chrome124", timeout=30)
        except Exception:
            return -1, ""
        if r.status_code == 403:
            self.cf += 1
        return r.status_code, dec(r.content)

    # ---- 列表页解析 ----
    @staticmethod
    def rows(h):
        """返回 [(tid, title, type, jobtype, company, tagline)]"""
        out = []
        for m in re.finditer(r'id="normalthread_(\d+)"(.*?)(?=id="normalthread_|</tbody>\s*<tr>|$)', h, re.S):
            tid = int(m.group(1))
            blk = m.group(2)
            t = re.search(rf'thread-{tid}-\d+-\d+\.html"[^>]*class="[^"]*"[^>]*>([^<]{{2,120}})</a>', blk)
            if not t:
                t = re.search(rf'thread-{tid}-\d+-\d+\.html[^>]*>([^<]{{2,120}})</a>', blk)
            title = re.sub(r"\s+", " ", t.group(1)).strip() if t else ""
            ty = re.search(r'<font color="green">([^<]{1,20})</font>', blk)
            jt = re.search(r'<font color="#00B2E8">([^<]{1,20})</font>', blk)
            co = re.search(r'@<b><font color="#FF6600">([^<]{1,24})</font>', blk)
            info = re.sub(r"<[^>]+>", " ", blk)
            info = re.sub(r"\s+", " ", info).strip()[:160]
            out.append((tid, title, ty.group(1) if ty else "",
                        jt.group(1) if jt else "", co.group(1) if co else "", info))
        return out

    # ---- 单帖正文 ----
    def thread(self, tid, pages=3):
        title, floors, hide = "", [], False
        for p in range(1, pages + 1):
            url = (f"{HOST}/bbs/thread-{tid}-1-1.html" if p == 1
                   else f"{HOST}/bbs/thread-{tid}-{p}-1.html")
            st, h = self.get(url)
            if st != 200:
                break
            if "积分不足" in h or "阅读权限" in h:
                hide = True
            if not title:
                m = re.search(r"<title>(.*?)</title>", h, re.S)
                if m:
                    title = re.sub(r"\s+", " ", m.group(1)).strip()
                    title = re.sub(r"\s*[-|]\s*(一亩三分地|Powered by Discuz).*$", "", title)
            authors = re.findall(r'class="xw1"[^>]*>(.*?)</a>', h, re.S)
            for i, m in enumerate(re.finditer(
                    r'id="postmessage_(\d+)"(.*?)(?=id="postmessage_|</body>|$)', h, re.S)):
                b = m.group(2)
                b = re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S | re.I)
                b = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</blockquote>", "\n", b, flags=re.I)
                b = re.sub(r"<[^>]+>", "", b)
                b = (b.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                      .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
                b = re.sub(r"[ \t]+", " ", b)
                b = re.sub(r"\n\s*\n+", "\n", b).strip()
                if len(b) < 3:
                    continue
                a = authors[i] if i < len(authors) else ""
                floors.append({"pid": int(m.group(1)),
                               "author": re.sub(r"<[^>]+>", "", a).strip(), "text": b})
            if f"thread-{tid}-{p+1}-1.html" not in h:
                break
        return title, floors, hide


def scan(cli, fid, pages, start=1):
    total_new = 0
    with open(INDEX, "a") as f:
        for p in range(start, start + pages):
            st, h = cli.get(f"{HOST}/bbs/forum-{fid}-{p}.html")
            if st != 200:
                print(f"\n  page={p} HTTP {st} -> 停")
                break
            rs = cli.rows(h)
            if not rs:
                print(f"\n  page={p} 空 -> 到底了（共 {p-1} 页）")
                break
            for tid, title, ty, jt, co, info in rs:
                f.write(json.dumps({"tid": tid, "fid": fid, "title": title, "type": ty,
                                    "job": jt, "company": co, "info": info},
                                   ensure_ascii=False) + "\n")
            total_new += len(rs)
            cos = [r[4] for r in rs if r[4]]
            print(f"  fid={fid} page={p}  +{len(rs)}  累计 {total_new}  "
                  f"本页公司 {sorted(set(cos))[:6]}", end="\r", flush=True)
            if cli.cf >= 3:
                print("\n[!] CF 连续拦截，停")
                break
    print(f"\n[+] fid={fid} 扫完，写 {INDEX}")


def load_index(company=None):
    if not os.path.exists(INDEX):
        return []
    seen, out = set(), []
    for line in open(INDEX):
        r = json.loads(line)
        if r["tid"] in seen:
            continue
        seen.add(r["tid"])
        if company and (r.get("company") or "").lower() != company.lower():
            continue
        out.append(r)
    return out


def fetch(cli, company, pages_per_post=3, limit=0):
    items = load_index(company)
    allidx = load_index()
    print(f"[*] 索引 {len(allidx)} 条，{company} 命中 {len(items)} 条")
    if not items:
        print("    没命中。先 --scan 扫列表，或检查公司标记大小写")
        return
    if limit:
        items = items[:limit]

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

    done = {r[0] for r in con.execute("SELECT tid FROM threads WHERE body != ''")}
    items = [x for x in items if x["tid"] not in done]
    print(f"    待抓 {len(items)}")

    out = os.path.join(DATA, f"threads_{company}.jsonl")
    ok = hide_n = 0
    with open(out, "a") as f:
        for i, r in enumerate(items, 1):
            title, floors, hide = cli.thread(r["tid"], pages_per_post)
            if not floors:
                print(f"  {i}/{len(items)} {r['tid']} 空", end="\r", flush=True)
                continue
            body = "\n\n".join(f"[{x['author']}] {x['text']}" if x["author"] else x["text"]
                               for x in floors)
            f.write(json.dumps({"tid": r["tid"], "list_title": r["title"], "title": title,
                                "company": r.get("company"), "has_hide": hide,
                                "floors": len(floors), "body": body}, ensure_ascii=False) + "\n")
            f.flush()
            con.execute(
                "INSERT OR REPLACE INTO threads(tid,url,title,body,posts_n,channel,pages,fetched_at) "
                "VALUES(?,?,?,?,?,?,?,datetime('now'))",
                (r["tid"], f"{HOST}/bbs/thread-{r['tid']}-1-1.html", title or r["title"],
                 body, len(floors), f"{company}", pages_per_post))
            con.commit()
            ok += 1
            hide_n += hide
            print(f"  {i}/{len(items)} ok={ok} 含hide={hide_n}  {r['tid']} "
                  f"楼层={len(floors)} 字数={len(body)}  {(title or r['title'])[:34]}",
                  end="\r", flush=True)
            if cli.cf >= 3:
                print("\n[!] CF 连续拦截，停")
                break
    print(f"\n[+] {ok} 帖 -> {out}（其中 {hide_n} 帖含权限提示）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--fid", type=int, default=145)
    ap.add_argument("--pages", type=int, default=100)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--company", default="openai")
    ap.add_argument("--pages-per-post", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rate", type=float, default=1.4)
    a = ap.parse_args()
    cli = C(a.rate)
    if a.scan:
        scan(cli, a.fid, a.pages, a.start)
    if a.fetch:
        fetch(cli, a.company, a.pages_per_post, a.limit)


if __name__ == "__main__":
    main()
