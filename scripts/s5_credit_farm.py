#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s5_credit_farm.py — 免费攒大米。（签到 +1/天，每日答题 +1/天）

一亩三分地的积分公式：总积分 = 大米 + 小米/20 + 学分×50 + 萝卜/20 + 水井
免费来源里，能自动化的是这两项 2 米/天。剩下的大头靠一次性动作（见 README 路线 A）。

为什么用浏览器而不是纯 HTTP：
  签到和答题都绑微信、带验证码/风控。harryhare 那套是硬打 + 2captcha；
  这里走"真实 Chrome 里点按钮"，用你自己的登录态，不需要第三方打码。

用法:
  pip install patchright && python -m patchright install chromium
  python3 s5_credit_farm.py --login        # 第一次：有头登录一次，存 storage_state
  python3 s5_credit_farm.py                # 之后：无头跑签到 + 答题
  python3 s5_credit_farm.py --repeat 3     # 答题答错会倒扣，默认只敢试 1 次

定时（每天洛杉矶时间 8:15）:
  15 8 * * * cd /path/to/1p3a-free && python3 scripts/s5_credit_farm.py >> data/farm.log 2>&1

产出: data/browser_state.json, data/farm.log
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
STATE = os.path.join(DATA, "browser_state.json")
QA_CACHE = os.path.join(DATA, "qa.json")
os.makedirs(DATA, exist_ok=True)

HOST = "https://www.1point3acres.com"
SIGN_URL = f"{HOST}/bbs/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=0&inajax=0"
CREDIT_URL = f"{HOST}/home.php?mod=spacecp&ac=credit&showcredit=1"
TASK_URL = f"{HOST}/bbs/"
QA_SRC = "https://raw.githubusercontent.com/eagleoflqj/p1a3_script/master/QA.js"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(os.path.join(DATA, "farm.log"), "a") as f:
        f.write(line + "\n")


def get_pw():
    try:
        from patchright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        from playwright.sync_api import sync_playwright
        return sync_playwright


def load_qa():
    """题库：eagleoflqj/p1a3_script 的 QA.js，194 题。缓存到本地。"""
    if os.path.exists(QA_CACHE):
        try:
            return json.load(open(QA_CACHE))
        except Exception:
            pass
    try:
        raw = urllib.request.urlopen(QA_SRC, timeout=25).read().decode("utf-8", "ignore")
        pairs = dict(re.findall(r"'([^']{6,200})'\s*:\s*'([^']*)'", raw))
        if pairs:
            json.dump(pairs, open(QA_CACHE, "w"), ensure_ascii=False, indent=1)
            log(f"题库已缓存 {len(pairs)} 题 -> {QA_CACHE}")
        return pairs
    except Exception as e:
        log(f"[!] 拉题库失败: {e}")
        return {}


def norm(s):
    return re.sub(r"[\s，,。.？?！!、：:；;《》“”\"'（）()]+", "", s or "")


def pick_answer(question, options, qa):
    """1) 题库精确命中 2) 归一化命中 3) 选项包含答案 4) 放弃"""
    if not qa:
        return None
    if question in qa:
        return qa[question]
    nq = norm(question)
    for q, a in qa.items():
        if norm(q) == nq:
            return a
    # 模糊：问题互相包含
    for q, a in qa.items():
        if len(nq) > 8 and (nq in norm(q) or norm(q) in nq):
            return a
    return None


def match_option(answer, options):
    """把答案文字对到页面上的可点选项。"""
    if not answer:
        return None
    na = norm(answer)
    for opt in options:
        if norm(opt) == na or na in norm(opt) or norm(opt) in na:
            return opt
    return None


