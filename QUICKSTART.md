# QUICKSTART — 5 分钟上手

```bash
cd 1p3a-free
pip3 install requests curl_cffi playwright
python3 -m playwright install chromium
```

## 1. 先占便宜：archive.org（不用注册、不用碰目标站）

```bash
python3 scripts/s6_archive_harvest.py --list          # 枚举 tid，460 页 CDX，跑一会儿
python3 scripts/s6_archive_harvest.py --harvest --resume
```

跑完查库：

```bash
sqlite3 data/1p3a.db "select count(*), sum(length(body)) from threads;"
sqlite3 data/1p3a.db "select tid,posts_n,length(body),title from threads order by length(body) desc limit 10;"
```

## 2. 过 CF（后面所有直连的前提）

```bash
python3 scripts/s2_cf_session.py --login    # 真 Chrome 弹窗，登录一次
python3 scripts/s2_cf_session.py --check    # 看到"有正文=True"就成
```

要点：**必须真 Chrome + 有头**。headless 一律被拦，别试了。

## 3. 探通道（1 分钟，确认手机版还开着）

```bash
python3 scripts/s4_edge_probe.py --tid 1196469
```

预期输出：正常页 / 手机版 / 导读 / 搜索摘要都 200。

## 4. 全量抓

```bash
python3 scripts/s1_sitemap_enum.py --sitemap --max-page 6000
python3 scripts/s3_crawl.py --resume --rate 1.0
```

## 5. 挂着攒大米（每天 2 米，50 天到 200 = 等效 VIP）

```bash
python3 scripts/s5_credit_farm.py --login   # 第一次，登录+绑微信
15 8 * * * cd /你的路径/1p3a-free && python3 scripts/s5_credit_farm.py >> data/farm.log 2>&1
```

别忘了一次性动作（一共 102 米，比签到 50 天还多）：
新人考试 +95、规则考试 +5、设头像 +1、验证邮箱 +1。

## 常见卡点

| 症状 | 原因 | 解法 |
|---|---|---|
| 全站 403 `Just a moment` | cf_clearance 过期 | 重跑 `s2_cf_session.py` |
| `s2 --check` 200 但没正文 | 掉登录了 | `s2_cf_session.py --login` |
| 抓到的正文全是乱码 | 编码判断 | 脚本已处理（utf-8 优先，回落 gb18030），若自定义解析器记得照抄 |
| archive 报 429 | 打太快 | 脚本有指数退避；把 `sleep(1.5)` 调到 2-3 |
| `no column named channel` | 老表结构 | 脚本已加 `ALTER TABLE` 迁移 |
| 附件拿不到 | 服务端要求登录 | 必须注册号，1 米/次 |
