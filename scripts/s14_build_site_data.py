#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s14_build_site_data.py — 把 68 道标准题 + 305 篇原帖合成网站数据集。"""
import json, re, sqlite3, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB = os.path.join(DATA, "1p3a.db")
OUT = os.path.join(BASE, "site", "data.json")
os.makedirs(os.path.join(BASE, "site"), exist_ok=True)

EN = {
 "infection-spread-cellular-automata": "Infection Spread / Cellular Automata",
 "gpu-credits": "GPU Credits",
 "poker-simulation": "Poker Simulation / Hand Ranking",
 "monster-battle-system": "Monster Battle System",
 "modal-lock-fair-modal-lock": "ModalLock / FairModalLock",
 "payment-coffee-shop": "Payment System / Coffee Shop",
 "design-chess-game": "Design Chess / Chess.com",
 "design-sora-video-generation": "Design Sora Video Generation",
 "social-network-follow-graph": "Social Network Follow Graph",
 "kv-store-time-based": "KV Store / Time-based Index",
 "durable-kv-store-serialization": "Durable KV Store Serialization",
 "resumable-iterator": "Resumable Iterator",
 "ip-address-cidr-iterator": "IPv4 / CIDR Iterator",
 "numpy-1nn-wx-b": "NumPy 1-NN / Wx+B",
 "autograd-hillis-steele-scan": "Autograd / Hillis-Steele Scan",
 "transformer-bug-hunt": "Transformer Bug Hunt",
 "masked-cross-entropy-loss": "Masked Cross Entropy Loss",
 "classifier-noisy-annotators": "Classifier with Noisy Annotators",
 "memory-allocator": "Memory Allocator",
 "opensheet-spreadsheet": "OpenSheet Spreadsheet",
 "fault-tolerant-work-queue": "Fault-tolerant Work Queue",
 "chat-activity-message-aggregation": "Chat Activity Message Aggregation",
 "shard-rebalance": "Shard Rebalance",
 "distributed-cluster-count-topology": "Distributed Cluster / Machine Topology",
 "design-cloud-ide": "Design Cloud IDE",
 "design-slack": "Design Slack",
 "design-google-calendar": "Design Google Calendar",
 "design-url-shortener": "Design URL Shortener",
 "design-typing-race-game": "Design Typing Race Game",
 "design-ai-chatbot-system": "Design AI Chatbot System",
 "chatgpt-enterprise-rag": "ChatGPT Enterprise RAG",
 "rag-search-ml-design": "RAG Search ML Design",
 "webhook-delivery-system": "Webhook Delivery System",
 "image-sharing-content-deduplication": "Image Sharing Content Deduplication",
 "multi-tenant-ci-cd-workflow": "Multi-tenant CI/CD Workflow",
 "grid-demand-response-dispatch": "Grid Demand Response Dispatch",
 "points-of-interest-yelp": "Points of Interest (Yelp)",
 "gpt-3-playground": "GPT-3 Playground",
 "real-time-ai-product-feature": "Real-time AI Product Feature",
 "version-dependency": "Version Dependency Resolution",
 "time-based-kv-store": "Time-based KV Store",
 "streaming-entropy": "Streaming Entropy",
 "math-reasoning-stopping-time": "Math Reasoning / Stopping Time",
 "sharded-matmul-backprop-debugging": "Sharded MatMul Backprop Debugging",
 "vector-linked-list-checkpoints": "Vectorized Linked List Checkpoints",
 "model-calibration-ace-metric": "Model Calibration / ACE Metric",
 "light-source-sampling-mle": "Light Source Sampling",
 "code-reading-pytorch-refactor": "Code Reading / PyTorch Refactor",
 "toy-language-type-inference": "Toy Language Type Inference",
 "implement-cd-command": "Implement cd Command",
 "crossword-puzzle-solver": "Crossword Puzzle Solver",
 "elevator-scheduling-simulation": "Elevator Scheduling Simulation",
 "rectangle-board-with-undo": "Rectangle Board with Undo",
 "in-memory-database-sql": "In-memory Database / SQL",
 "maximum-score-grid-path-limited-jumps": "Maximum Score Grid Path (Limited Jumps)",
 "oa-count-shop-paths": "OA: Count Shop Paths",
 "oa-simple-network-endpoint": "OA: Simple Network Endpoint",
 "oa-microorganism-simulation": "OA: Microorganism Simulation",
 "job-scheduler-bug-fix": "Job Scheduler Bug Fix",
 "data-labeling-task-scheduler": "Data Labeling Task Scheduler",
 "mining-novel-data-unlabeled-corpus": "Mining Novel Data from Unlabeled Corpus",
 "android-mobile-screen": "Android Mobile Screen",
 "design-steam-game-store-launcher": "Design Steam Game Store Launcher",
 "technical-deep-dive": "Technical Deep Dive",
 "hm-bq-why-openai": "HM Behavioral: Why OpenAI",
 "recruiter-hr-screen-bq": "Recruiter / HR Screen",
 "engineering-management-fundamentals": "Engineering Management Fundamentals",
 "cross-functional-collaboration-bq": "Cross-functional Collaboration (BQ)",
 # EXTRA
 "tag-html-parsing": "Tag / HTML Parsing",
 "rate-limiter": "Rate Limiter",
 "ai-safety-agi": "AI Safety / AGI",
 "ml-coding-numpy": "ML Coding (numpy / Numerical Stability)",
 "refactoring": "Refactoring",
 "reservoir-sampling": "Reservoir Sampling",
}