def run(login=False, repeat=1):
    sync_playwright = get_pw()
    qa = load_qa()
    log(f"题库 {len(qa)} 题")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not login,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx_args = dict(locale="zh-CN", timezone_id="America/Los_Angeles",
                        viewport={"width": 1440, "height": 900})
        if os.path.exists(STATE) and not login:
            ctx_args["storage_state"] = STATE
        ctx = browser.new_context(**ctx_args)
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")
        page = ctx.new_page()

        # ---------- 0. 登录 ----------
        page.goto(f"{HOST}/bbs/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        if "Just a moment" in page.title():
            log("过 CF 挑战中 ...")
            for _ in range(40):
                if "Just a moment" not in page.title():
                    break
                time.sleep(1.5)

        if login:
            print("\n>>> 浏览器已打开。请手动登录 + 完成微信绑定，然后回终端按回车。")
            input()
            ctx.storage_state(path=STATE)
            log(f"登录态已存 -> {STATE}")

        logged = "登录" not in page.content()[:4000] or "logout" in page.content().lower()
        log(f"页面: {page.title()!r}  登录态: {'看着像已登录' if logged else '可能是游客'}")

        # ---------- 1. 签到 ----------
        try:
            page.goto(SIGN_URL, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
            body = page.content()
            if "已经签到" in body or "今日已签到" in body or "已签到" in body:
                log("签到：今天已经签过了")
            else:
                clicked = False
                for sel in ("a:has-text('签到')", "button:has-text('签到')",
                            "input[type=submit]", "#qiandao", ".qd_btn", "a.btn"):
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            el.click()
                            clicked = True
                            time.sleep(2)
                            break
                    except Exception:
                        continue
                log(f"签到：{'点了按钮' if clicked else '没找到按钮，得手动看一眼 ' + SIGN_URL}")
                if clicked and page.query_selector("input[name*=seccode], #seccodeverify"):
                    log("签到：出现验证码，需要人工过一次（或接打码平台）")
                    if login:
                        input("    处理完验证码按回车 >>> ")
        except Exception as e:
            log(f"签到异常: {e}")

        # ---------- 2. 每日答题 ----------
        for attempt in range(1, repeat + 1):
            try:
                page.goto(TASK_URL, wait_until="domcontentloaded", timeout=45000)
                time.sleep(2)
                # 找"每日答题"入口
                entry = None
                for sel in ("a:has-text('每日答题')", "a:has-text('答题')", "text=每日答题"):
                    try:
                        e = page.query_selector(sel)
                        if e and e.is_visible():
                            entry = e
                            break
                    except Exception:
                        continue
                if not entry:
                    log("答题：首页没找到入口（可能在「今日任务」浮层里），跳过")
                    break
                entry.click()
                time.sleep(2.5)

                qtext = ""
                for sel in (".q_title", ".question", "#question", ".qsc", "h2", "h3",
                            ".modal-body", ".layui-layer-content"):
                    el = page.query_selector(sel)
                    if el:
                        t = el.inner_text().strip()
                        if len(t) > 6:
                            qtext = t
                            break
                if not qtext:
                    qtext = page.inner_text("body")[:600]

                opts = []
                for sel in ("label", ".option", ".radio", "input[type=radio] + span", "li.answer"):
                    for el in page.query_selector_all(sel):
                        try:
                            t = el.inner_text().strip()
                            if 1 < len(t) < 120:
                                opts.append(t)
                        except Exception:
                            pass
                    if opts:
                        break
                opts = list(dict.fromkeys(opts))

                ans = pick_answer(qtext, opts, qa)
                target = match_option(ans, opts) if ans else None
                if not ans:
                    log(f"答题：题库没这题 -> {qtext[:70]!r}  选项={opts[:4]}")
                    if login:
                        input("    手动答完按回车 >>> ")
                    break
                log(f"答题：命中题库 -> {ans[:50]!r}")
                if target:
                    for el in page.query_selector_all("label, .option, li.answer, span"):
                        try:
                            if el.inner_text().strip() == target:
                                el.click()
                                break
                        except Exception:
                            pass
                # 提交
                for sel in ("button:has-text('提交')", "a:has-text('提交')",
                            "input[type=submit]", "button:has-text('确定')"):
                    try:
                        b = page.query_selector(sel)
                        if b and b.is_visible():
                            b.click()
                            time.sleep(2)
                            break
                    except Exception:
                        continue
                log(f"答题：已提交（第 {attempt} 次）")
                break
            except Exception as e:
                log(f"答题异常: {e}")
                break

        # ---------- 3. 核对到账 ----------
        try:
            page.goto(CREDIT_URL, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
            txt = page.inner_text("body")
            today = time.strftime("%Y-%m-%d")
            got = [ln.strip() for ln in txt.split("\n")
                   if ("签到" in ln or "答题" in ln) and ("大米" in ln or "+1" in ln)]
            log(f"积分页核对：{len(got)} 条相关记录")
            for g in got[:6]:
                log(f"    {g[:100]}")
            m = re.search(r"大米[^\d]{0,10}(\d+)", txt)
            if m:
                log(f"当前大米: {m.group(1)}")
        except Exception as e:
            log(f"核对异常: {e}")

        if login:
            ctx.storage_state(path=STATE)
            input("    确认后按回车关闭 >>> ")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--repeat", type=int, default=1, help="答题最多试几次（答错扣 1 米，别贪）")
    a = ap.parse_args()
    run(a.login, a.repeat)


if __name__ == "__main__":
    main()
