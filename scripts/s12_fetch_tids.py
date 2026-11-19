#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s12_fetch_tids.py — 按 tid 清单批量抓帖子（追加写，不覆盖）。"""
import json, sqlite3, sys, importlib.util, os
spec = importlib.util.spec_from_file_location("s11", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s11_openai_hunt.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data/openai_missing.json")
tag = sys.argv[2] if len(sys.argv) > 2 else "openai"
rate = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
pages = int(sys.argv[4]) if len(sys.argv) > 4 else 3

items = json.load(open(src))
tids = sorted((int(k) for k in items), reverse=True)
con = sqlite3.connect(os.path.join(BASE, "data/1p3a.db"))
con.execute("""CREATE TABLE IF NOT EXISTS threads(tid INTEGER PRIMARY KEY,url TEXT,title TEXT,body TEXT,
  posts_n INTEGER,channel TEXT,pages INTEGER,fetched_at TEXT)""")
have = {r[1] for r in con.execute("PRAGMA table_info(threads)")}
for c, d in (("channel","TEXT"),("pages","INTEGER"),("url","TEXT"),("ts","TEXT"),("posts_n","INTEGER")):
    if c not in have: con.execute(f"ALTER TABLE threads ADD COLUMN {c} {d}")
con.commit()
done = {r[0] for r in con.execute("SELECT tid FROM threads WHERE body != ''")}
tids = [t for t in tids if t not in done]
print(f"[*] 待抓 {len(tids)}")
cli = m.C(rate); ok = hide_n = 0
out = os.path.join(BASE, f"data/threads_{tag}.jsonl")
with open(out, "a") as f:
    for i, tid in enumerate(tids, 1):
        title, floors, hide = cli.thread(tid, pages)
        if not floors:
            print(f"  {i}/{len(tids)} {tid} 空", end="\r", flush=True); continue
        body = "\n\n".join(f"[{x['author']}] {x['text']}" if x["author"] else x["text"] for x in floors)
        rec = items.get(str(tid), {})
        f.write(json.dumps({"tid": tid, "title": title, "list_title": rec.get("title"),
                            "company": rec.get("company") or tag, "fid": rec.get("fid"),
                            "has_hide": hide, "floors": len(floors), "body": body}, ensure_ascii=False) + "\n")
        f.flush()
        con.execute("INSERT OR REPLACE INTO threads(tid,url,title,body,posts_n,channel,pages,fetched_at) "
                    "VALUES(?,?,?,?,?,?,?,datetime('now'))",
                    (tid, f"https://www.1point3acres.com/bbs/thread-{tid}-1-1.html", title or rec.get("title"),
                     body, len(floors), tag, pages))
        con.commit(); ok += 1; hide_n += hide
        print(f"  {i}/{len(tids)} ok={ok} hide={hide_n} {tid} 楼{len(floors)} 字{len(body)} "
              f"{(title or '')[:36]}", end="\r", flush=True)
        if cli.cf >= 3:
            print("\n[!] CF 拦截，停"); break
print(f"\n[+] {ok} 帖 / 含hide {hide_n} -> {out}")