# slug -> (中文名, 匹配正则, 岗位提示)
MAP = {
 "infection-spread-cellular-automata": ("植物感染 / 细胞自动机", r"植物感染|感染|infect|cellular.?automata|传染病|plant.?infection", ["swe","mle","research"]),
 "gpu-credits": ("GPU Credits 额度系统", r"gpu\s*credit|gpu\s*额度|credit.*(grant|subtract|balance)|额度", ["swe","infra"]),
 "poker-simulation": ("扑克模拟 / 牌型比较", r"poker|扑克|card\s*game|牌型|同花|三条|踢脚|card\s*simulation", ["swe"]),
 "monster-battle-system": ("怪兽对战系统", r"monster\s*battle|怪兽", ["swe","research"]),
 "modal-lock-fair-modal-lock": ("ModalLock / FairModalLock", r"modal\s*lock|modallock|多线程|threading|并发锁", ["swe","infra"]),
 "payment-coffee-shop": ("支付系统 / 咖啡店", r"payment|coffee\s*shop|咖啡店|支付系统|crossboard|填字", ["swe"]),
 "design-chess-game": ("设计国际象棋 / Chess.com", r"chess|国际象棋|棋", ["swe"]),
 "design-sora-video-generation": ("设计 Sora 视频生成", r"sora|视频生成|video\s*generat", ["swe","research"]),
 "social-network-follow-graph": ("社交网络关注图", r"social\s*(network|graph)|关注图|follow\s*graph", ["swe"]),
 "kv-store-time-based": ("KV Store / 时间戳索引", r"kv\s*store|key.?value|内存数据库|in-?memory|time.?based", ["swe"]),
 "durable-kv-store-serialization": ("持久化 KV Store 序列化", r"durable.*kv|序列化|snapshot|快照|persist", ["swe"]),
 "resumable-iterator": ("可恢复迭代器", r"resumable|迭代器|iterator", ["swe"]),
 "ip-address-cidr-iterator": ("IPv4 / CIDR 迭代器", r"cidr|ipv4|ip\s*地址|ip地址", ["swe"]),
 "numpy-1nn-wx-b": ("NumPy 1-NN / Wx+B", r"numpy|1-?nn|wx\s*\+\s*b|向量化", ["mle"]),
 "autograd-hillis-steele-scan": ("Autograd / Hillis-Steele Scan", r"autograd|backprop|反向传播|scan|梯度", ["mle"]),
 "transformer-bug-hunt": ("Transformer Bug Hunt", r"transformer.*bug|bug\s*hunt|attention.*bug", ["mle"]),
 "masked-cross-entropy-loss": ("Masked Cross Entropy Loss", r"cross.?entropy|交叉熵|masked.*loss", ["mle"]),
 "classifier-noisy-annotators": ("噪声标注分类器", r"noisy|标注|annotator|label\s*smooth", ["mle"]),
 "memory-allocator": ("内存分配器", r"memory\s*alloc|内存分配|allocator", ["swe","infra"]),
 "opensheet-spreadsheet": ("OpenSheet 电子表格", r"spreadsheet|opensheet|电子表格|表格依赖", ["swe"]),
 "fault-tolerant-work-queue": ("容错工作队列", r"work\s*queue|任务队列|reserve.*complete.*fail", ["swe","infra"]),
 "chat-activity-message-aggregation": ("聊天消息聚合", r"message\s*aggregat|chat.*activity|消息聚合", ["swe"]),
 "shard-rebalance": ("分片重平衡", r"shard|分片|rebalanc", ["swe","infra"]),
 "distributed-cluster-count-topology": ("分布式集群 / Machine Topology", r"topology|拓扑|cluster.*count|machine", ["swe","infra"]),
 "design-cloud-ide": ("设计 Cloud IDE", r"cloud\s*ide|云端\s*ide|在线\s*ide", ["swe"]),
 "design-slack": ("设计 Slack", r"design\s*slack|slack", ["swe"]),
 "design-google-calendar": ("设计 Google Calendar", r"google\s*calendar|日历", ["swe"]),
 "design-url-shortener": ("设计短链接", r"url\s*short|短链|短网址", ["swe"]),
 "design-typing-race-game": ("设计打字竞速游戏", r"typing\s*race|打字|竞速", ["swe"]),
 "design-ai-chatbot-system": ("设计 AI Chatbot 系统", r"chatbot|聊天机器人|ai\s*chat", ["swe","mle"]),
 "chatgpt-enterprise-rag": ("ChatGPT 企业版 RAG", r"\bRAG\b|检索增强|enterprise\s*chatgpt", ["swe","mle"]),
 "rag-search-ml-design": ("RAG 搜索 ML 设计", r"rag.*search|检索.*搜索", ["mle"]),
 "webhook-delivery-system": ("Webhook 投递系统", r"webhook", ["swe"]),
 "image-sharing-content-deduplication": ("图片分享去重", r"image\s*shar|图片.*去重|dedup", ["swe"]),
 "multi-tenant-ci-cd-workflow": ("多租户 CI/CD", r"ci\s*/?\s*cd|multi.?tenant|流水线", ["swe","infra"]),
 "grid-demand-response-dispatch": ("电网需求响应调度", r"电网|demand\s*response|\bgrid\s*balanc", ["swe"]),
 "points-of-interest-yelp": ("POI 兴趣点系统", r"\\bpoi\\b|兴趣点|yelp", ["swe"]),
 "gpt-3-playground": ("GPT-3 Playground", r"playground", ["swe"]),
 "real-time-ai-product-feature": ("实时 AI 产品功能", r"real.?time\s*ai|实时.*ai", ["swe"]),
 "version-dependency": ("版本依赖解析", r"version\s*depend|版本依赖|依赖解析", ["swe"]),
 "time-based-kv-store": ("时间索引 KV Store", r"time.?based\s*kv|时间.*kv", ["swe"]),
 "streaming-entropy": ("流式计算熵", r"entropy|熵", ["mle"]),
 "math-reasoning-stopping-time": ("数学推理停止时间", r"stopping\s*time|停止时间|math\s*reason", ["mle"]),
 "sharded-matmul-backprop-debugging": ("分片矩阵乘反向调试", r"matmul|矩阵乘", ["mle"]),
 "vector-linked-list-checkpoints": ("向量化链表检查点", r"linked\s*list|链表", ["swe"]),
 "model-calibration-ace-metric": ("模型校准 / ACE 指标", r"calibrat|校准|\\bACE\\b", ["mle"]),
 "light-source-sampling-mle": ("光源采样", r"light\s*source|光源", ["mle"]),
 "code-reading-pytorch-refactor": ("代码阅读 / PyTorch 重构", r"code\s*read|pytorch|重构|refactor", ["mle","swe"]),
 "toy-language-type-inference": ("玩具语言类型推断", r"type\s*infer|类型推断|type\s*system", ["swe"]),
 "implement-cd-command": ("实现 cd 命令", r"\bcd\s*命令|implement\s*cd", ["swe"]),
 "crossword-puzzle-solver": ("填字游戏求解器", r"crossword|填字", ["swe"]),
 "elevator-scheduling-simulation": ("电梯调度模拟", r"elevator|电梯", ["swe"]),
 "rectangle-board-with-undo": ("带撤销的矩形板", r"rectangle|矩形|undo|撤销", ["swe"]),
 "in-memory-database-sql": ("内存数据库 SQL", r"in.?memory\s*database|sql\s*engine|数据库实现", ["swe"]),
 "maximum-score-grid-path-limited-jumps": ("网格最大得分路径", r"grid\s*path|maximum\s*score|网格路径", ["swe"]),
 "oa-count-shop-paths": ("OA: 商店路径计数", r"shop\s*path|商店路径", ["swe"]),
 "oa-simple-network-endpoint": ("OA: 简单网络端点", r"network\s*endpoint|网络端点", ["swe"]),
 "oa-microorganism-simulation": ("OA: 微生物模拟", r"microorganism|微生物", ["swe"]),
 "job-scheduler-bug-fix": ("任务调度器 Bug 修复", r"job\s*schedul|调度器.*bug|scheduler\s*bug", ["swe"]),
 "data-labeling-task-scheduler": ("数据标注任务调度", r"data\s*label|标注.*调度", ["swe","mle"]),
 "mining-novel-data-unlabeled-corpus": ("未标注语料挖掘", r"unlabeled|未标注|corpus", ["mle"]),
 "android-mobile-screen": ("Android 移动端屏幕", r"android|移动端", ["swe"]),
 "design-steam-game-store-launcher": ("Steam 商店启动器", r"steam|游戏商店|launcher", ["swe"]),
 "technical-deep-dive": ("技术深挖 (Technical Deep Dive)", r"deep\s*dive|深挖|technical\s*deep", ["all"]),
 "hm-bq-why-openai": ("HM 行为面：为什么选 OpenAI", r"why\s*openai|为什么.*openai|hm.*bq|hiring\s*manager", ["all"]),
 "recruiter-hr-screen-bq": ("Recruiter / HR 行为面", r"(recruiter|\bHR\b)\s*[^\n]{0,8}(call|screen|面|轮|聊)|hr\s*面经", ["all"]),
 "engineering-management-fundamentals": ("工程管理基础 (EM)", r"engineering\s*management|管理岗|em\s*面", ["em"]),
 "cross-functional-collaboration-bq": ("跨职能协作行为面", r"cross.?functional|跨职能|collaborat", ["all"]),
}

