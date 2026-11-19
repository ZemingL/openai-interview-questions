#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s17_clean_db.py — 深度清洗库内正文（去论坛 UI / HTML 残留 / 隐藏提示 / 楼层戳）"""
import re, sqlite3, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "1p3a.db")

# 整行删除的 UI / 元信息
DROP_LINE = re.compile(
    r"^\s*(提升卡|置顶卡|关贴卡|开贴卡|变色卡|千斤顶|狗仔卡|使用道具|举报|回复|支持|反对|"
    r"评分|收藏|淘帖|分享|顶|踩)\s*$|"
    r"^\s*本楼：|^\s*只看该作者|^\s*当前离线|^\s*主题\s|^\s*帖子\s*\d+|^\s*积分\s|"
    r"^\s*大米\s*颗|^\s*鳄梨\s*个|^\s*水井\s*尺|^\s*蓝莓\s*颗|^\s*萝卜\s*根|^\s*小米\s*粒|^\s*学分\s*个|"
    r"^\s*注册时间|^\s*最后登录|^\s*匿名用户|^\s*地里匿名用户|^\s*匿名用户-[A-Z0-9]+|"
    r"^\s*&#x?[0-9A-Fa-f]+;\s*$|^\s*<td|^\s*itemprop=|^\s*class=\"|^\s*</?t[dr]|"
    r"^\s*\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}(:\d{2})?\s*$|"
    r"^\s*(昨天|前天|今天)\s*\d{1,2}:\d{2}\s*$|^\s*\d+\s*(分钟|小时|天)前\s*$|"
    r"^\s*(Color|Link|Quote|Code|Bold|Italic|Underline|Image|Url|Hide)\s*$|"
    r"^\s*(楼主|沙发|板凳|地板)\s*$|^\s*\d+\s*#\s*$|"
    r"^\s*[+\-]?\d+\s*$|^\s*x\s*$|^\s*\.{3,}\s*$|"
    r"^\s*点评|^\s*回复\s*$|^\s*查看全部|^\s*收起|^\s*理由|^\s*参与人数|"
    r"^\s*\[参与人数|^\s*游客，您好|^\s*感谢分享|^\s*谢谢分享|"
    r"浏览过的版块|论坛导航|新手指南|常见Q&A|关于我们|加入团队|解锁VIP|VIP通行证|"
    r"购买蓝莓|商务合作|企业招聘|地里专栏|服务条款|社区守则|隐私政策|"
    r"gas furnace|修理方法|润德国|上六天班|九评领英|找工存档|写了本书|"
    r"宫殿要懂的套路|焦虑症|The PIP I am|项目管理的方式|留个联系方式|"
    r"发帖聊聊|详细讲解|^\s*\d{4}\s*年\s*\d+\s*月|"
    r"^\s*【?海投|^\s*刷题打卡|^\s*Leetcode|^\s*小白转码|"
    r"^\s*相关帖子|^\s*上一篇|^\s*下一篇|^\s*推荐阅读|^\s*猜你喜欢|^\s*热门推荐|"
    r"^\s*(亚麻|Stripe|爱彼迎|Amazon|Mathwork|谷歌|ByteDance|怎样快速|堆栈|工作日|"
    r"贷款公司|求问|核心编制|果is|条纹|刀大师|DRW|google 面经|Rippling|Pinterest|"
    r"砖场|Anthropic|Fortinet|找工小结|【海投|Summer intern|apple )")

