#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s19_purify.py — 把 data.json 里和题目无关的内容 trim 掉。

策略：按句子切分 → 打分（题目特征 - 无关特征）→ 只留正分句 → 重新拼段落。
不动数据库，只改 site/data.json 的 snippets / answer。
"""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site", "data.json")

# 题目相关特征
KEEP = re.compile(
    r"题目|题意|要求|实现|输入|输出|给定|返回|参数|边界|条件|规则|复杂度|"
    r"follow[\s-]?up|追问|第[一二三四五1-5]问|part\s*\d|考察|考的是|面的是|考了|"
    r"设计|写一个|写个|实现一个|需要支持|支持以下|请实现|描述|example|样例|"
    r"数组|链表|树|图|队列|栈|哈希|堆|字符串|矩阵|网格|线程|锁|事务|索引|缓存|"
    r"class\s|def\s|return\s|import\s|```|O\(|时间复杂度|空间复杂度", re.I)
# 无关特征
DROP = re.compile(
    r"recruiter|\bHR\b|约面|排期|多久|几周|几天|回复|timeline|时间线|流程|几轮|轮次|加面|"
    r"挂了|被拒|拒信|reject|fail|offer|包裹|薪资|工资|签字费|\bTC\b|\bbase\b|\bRSU\b|"
    r"求米|加米|大米|积分|私聊|评论区|补充内容|编辑|更新于|"
    r"team[\s-]?match|内推|referral|冷冻期|\bHC\b|headcount|招人|"
    r"感觉|可惜|难受|心态|发挥|郁闷|遗憾|经验教训|反思|"
    r"祝|加油|好运|感谢|谢谢|patpat|安慰|"
    r"体验|感受|氛围|我本人|我还没|没面过|仅供参考|"
    r"刷题|复习|mock|备考|准备中|准备了|正在准备|分享给|指正|补充|整理|"
    r"\bBQ\b|behavioral|行为面|"
    r"楼主|匿名|发表于|浏览|收藏|回复\s*$|^×$|^x$|"
    r"没做完|时间不够|来不及|紧张|"
    r"放水|吐槽|无语|服了|祭旗|祭天|后悔|懊悔|痛心|寒心|离谱|"
    r"以上|仅供参考|自行判断|不确定|可能吧|应该是吧|"
    r"面经\s*\||挂经\s*\||求捞|请愿|效仿|"
    r"We'll cover|You will need|Please let us know|invitation|Will you be|"
    r"takehome|48小时|提交后|Intern Interview|Data Engineer|Applied ML|"
    r"^(亚麻|Stripe|爱彼迎|Amazon|Mathwork|谷歌|ByteDance|怎样快速|堆栈|工作日|贷款公司|求问|"
    r"核心编制|果is|条纹|刀大师|DRW|google|Rippling|Pinterest|砖场|Anthropic|Fortinet|找工小结|"
    r"【海投|Summer intern|apple|hedge|hinge|Nvidia员工|Shopify|United Airline|Roblox)", re.I)


def split_sents(text):
    """按句号/分号/换行切句，保留分隔符"""
    parts = re.split(r"(?<=[。！？；!?;])\s*|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def purify(text, ratio=0.45, max_len=1300):
    """保留题目相关度最高的句子，累计到原长的 ratio，按原序拼回"""
    if not text:
        return None
    sents = [x for x in split_sents(text) if len(x) >= 6]
    if not sents:
        return None
    total = sum(len(x) for x in sents)
    target = max(150, int(total * ratio))

    scored = []
    for i, x in enumerate(sents):
        k = len(KEEP.findall(x))
        d = len(DROP.findall(x))
        score = k * 2 - d
        scored.append((score, len(x), i, x))

    # 先按分数降序挑，够了就停
    picked, ln = set(), 0
    for score, L, i, x in sorted(scored, key=lambda t: (-t[0], -t[1])):
        if ln >= target:
            break
        if score < 0:
            continue          # 纯噪声跳过，除非还不够长
        picked.add(i); ln += L
    # 仍不够：退而求其次，按长度补
    if ln < target * 0.6:
        for score, L, i, x in sorted(scored, key=lambda t: -t[1]):
            if i in picked:
                continue
            picked.add(i); ln += L
            if ln >= target:
                break

    body = "".join(x for i, x in enumerate(sents) if i in picked).strip()
    if len(body) < 100:
        return None
    # 质量门：标题列表 / 招聘关键词密集 → 判定为噪声
    JUNK = re.compile(r"面经|挂经|电面|求捞|intern|\bOA\b|\bVO\b|\bSDE\b|\bDS\b|\bHR\b|"
                      r"Interview|Engineer|Data Scien", re.I)
    if len(JUNK.findall(body)) >= 3:
        return None
    # 推荐列表 / 站内提示 / 无关话题
    LISTY = re.compile(r"gas furnace|德国官方|unpaid|\bPIP\b|does not represent|地里新农|"
                       r"考试中心|1Point3Acres\.com|修理方法|润德国|上六天班|"
                       r"热门推荐|相关主题|点击阅读更多", re.I)
    if LISTY.search(body):
        return None
    # 中文占比过低（多半是广告/英文模板）
    zh = len(re.findall(r"[\u4e00-\u9fff]", body))
    if zh and zh / len(body) < 0.25:
        return None
    return body[:max_len]


def main():
    d = json.load(open(SITE))
    qs = d["questions"]

    # ---- snippets ----
    sn_before = sn_after = 0
    for q in qs:
        out = []
        for s in q.get("snippets") or []:
            sn_before += len(s["text"])
            t = purify(s["text"])
            if t:
                out.append({"tid": s["tid"], "text": t})
                sn_after += len(t)
        q["snippets"] = out[:2]

    # ---- answer ----
    an_before = an_after = 0
    for q in qs:
        out = []
        for a in q.get("answer") or []:
            an_before += len(a["text"])
            t = purify(a["text"], ratio=0.5)
            if t:
                out.append({"tid": a["tid"], "text": t})
                an_after += len(t)
        q["answer"] = out[:1]

    # ---- posts 里的标题也 trim：只保留帖子，不动 ----
    d["meta"]["total_chars"] = sum(len(s["text"]) for q in qs for s in q["snippets"])

    json.dump(d, open(SITE, "w"), ensure_ascii=False, separators=(",", ":"))
    have_sn = sum(1 for q in qs if q["snippets"])
    have_an = sum(1 for q in qs if q["answer"])
    print(f"摘录  {sn_before:,} → {sn_after:,} 字（-{(1-sn_after/max(sn_before,1))*100:.0f}%）")
    print(f"答案  {an_before:,} → {an_after:,} 字（-{(1-an_after/max(an_before,1))*100:.0f}%）")
    print(f"有摘录 {have_sn}/{len(qs)}   有答案 {have_an}/{len(qs)}")
    print("\n样例：")
    for q in qs[:2]:
        if q["snippets"]:
            print(f"\n【{q['name']}】")
            print(q["snippets"][0]["text"][:320])


if __name__ == "__main__":
    main()