# 帖子里出现但不在 68 题里的
EXTRA = {
 "tag-html-parsing": ("Tag / HTML 解析", r"html\s*tag|tag\s*parser|解析\s*html|strip\s*tag|标签解析", ["swe"], "coding"),
 "rate-limiter": ("Rate Limiter 限流器", r"rate\s*limit|限流", ["swe","infra"], "coding"),
 "ai-safety-agi": ("AI Safety / AGI 观点题", r"ai\s*safety|agi|safety", ["all"], "behavioral"),
 "ml-coding-numpy": ("ML Coding（numpy / 数值稳定性）", r"numpy|数值稳定|ml\s*coding|colab|scipy", ["mle"], "coding"),
 "refactoring": ("Refactoring 重构", r"refactor|重构", ["swe"], "coding"),
 "reservoir-sampling": ("Reservoir / 采样类", r"reservoir|采样", ["mle"], "coding"),
}


def load_posts():
    con = sqlite3.connect(DB)
    return con.execute(
        "SELECT tid,title,body,posts_n FROM threads WHERE channel='openai' AND body!='' ORDER BY tid DESC"
    ).fetchall()


NOISE = re.compile(
    r"提升卡|置顶卡|关贴卡|开贴卡|变色卡|千斤顶|狗仔卡|当前离线|主题\s*帖子|"
    r"积分\s*通行证|大米\s*颗|鳄梨\s*个|水井\s*尺|蓝莓\s*颗|萝卜\s*根|小米\s*粒|学分\s*个|"
    r"注册时间|最后登录|使用道具|回复\s*支持\s*反对|本楼：|只看该作者|匿名用户-|"
    r"淘帖\d*|好苗\d*|杂草\d*|参与人数|收起|^\s*理由|查看全部评分|上一篇|下一篇|"
    r"相关帖子|Unlock interview|Popular Interview Questions|注册一亩三分地论坛|"
    r"您需要 登录|没有帐号|点击阅读更多|打开一亩三分地APP|常见问题|联系客服|"
    r"商务洽谈|Copyright|See Terms|触屏版|电脑版|客户端|Powered by Discuz|"
    r"本帖子中包含更多资源|附件|评分\s*$|举报\s*$|支持\s*$|反对\s*$|"
    r"^<\s*/?\s*(td|tr|div|span|table|tbody|a|b|font)|itemprop|class=\s*[\"']|"
    r"&#x?[0-9A-Fa-f]+;|setAttribute|innerHTML|\.innerHTML|sbtn\.|document\.|"
    r"function\s*\(|window\.|^\s*var\s+\w+\s*=|onclick|javascript:|"
    r"本帖隐藏|积分高于|您当前积分|使用VIP即刻解锁|解锁阅读权限|"
    r"回复发表中|回复\s*$|收藏\s*\d|欢迎体验一亩三分地|职业规划.*面试辅导|量身定制|^\s*\d+\s*$|^x$|^\s*[+\-]?\d+\s*$")
