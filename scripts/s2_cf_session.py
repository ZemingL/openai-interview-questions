#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s2_cf_session.py — 用真实浏览器过 Cloudflare Managed Challenge，导出可复用的登录态。

一亩三分地 /bbs/ 全站 CF 前置（`cf-mitigated: challenge`）。
curl / 普通 requests 一律 403 Just a moment...。
这里用 patchright/playwright 起一个真 Chromium，过掉挑战后把 cf_clearance 和 UA 一起存下来。

关键约束（别踩坑）：
  cf_clearance 绑 IP + User-Agent + TLS 指纹。三样对齐才能复用。
  · 换代理 → cookie 立刻失效，必须在新出口 IP 上重新过
  · 换 UA → 失效
  · 有效期约 30 分钟 ~ 24 小时，到期重新跑这个脚本

用法:
  pip install patchright && python -m patchright install chromium
  python3 s2_cf_session.py                 # 游客态，只为过 CF
  python3 s2_cf_session.py --login         # 有头模式，手动登录一次，把登录态一起存下来
  python3 s2_cf_session.py --check         # 验证现有 session.json 还能用

产出: data/session.json  {"cookies": "...", "ua": "...", "saved_at": "..."}
"""
import argparse
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
SESS = os.path.join(DATA, "session.json")
os.makedirs(DATA, exist_ok=True)

PROBE = "https://www.1point3acres.com/bbs/thread-4428-1-1.html"


def get_pw():
    """优先 patchright（去掉 CDP 指纹），退 playwright。"""
    try:
        from patchright.sync_api import sync_playwright
        print("[*] 用 patchright")
        return sync_playwright
    except ImportError:
        from playwright.sync_api import sync_playwright
        print("[*] 用 playwright（建议装 patchright 提升通过率）")
        return sync_playwright


def wait_challenge(page, timeout=60):
    """等 'Just a moment...' 消失。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            title = page.title()
        except Exception:
            title = ""
        if "just a moment" not in title.lower() and "attention required" not in title.lower():
            return True
        page.wait_for_timeout(1500)
    return False


def run(login=False):
    sync_playwright = get_pw()
    with sync_playwright() as p:
        # 实测：headless Chromium 一律过不去（title 停在"请稍候…"、cookies 为空）。
        # 必须 真 Chrome + 有头。macOS/Windows 上都装得到，别用 headless。
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled",
                      "--start-maximized"],
            )
            print("[*] 用本机 Google Chrome（有头）")
        except Exception as e:
            print(f"[!] 找不到本机 Chrome（{e}），退回 playwright chromium 有头")
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled",
                      "--start-maximized"],
            )
        ctx = browser.new_context(
            locale="zh-CN",
            timezone_id="America/Los_Angeles",
            viewport={"width": 1440, "height": 900},
        )
        # 抹掉 navigator.webdriver
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
            "Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh','en']});"
        )
        page = ctx.new_page()
        print(f"[*] 打开 {PROBE}")
        page.goto(PROBE, wait_until="domcontentloaded", timeout=60000)

        ok = wait_challenge(page)
        print(f"[*] 挑战结果: {'通过' if ok else '未通过（可能是 Turnstile 交互验证）'}")

        if login:
            print("[*] 有头模式：现在手动登录，登录完成后回终端按回车")
            page.goto("https://www.1point3acres.com/bbs/member.php?mod=logging&action=login",
                      wait_until="domcontentloaded")
            input("    登录好了就按回车 >>> ")
            page.goto(PROBE, wait_until="domcontentloaded")
            wait_challenge(page)

        html = page.content()
        if "postmessage" not in html:
            print("[!] 页面里没有 postmessage，可能没登录或还没过挑战")
            print(f"    title={page.title()!r}  len={len(html)}")
        else:
            print("[+] 拿到正文渲染页")

        cookies = ctx.cookies()
        ck = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        ua = page.evaluate("navigator.userAgent")
        names = [c["name"] for c in cookies]
        print(f"[*] cookie 数: {len(cookies)}  含 cf_clearance: {'cf_clearance' in names}")
        print(f"[*] UA: {ua}")

        json.dump({"cookies": ck, "ua": ua, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                  open(SESS, "w"), ensure_ascii=False, indent=1)
        print(f"[+] 写出 {SESS}")
        print("    注意：这个 cookie 绑 IP，换网络/换代理要重新跑。")

        if login:
            input("    确认后按回车关闭浏览器 >>> ")
        browser.close()


def check():
    if not os.path.exists(SESS):
        print("[!] 没有 session.json，先跑不带 --check 的")
        return
    s = json.load(open(SESS))
    print(f"[*] saved_at = {s.get('saved_at')}")
    try:
        from curl_cffi import requests as creq
        r = creq.get(PROBE, impersonate="chrome124",
                     headers={"Cookie": s["cookies"], "User-Agent": s["ua"]}, timeout=25)
    except ImportError:
        import requests
        r = requests.get(PROBE, headers={"Cookie": s["cookies"], "User-Agent": s["ua"]}, timeout=25)
    hit = "postmessage" in r.text or "t_f" in r.text
    cf = "Just a moment" in r.text
    print(f"[*] HTTP {r.status_code}  bytes={len(r.content)}  CF挑战={cf}  有正文={hit}")
    if hit:
        print("[+] 还能用，直接去跑 s3_crawl.py")
    elif cf:
        print("[!] 挑战又来了，重跑本脚本（不带 --check）")
    else:
        print("[!] 没正文：可能掉登录了，用 --login 重新登")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check()
    else:
        run(a.login)


if __name__ == "__main__":
    main()
