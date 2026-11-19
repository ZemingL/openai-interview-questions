#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s4_edge_probe.py — Discuz 边缘通道探测。

同一个 tid，把 8 条输出通道全打一遍，比正文长度。
谁吐得多用谁。这是花 5 分钟就能省掉 50 天攒积分的一步。

用法:
  python3 s4_edge_probe.py --tid 4428
  python3 s4_edge_probe.py --tid 4428 --tid 1000016
  python3 s4_edge_probe.py --from-file data/tids.txt --n 5

依赖 cookie（多数通道游客可达，带登录态命中率更高）:
  data/session.json  {"cookies": "...", "ua": "..."}   ← s2 产出，可缺省
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
    import requests as creq
    HAVE_CFFI = False

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SESS = os.path.join(DATA, "session.json")

HOST = "https://www.1point3acres.com"
UA_DEFAULT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# 8 条通道：名称 -> (url, UA 类型, 备注)
CHANNELS = {
    "01_正常页":      ("{H}/bbs/thread-{T}-1-1.html", "pc", "基准：Discuz 标准 viewthread"),
    "02_打印页":      ("{H}/bbs/forum.php?mod=viewthread&action=printable&tid={T}", "pc",
                       "forum_viewthread.php 的 printable 分支，站方在 robots 里 disallow"),
    "03_Archiver":    ("{H}/bbs/archiver/tid-{T}.html", "pc",
                       "纯文字版，为搜索引擎做的，hide 判断常缺失"),
    "04_Archiver_dyn":("{H}/bbs/archiver/?tid-{T}.html", "pc", "archiver 另一种路由写法"),
    "05_手机版":      ("{H}/bbs/forum.php?mod=viewthread&tid={T}&mobile=yes", "mobile",
                       "mobile 插件模板，另一套权限逻辑，robots 未禁"),
    "06_RSS":         ("{H}/bbs/forum.php?mod=rss&tid={T}", "pc", "摘要输出口"),
    "07_导读新帖":    ("{H}/bbs/forum.php?mod=guide&view=newthread", "pc",
                       "列表页直接吐 message 前 N 字，通常在 discuzcode 之前截取"),
    "08_搜索摘要":    ("{H}/bbs/search.php?mod=forum&srchtxt={K}&searchsubmit=yes", "pc",
                       "检索索引存原文，摘要常带 hide 内容"),
}


def load_session():
    if os.path.exists(SESS):
        try:
            s = json.load(open(SESS))
            return s.get("cookies", ""), s.get("ua") or UA_DEFAULT
        except Exception:
            pass
    return "", UA_DEFAULT


def fetch(url, ua, cookie, timeout=25):
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if cookie:
        headers["Cookie"] = cookie
    try:
        if HAVE_CFFI:
            r = creq.get(url, headers=headers, impersonate="chrome124",
                         timeout=timeout, allow_redirects=True)
        else:
            import requests
            r = creq.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return r.status_code, r.content
    except Exception as e:
        return -1, str(e).encode()


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


def body_text(html):
    """抽所有可能承载正文的容器，返回去标签纯文本。"""
    chunks = []
    # 通用：从 postmessage_XX 到下一个楼层 / 页脚，容纳 PC 的 </td> 和 mobile 的 </div>
    for m in re.finditer(
            r'id="postmessage_\d+"(.*?)(?=id="postmessage_|<div class="footer|<div id="footer|</body>|$)',
            html, re.S | re.I):
        chunks.append(m.group(1))
    for pat in (r'class="t_f[^"]*"[^>]*>(.*?)</td>',
                r'<div class="pcbcontent[^"]*"[^>]*>(.*?)</div>',
                r'<pre[^>]*>(.*?)</pre>',
                r'<blockquote[^>]*>(.*?)</blockquote>'):
        for m in re.finditer(pat, html, re.S | re.I):
            chunks.append(m.group(1))
    out = []
    for c in chunks:
        t = re.sub(r"<script.*?</script>|<style.*?</style>", "", c, flags=re.S | re.I)
        t = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", t, flags=re.I)
        t = re.sub(r"<[^>]+>", " ", t)
        t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
              .replace("&gt;", ">").replace("&quot;", '"'))
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n\s*\n+", "\n", t).strip()
        if len(t) > 10:
            out.append(t)

    # 兜底：mobile 模板没有 postmessage 容器，整页去标签再剪掉导航/页脚
    if sum(len(x) for x in out) < 200:
        t = re.sub(r"<script.*?</script>|<style.*?</style>|<head>.*?</head>", "", html, flags=re.S | re.I)
        t = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</td>", "\n", t, flags=re.I)
        t = re.sub(r"<[^>]+>", " ", t)
        t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
              .replace("&gt;", ">").replace("&quot;", '"').replace("&#128273;", ""))
        t = re.sub(r"[ \t]+", " ", t)
        keep = []
        for ln in t.split("\n"):
            ln = ln.strip()
            if len(ln) < 2:
                continue
            if any(j in ln for j in ("黑五价提前开抢", "体验新版", "常见问题", "联系客服",
                                     "does not represent", "触屏版", "客户端", "商务洽谈",
                                     "Copyright", "See Terms", "打开一亩三分地APP")):
                continue
            keep.append(ln)
        t = "\n".join(keep).strip()
        if len(t) > 200:
            out = [t]
    return "\n".join(out)


def cf_blocked(status, html):
    return status == 403 and ("Just a moment" in html or "cf-mitigated" in html)


def probe_one(tid, cookie, ua_pc):
    print(f"\n{'='*70}\n tid = {tid}\n{'='*70}")
    results = []
    for name, (tpl, kind, note) in CHANNELS.items():
        url = tpl.format(H=HOST, T=tid, K="offer")
        ua = UA_MOBILE if kind == "mobile" else ua_pc
        st, raw = fetch(url, ua, cookie)
        html = decode(raw)
        if cf_blocked(st, html):
            results.append((name, st, 0, "CF 拦截", note))
            print(f"  {name:<14} {st}  CF拦截")
            time.sleep(1)
            continue
        txt = body_text(html)
        results.append((name, st, len(txt), txt[:120], note))
        flag = "✓" if len(txt) > 50 else "·"
        print(f"  {flag} {name:<14} {st}  正文 {len(txt):>6} 字   {note[:34]}")
        if len(txt) > 50:
            print(f"      预览: {txt[:110]}")
        time.sleep(1.2)

    ok = [r for r in results if isinstance(r[2], int) and r[2] > 0]
    ok.sort(key=lambda x: -x[2])
    print(f"\n  >>> tid={tid} 命中通道排序:")
    for name, st, n, prev, _ in ok[:4]:
        print(f"      {name:<14} {n} 字")
    if not ok:
        print("      （全部无正文：要么 CF 没过，要么这个 tid 本身没内容）")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tid", action="append", default=[])
    ap.add_argument("--from-file")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()

    cookie, ua = load_session()
    if not cookie:
        print("[!] 没有 data/session.json，游客身份试。命中率低就先去跑 s2_cf_session.py\n")

    tids = [int(x) for x in a.tid]
    if a.from_file and os.path.exists(a.from_file):
        for i, line in enumerate(open(a.from_file)):
            if i >= a.n:
                break
            tids.append(int(line.split("\t")[0]))
    if not tids:
        tids = [4428, 1000016]

    for tid in tids:
        probe_one(tid, cookie, ua)


if __name__ == "__main__":
    main()