# 评论性开头
COMMENT = re.compile(r"^(恭喜|lz\b|楼主|感谢|谢谢|patpat|mark|蹲|同问|请问下|求问|好奇|"
                     r"太可惜|牛逼|厉害|收藏了|赞一个|顶|沙发|同加面|我也是|我是懒羊羊)")
# 题面特征：出现这些词优先
SIGNAL = re.compile(r"题目|题面|问题是|要求|实现|implement|design|给定|input|output|"
                    r"follow\s*up|追问|输入|输出|返回|写一个|写个|算法|复杂度|思路|"
                    r"第一问|第二问|第三问|part\s*[1-4]|考察|考的是|原题", re.I)

def clean(t):
    out = []
    STOP = ("给您点个赞", "给你点个赞", "相关帖子", "查看全部评分",
            "回复发表中", "淘帖0", "这篇帖子被以下")
    for ln in (t or "").split("\n"):
        ln = ln.strip()
        if len(ln) < 6: continue
        if any(s in ln for s in STOP): break
        if NOISE.search(ln): continue
        if len(re.sub(r"[^\w\u4e00-\u9fff]", "", ln)) < 5: continue
        if COMMENT.search(ln): continue
        out.append(ln)
    return "\n".join(out)

def snippet(body, pat, n=1):
    """抓命中处上下文，优先选含题面特征的段落"""
    body = clean(body)
    for cut in ("本帖隐藏的内容需要积分", "您需要 登录 才可以下载"):
        i = body.find(cut)
        if i > 200: body = body[:i]
    cands = []
    for m in re.finditer(pat, body, re.I):
        s0 = max(0, m.start() - 200); e0 = min(len(body), m.end() + 380)
        seg = re.sub(r"\n{2,}", "\n", body[s0:e0]).strip()
        if len(seg) < 60: continue
        score = len(SIGNAL.findall(seg))
        cands.append((score, len(seg), seg))
    if not cands: return []
    cands.sort(key=lambda x: (-x[0], -x[1]))
    ok = [c[2] for c in cands if c[0] > 0] or [cands[0][2]]
    return ok[:n]