# 含这些词的行整行删除（论坛提示 / 广告）
DROP_ANY = re.compile(
    r"注册一亩三分地论坛|您需要\s*登录|没有帐号|本帖隐藏的内容|积分高于|您当前积分|"
    r"使用VIP即刻解锁|VIP即刻解锁|Unlock interview|Popular Interview Questions|"
    r"欢迎体验一亩三分地|职业规划.*面试辅导|量身定制|使用独家折扣码|1p3acre|"
    r"欢迎分享你知道的情况|会给更多积分奖励|很有用的信息|给你点个赞|给您点个赞|"
    r"欢迎来一亩三分地|地里的生活菌|instant_dev|instant_ops|游客，您好|"
    r"^\s*\[参与人数|感谢分享！|谢谢分享|欢迎分享|很有用的信息|"
    r"本帖子中包含更多资源|点击阅读更多|打开一亩三分地APP|常见问题|联系客服|"
    r"商务洽谈|Copyright|See Terms|触屏版|电脑版|客户端|Powered by Discuz|"
    r"隐私提醒|禁止发布广告|找人请去|论坛内容在发帖|为防止被骚扰|公开留微信|"
    r"快速回复|返回顶部|返回列表|发表回复|回帖后跳|查阅全站|本版积分规则|"
    r"干货版块可免费使用|关注我们|微信公众号|海外投资公众号|求职移民公众号|"
    r"体验AI模拟面试|个性化反馈|提升技术水平|助力职业进阶|"
    r"^\s*var\s|^\s*//\s|fastpostvalidate|reoverBtn|isValid|"
    r"^\s*本帖最后由|^\s*补充内容|^\s*编辑|"
    r"^\.1point3acres|1point3acres\.com$|^\s*From 1point|^\s*check 1point"
    r"^Notice:|Instant|Salarytics|Visa Tracker")

# 行内清理
INLINE = [
    (re.compile(r'itemprop="articleBody">', re.I), ""),
    (re.compile(r'<td[^>]*>', re.I), ""),
    (re.compile(r'&#x?[0-9A-Fa-f]+;'), ""),
    (re.compile(r"&nbsp;"), " "),
    (re.compile(r"&amp;"), "&"),
    (re.compile(r"&lt;"), "<"), (re.compile(r"&gt;"), ">"),
    (re.compile(r"&quot;"), '"'),
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"游客，您好！|您好！|〖本帖隐藏〗"), ""),
]
# 段落里出现就截断（隐藏内容起点）
CUT = ("本帖隐藏的内容需要积分", "您需要 登录 才可以下载",
       "注册一亩三分地论坛，查看更多干货")


def clean(text):
    if not text:
        return ""
    for pat, rep in INLINE:
        text = pat.sub(rep, text)
    lines, out = text.split("\n"), []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if len(ln) < 4:
            continue
        if DROP_LINE.match(ln) or DROP_ANY.search(ln):
            continue
        out.append(ln)
    # ---- 尾部推荐列表清理：从后往前找连续短标题行 ----
    i = len(out) - 1
    while i >= 0:
        run, j = 0, i
        while j >= 0 and len(out[j]) <= 34 and not out[j].endswith(("。", "！", "？", ".", "!", "?")):
            run += 1; j -= 1
        if run >= 4:
            del out[j + 1:]
            break
        i = j if j < i else i - 1

    body = "\n".join(out)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def main():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT tid,title,body FROM threads").fetchall()
    print(f"[*] 待清洗 {len(rows)} 帖")
    before = sum(len(b or "") for _, _, b in rows)
    n = 0
    for tid, title, body in rows:
        nb = clean(body or "")
        if nb != (body or ""):
            con.execute("UPDATE threads SET body=? WHERE tid=?", (nb, tid))
            n += 1
    con.commit()
    after = sum(len(b or "") for _, _, b in con.execute("SELECT tid,title,body FROM threads"))
    print(f"[+] 更新 {n} 帖")
    print(f"[*] 正文 {before:,} -> {after:,} 字（去噪 {before-after:,}）")
    # 抽样
    print("\n抽样：")
    for tid, body in con.execute(
            "SELECT tid,body FROM threads WHERE channel='openai' AND length(body)>500 "
            "ORDER BY tid DESC LIMIT 2"):
        print(f"\n--- tid={tid} ({len(body)} 字)")
        print(body[:400])


if __name__ == "__main__":
    main()
