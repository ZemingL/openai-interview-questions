#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s7_rate_farm.py — 用多账号给主号刷大米，把总积分顶到 500（= VIP 阅读权限上限）。

原理（官方 FAQ 原话）：
  「给别人加分不消耗自己大米」—— Discuz 的评分动作是凭空造分。
  主号发一个靶帖，小号轮流给靶帖评分 → 主号大米涨 → 总积分涨 → hide 全部解锁。

实测拿到的接口参数（tid=1196469 帖子页）：
  formhash = 082ffd16                     ← name="formhash" value="..."
  评分提交 = forum.php?mod=misc&action=rate&tid=TID&pid=PID&ratehash=HASH
  查评分   = forum.php?mod=misc&action=viewratings&tid=TID&pid=PID
  积分类型 = 1|大米 2|萝卜 3|人参 4|水井 5|蓝莓

用法:
  # 1. 准备 accounts.json（每个小号一份 cookie + formhash）
  # 2. 主号发一个帖，拿 tid 和首楼 pid
  python3 s7_rate_farm.py --tid 1196469 --pid 21266245 --score 1
  python3 s7_rate_farm.py --tid X --pid Y --score 1 --dry-run   # 只看不提交

accounts.json 格式（每个小号一条）：
[
  {"name":"a1", "cookies":"cf_clearance=...; 4Oaf_61d6_saltkey=...; ...", "ua":"..."},
  {"name":"a2", "cookies":"...", "ua":"..."}
]

小号的 cookie 怎么拿：用浏览器登录一次，F12 → Network → 任意请求 → 复制 Cookie 整行。
或者跑 s2_cf_session.py --login 换号登录，把 data/session.json 另存一份。
"""
import argparse
import json
import os
import re
import sys
import time

try:
    from curl_cffi import requests as creq
except ImportError:
    sys.exit("先 pip3 install curl_cffi")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
ACC = os.path.join(DATA, "accounts.json")
HOST = "https://www.1point3acres.com"

SCORE_FIELD = {1: "score1", 2: "score2", 3: "score3"}


def dec(b):
    for e in ("gb18030", "gbk", "utf-8"):
        try:
            return b.decode(e)
        except Exception:
            pass
    return b.decode("utf-8", "ignore")


def load_accounts():
    if not os.path.exists(ACC):
        sys.exit(f"没有 {ACC}，先按文件头注释里的格式建一份")
    accs = json.load(open(ACC))
    print(f"[*] 载入 {len(accs)} 个小号")
    return accs


def sess(acc, timeout=25):
    h = {"Cookie": acc["cookies"], "User-Agent": acc.get("ua") or
         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
         "Accept-Language": "zh-CN,zh;q=0.9"}
    try:
        r = creq.get(f"{HOST}/bbs/thread-{acc['_tid']}-1-1.html",
                     headers=h, impersonate="chrome124", timeout=timeout)
        return r
    except Exception as e:
        print(f"  [!] {acc['name']} 请求失败: {e}")
        return None


def grab_formhash(html):
    m = re.search(r'name="formhash"\s+value="([a-zA-Z0-9]+)"', html)
    return m.group(1) if m else None


def grab_ratehash(html, tid, pid):
    """评分按钮里的 ratehash。没有就说明这个号没评分权限。"""
    for pat in (rf'action=rate&amp;tid={tid}&amp;pid={pid}&amp;ratehash=([a-zA-Z0-9]+)',
                rf'action=rate&tid={tid}&pid={pid}&ratehash=([a-zA-Z0-9]+)',
                r'ratehash=([a-zA-Z0-9]{8,})'):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def whoami(html):
    m = re.search(r'欢迎您回来[^<]*<[^>]*>([^<]{2,20})</a>', html)
    if m:
        return m.group(1)
    m = re.search(r'home\.php\?mod=space&amp;uid=(\d+)', html)
    return f"uid={m.group(1)}" if m else "?"


def rate(acc, tid, pid, score, points, reason, dry=False):
    acc["_tid"] = tid
    r = sess(acc)
    if r is None or r.status_code != 200:
        return False, f"HTTP {getattr(r,'status_code','-')}"
    html = dec(r.content)
    if "积分不足" not in html and "postmessage" not in html:
        return False, "页面异常（cookie 掉了 / CF 拦了）"

    formhash = grab_formhash(html)
    ratehash = grab_ratehash(html, tid, pid)
    user = whoami(html)
    if not formhash:
        return False, "没拿到 formhash"
    if not ratehash:
        return False, f"{user} 没有评分入口（用户组等级不够 / 不能给自己评分）"

    if dry:
        return True, f"{user} formhash={formhash} ratehash={ratehash} （dry-run 未提交）"

    url = f"{HOST}/bbs/forum.php?mod=misc&action=rate&tid={tid}&pid={pid}&ratehash={ratehash}"
    payload = {
        "formhash": formhash,
        "score" + str(score): str(points),
        "reason": reason,
        "ratesubmit": "true",
    }
    h = {"Cookie": acc["cookies"], "User-Agent": acc.get("ua") or
         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
         "Referer": f"{HOST}/bbs/thread-{tid}-1-1.html",
         "Content-Type": "application/x-www-form-urlencoded"}
    try:
        rr = creq.post(url, headers=h, data=payload, impersonate="chrome124", timeout=25)
    except Exception as e:
        return False, f"提交异常: {e}"
    body = dec(rr.content)
    if "感谢" in body or "成功" in body or rr.status_code in (200, 302):
        if "抱歉" in body or "不能" in body or "已经" in body:
            return False, f"被拒: {' '.join(re.sub(r'<[^>]+>',' ',body).split())[:80]}"
        return True, f"{user} +{points}"
    return False, f"HTTP {rr.status_code}"


def check_credit(cookies, ua=None):
    h = {"Cookie": cookies, "User-Agent": ua or
         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    for u in (f"{HOST}/home.php?mod=spacecp&ac=credit&showcredit=1",
              f"{HOST}/bbs/home.php?mod=spacecp&ac=credit&showcredit=1"):
        try:
            r = creq.get(u, headers=h, impersonate="chrome124", timeout=25)
            t = dec(r.content)
            t2 = re.sub(r"<[^>]+>", " ", t)
            t2 = " ".join(t2.split())
            m = re.search(r"大米[^\d]{0,8}(\d+)", t2)
            if m:
                return int(m.group(1)), t2[:200]
        except Exception:
            continue
    return None, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tid", type=int, required=True, help="主号的靶帖 tid")
    ap.add_argument("--pid", type=int, required=True, help="该帖首楼 pid")
    ap.add_argument("--score", type=int, default=1, help="积分类型：1=大米（默认）")
    ap.add_argument("--points", type=int, default=0, help="每次加多少分，0=用小号默认上限")
    ap.add_argument("--reason", default="感谢分享，很有帮助")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=8.0, help="两个小号间隔秒数（别太快）")
    a = ap.parse_args()

    accs = load_accounts()
    ok = fail = 0
    for i, acc in enumerate(accs, 1):
        pts = a.points or 10
        good, msg = rate(acc, a.tid, a.pid, a.score, pts, a.reason, a.dry_run)
        flag = "✓" if good else "✗"
        print(f"  [{i}/{len(accs)}] {flag} {acc['name']:<12} {msg}")
        ok += good
        fail += (not good)
        if i < len(accs):
            time.sleep(a.sleep)

    print(f"\n[+] 成功 {ok} / 失败 {fail}")
    print("[*] 去积分页核对大米到账：")
    print(f"    {HOST}/home.php?mod=spacecp&ac=credit&showcredit=1")


if __name__ == "__main__":
    main()