def detect_role(title, body):
    """看标题 + 开头 600 字，默认 SWE"""
    r = set()
    t = (title or "") + " " + (body or "")[:600]
    if re.search(r"\bMLE\b|ML\s*(Engineer|岗)|machine\s*learning\s*engineer|机器学习岗", t, re.I): r.add("mle")
    if re.search(r"research\s*(engineer|org|岗|scientist)|研究员|research\s*岗|\bRE\s*(岗|面|track)", t, re.I): r.add("research")
    if re.search(r"infra|基础设施|systems?\s*coding|platform\s*team", t, re.I): r.add("infra")
    if re.search(r"\bPM\b|产品经理|product\s*manager", t, re.I): r.add("pm")
    if re.search(r"\bDS\b|data\s*scien|数据科学", t, re.I): r.add("ds")
    if re.search(r"管理岗|工程管理|\bEM\b|engineering\s*manager", t, re.I): r.add("em")
    if not r: r.add("swe")
    return sorted(r)


def detect_stage(title, body):
    s = set()
    t = title + body[:3000]
    if re.search(r"OA|在线笔|online\s*assess", t, re.I): s.add("OA")
    if re.search(r"电面|phone\s*screen|店面|tech\s*screen|screening", t, re.I): s.add("Phone Screen")
    if re.search(r"昂赛|onsite|\bVO\b|虚拟现场|virtual\s*onsite", t, re.I): s.add("Onsite")
    if re.search(r"BQ|behavioral|行为面", t, re.I): s.add("Behavioral")
    if re.search(r"deep\s*dive|深挖", t, re.I): s.add("Deep Dive")
    if re.search(r"team\s*match", t, re.I): s.add("Team Match")
    return sorted(s) or ["Onsite"]


