#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s6_archive_harvest.py — 从 archive.org 收割一亩三分地帖子，完全不碰目标站。

用法:
  python3 s6_archive_harvest.py --list                 # 只导出全部已知帖子 URL 清单
  python3 s6_archive_harvest.py --harvest --limit 200  # 抓正文入 SQLite
  python3 s6_archive_harvest.py --harvest --resume     # 断点续跑

产出:
  data/tids.txt      tid 清单
  data/1p3a.db       SQLite: threads(tid, url, ts, title, body, posts_n, fetched_at)
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
TID_FILE = os.path.join(DATA, "tids.txt")
CDX = "http://web.archive.org/cdx/search/cdx"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

os.makedirs(DATA, exist_ok=True)


def http_get(url, tries=5, timeout=45):
    """archive.org 会 429，指数退避。"""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20 * (i + 1)
                print(f"  [429] 退避 {wait}s ...", file=sys.stderr)
                time.sleep(wait)
                continue
            if i == tries - 1:
                print(f"  [!] {url[:90]} -> {e}", file=sys.stderr)
                return None
            time.sleep(3 + i * 4)
        except Exception as e:
            if i == tries - 1:
                print(f"  [!] {url[:90]} -> {e}", file=sys.stderr)
                return None
            time.sleep(3 + i * 4)


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS threads(
        tid INTEGER PRIMARY KEY,
        url TEXT,
        ts TEXT,
        title TEXT,
        body TEXT,
        posts_n INTEGER,
        fetched_at TEXT
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ts ON threads(ts)")
    con.commit()
    return con


# ---------------------------------------------------------------- CDX 清单
def cdx_pages(pattern="1point3acres.com/bbs/thread-*"):
    """CDX 的 showNumPages 拿总页数，再逐页 collapse=urlkey 拿唯一 URL。"""
    raw = http_get(f"{CDX}?url={urllib.parse.quote(pattern)}&output=json&showNumPages=true")
    numpages = 1
    if raw:
        try:
            numpages = int(json.loads(raw)[1][0])
        except Exception:
            pass
    print(f"[*] CDX 总页数: {numpages}")
    return numpages


def cdx_list(pattern="1point3acres.com/bbs/thread-*"):
    numpages = cdx_pages(pattern)
    seen = {}
    for p in range(numpages):
        url = (f"{CDX}?url={urllib.parse.quote(pattern)}&output=json"
               f"&fl=original,timestamp,statuscode&collapse=urlkey&page={p}")
        raw = http_get(url)
        if not raw:
            continue
        try:
            rows = json.loads(raw)
        except Exception:
            continue
        rows = rows[1:] if rows and rows[0] and rows[0][0] == "original" else rows
        for r in rows:
            if len(r) < 3:
                continue
            orig, ts, code = r[0], r[1], r[2]
            if code != "200":
                continue
            m = re.search(r"/thread-(\d+)-\d+-\d+\.html", orig)
            if not m:
                continue
            tid = int(m.group(1))
            # 同一个 tid 保留最新一次成功快照
            if tid not in seen or ts > seen[tid][1]:
                seen[tid] = (orig, ts)
        print(f"    页 {p+1}/{numpages}  累计唯一 tid: {len(seen)}", end="\r", flush=True)
        time.sleep(0.6)
    print()
    with open(TID_FILE, "w") as f:
        for tid in sorted(seen):
            f.write(f"{tid}\t{seen[tid][1]}\t{seen[tid][0]}\n")
    print(f"[+] 写出 {TID_FILE}: {len(seen)} 个唯一帖子")
    return seen


# ---------------------------------------------------------------- 正文抓取
def wayback_raw(orig, ts):
    """id_ 后缀拿原始响应（不注入 archive 的工具栏）。"""
    return f"http://web.archive.org/web/{ts}id_/{orig}"


def extract(html, encoding="gbk"):
    """从 Discuz viewthread 页面抽标题 + 各层楼正文。"""
    if not html:
        return None, None, 0
    title = ""
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        title = re.sub(r"\s*-\s*一亩三分地.*$", "", title)
        title = re.sub(r"\s*-\s*Powered by Discuz!.*$", "", title, flags=re.I)
    bodies = []
    # Discuz X3: <td class="t_f" id="postmessage_NNN">...</td>
    for m in re.finditer(r'id="postmessage_\d+"[^>]*>(.*?)</td>', html, re.S | re.I):
        txt = m.group(1)
        txt = re.sub(r"<script.*?</script>", "", txt, flags=re.S | re.I)
        txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
        txt = re.sub(r"</p>|</div>|</blockquote>", "\n", txt, flags=re.I)
        txt = re.sub(r"<[^>]+>", "", txt)
        txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&")
                  .replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&quot;", '"').replace("&#39;", "'"))
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
        if txt:
            bodies.append(txt)
    return title, "\n\n---- 楼层 ----\n\n".join(bodies), len(bodies)


def harvest(limit=None, resume=False, encoding="gbk"):
    con = init_db()
    if not os.path.exists(TID_FILE):
        print("[*] 没有 tids.txt，先跑 --list")
        return
    todo = []
    with open(TID_FILE) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            todo.append((int(parts[0]), parts[1], parts[2]))
    if resume:
        done = {r[0] for r in con.execute("SELECT tid FROM threads WHERE body IS NOT NULL AND body != ''")}
        todo = [t for t in todo if t[0] not in done]
        print(f"[*] 断点续跑，剩余 {len(todo)}")
    if limit:
        todo = todo[:limit]

    ok = fail = 0
    for i, (tid, ts, orig) in enumerate(todo, 1):
        raw = http_get(wayback_raw(orig, ts))
        if raw is None:
            fail += 1
            continue
        html = raw.decode(encoding, "ignore")
        if "postmessage_" not in html:
            html = raw.decode("utf-8", "ignore")
        title, body, n = extract(html, encoding)
        if not body:
            fail += 1
            continue
        con.execute(
            "INSERT OR REPLACE INTO threads(tid,url,ts,title,body,posts_n,fetched_at) "
            "VALUES(?,?,?,?,?,?,datetime('now'))",
            (tid, orig, ts, title, body, n))
        con.commit()
        ok += 1
        if i % 20 == 0:
            print(f"    {i}/{len(todo)}  ok={ok} fail={fail}  当前 tid={tid} 楼层={n}", end="\r", flush=True)
        time.sleep(1.5)  # archive.org 别打太狠，429 了就往上调
    print(f"\n[+] 完成: ok={ok} fail={fail}  库={DB}")
    dump_sample(con)


def dump_sample(con=None, n=3):
    con = con or init_db()
    rows = con.execute(
        "SELECT tid,title,posts_n,length(body) FROM threads ORDER BY length(body) DESC LIMIT ?", (n,)
    ).fetchall()
    print("\n=== 最长正文抽样 ===")
    for tid, title, pn, ln in rows:
        print(f"  tid={tid}  楼层={pn}  正文={ln}字  {title[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--harvest", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--encoding", default="gbk")
    a = ap.parse_args()
    if a.list:
        cdx_list()
    if a.harvest:
        harvest(a.limit, a.resume, a.encoding)
    if not a.list and not a.harvest:
        ap.print_help()


if __name__ == "__main__":
    main()
