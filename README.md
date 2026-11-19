# OpenAI 面试题库 · 一亩三分地面经

静态站点，手机/桌面自适应，浏览器内跑 Python 3（Pyodide）。

## 内容

- **74 道题**，去重归类：Coding 46 · System Design 21 · Behavioral 5 · Other 2
- **305 篇原帖**，共 174 万字正文，来自一亩三分地 `/bbs/` openai 面经帖
- 每题带：题面摘录（标注来源 tid）、关联原帖（楼层数/字数/跳转链接）、热度（被多少篇帖子提到）
- 46 道 coding 题内置 Python 运行环境，非代码题不带编辑器

## 在线访问

GitHub Pages: https://liu-zeming.github.io/1p3a-openai-questions/

## 本地运行

```bash
cd docs && python3 -m http.server 8931
# 打开 http://127.0.0.1:8931
```

## 重建数据

```bash
python3 scripts/s14_build_site_data.py   # 数据库 -> site/data.json
python3 scripts/s15_gen_site.py          # data.json -> site/index.html
cp site/index.html docs/
```

## 数据来源

一亩三分地论坛 openai 面经帖（`forum-145` 等版块），已按公司字段 + 标题黑话双重匹配去重。
帖内 `[hide]` 内容需论坛积分，本站只收录公开可见部分。

## 技术

单文件 HTML，无框架，无构建。Pyodide 从 CDN 加载，Python 在浏览器本地执行，代码不上传。