def main():
    posts = load_posts()
    print(f"帖子 {len(posts)}")
    # 预计算每帖的岗位/阶段
    meta = {}
    for tid, title, body, pn in posts:
        meta[tid] = {"tid": tid, "title": title or "", "chars": len(body or ""),
                     "floors": pn or 0, "roles": detect_role(title or "", body or ""),
                     "stages": detect_stage(title or "", body or ""),
                     "url": f"https://www.1point3acres.com/bbs/thread-{tid}-1-1.html"}

    used = collections.Counter()
    questions = []

    def build(qid, name, pat, roles, category, freq=None, name_en=None):
        hits = []
        for tid, title, body, pn in posts:
            if re.search(pat, (title or "") + "\n" + (body or ""), re.I):
                hits.append(tid)
        if not hits:
            hits = []
        used[qid] = len(hits)
        snips = []
        for tid in (hits or [])[:12]:
            body = next(b for t, _, b, _ in posts if t == tid)
            for s in snippet(body, pat, 1):
                snips.append({"tid": tid, "text": s})
                break
            if len(snips) >= 6:
                break
        # 岗位/阶段按出现比例收窄，避免每题都挂满所有标签
        rc = collections.Counter(r for tid in (hits or []) for r in meta[tid]["roles"])
        sc = collections.Counter(s for tid in (hits or []) for s in meta[tid]["stages"])
        tot = len(hits) or 1
        allroles = [r for r, c in rc.most_common() if c / tot >= 0.30][:3] or \
                   [r for r, _ in rc.most_common(1)] or (roles if roles and "all" not in roles else ["swe"])
        stages = [s for s, c in sc.most_common() if c / tot >= 0.30][:2] or \
                 [s for s, _ in sc.most_common(1)]
        questions.append({
            "id": qid, "name": name, "name_en": name_en or name,
            "category": category,
            "roles": allroles,
            "stages": stages,
            "heat": len(hits),
            "runnable": category == "coding",
            "frequency": freq,
            "snippets": snips,
            "posts": [meta[t] for t in sorted(hits or [], reverse=True)[:40]],
        })

    # 68 道标准题
    for slug, (name, pat, roles) in MAP.items():
        cat = "coding" if re.search(r"coding|numpy|autograd|loss|allocator|kv|iterator|schedul|matmul|calibration|sampling|refactor|type.?infer|spreadsheet|queue|graph|simulation|path|command|solver|poker|battle|infection|transformer|entropy|checkpoint|topology|rebalance|aggregation|lock|parse|limiter", slug, re.I) else \
              ("behavioral" if re.search(r"bq|deep-dive|management|collaboration", slug, re.I) else "system-design")
        freq = None
        qb = [json.loads(l) for l in open(os.path.join(DATA, "interview_qbank.jsonl")) if json.loads(l)["company"] == "openai"]
        if qb:
            for x in qb[0]["questions"]:
                if x.get("slug") == slug:
                    freq = x.get("frequency"); cat = x.get("category") or cat
        build(slug, name, pat, roles, cat, freq, name_en=EN.get(slug) or slug.replace("-", " ").title())

    # 补充题
    for qid, (name, pat, roles, cat) in EXTRA.items():
        build(qid, name, pat, roles, cat, None, EN.get(qid) or qid.replace("-", " ").title())

    questions.sort(key=lambda x: (-x["heat"], x["name"]))
    roles_agg = collections.Counter()
    for q in questions:
        for r in q["roles"]:
            roles_agg[r] += 1

    out = {
        "meta": {
            "source": "public community forum OpenAI interview posts",
            "generated": __import__("time").strftime("%Y-%m-%d %H:%M"),
            "posts": len(posts),
            "questions": len(questions),
            "total_chars": sum(m["chars"] for m in meta.values()),
            "chars": sum(m["chars"] for m in meta.values()),
        },
        "roles": [{"id": k, "count": v} for k, v in roles_agg.most_common()],
        "categories": [
            {"id": "coding", "name": "Coding", "count": sum(1 for q in questions if q["category"] == "coding")},
            {"id": "system-design", "name": "System Design", "count": sum(1 for q in questions if q["category"] == "system-design")},
            {"id": "behavioral", "name": "Behavioral", "count": sum(1 for q in questions if q["category"] == "behavioral")},
            {"id": "other", "name": "Other", "count": sum(1 for q in questions if q["category"] not in ("coding", "system-design", "behavioral"))},
        ],
        "stages": sorted({s for q in questions for s in q["stages"]}),
        "questions": questions,
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"[+] {len(questions)} 道题 -> {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    for q in questions[:12]:
        print(f"  {q['heat']:>3} 帖  [{q['category']:<13}] {q['name']}")


if __name__ == "__main__":
    main()
