#!/usr/bin/env bash
# 一键部署到 GitHub Pages
# 用法：
#   ./deploy.sh                      # 仓库已手动建好，直接推
#   GH_TOKEN=ghp_xxx ./deploy.sh     # 有 token，全自动（建仓库 + 推 + 开 Pages）
set -euo pipefail
REPO="${REPO:-openai-interview-questions}"
USER="${GH_USER:-liu-zeming}"
BRANCH="main"

cd "$(dirname "$0")"

if [ -n "${GH_TOKEN:-}" ]; then
  echo "[1/4] 用 token 创建仓库（已存在则跳过）"
  curl -sS -X POST https://api.github.com/user/repos \
    -H "Authorization: Bearer $GH_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -d "{\"name\":\"$REPO\",\"description\":\"OpenAI 面试题库 · 一亩三分地面经\",\"private\":false,\"has_issues\":false,\"has_wiki\":false}" \
    -o /tmp/ghrepo.json -w "  HTTP %{http_code}\n" || true
  python3 -c "import json;d=json.load(open('/tmp/ghrepo.json'));print('  ',d.get('message') or d.get('full_name'))" 2>/dev/null || true
  REMOTE="https://x-access-token:$GH_TOKEN@github.com/$USER/$REPO.git"
else
  echo "[1/4] 无 token —— 需要仓库已存在。没有就去 https://github.com/new 建一个空仓库（不要勾 README）"
  REMOTE="git@github.com:$USER/$REPO.git"
  if ! git ls-remote "$REMOTE" >/dev/null 2>&1; then
    echo "  ✗ 仓库 $USER/$REPO 不存在。先建：https://github.com/new?name=$REPO"
    exit 1
  fi
fi

echo "[2/4] 推送"
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"
git branch -M "$BRANCH"
git push -u origin "$BRANCH" --force

if [ -n "${GH_TOKEN:-}" ]; then
  echo "[3/4] 开启 GitHub Pages（main /docs）"
  curl -sS -X POST "https://api.github.com/repos/$USER/$REPO/pages" \
    -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" \
    -d "{\"source\":{\"branch\":\"$BRANCH\",\"path\":\"/docs\"}}" \
    -o /tmp/ghpages.json -w "  HTTP %{http_code}\n" || true
  python3 -c "import json;d=json.load(open('/tmp/ghpages.json'));print('  ',d.get('message') or d.get('html_url'))" 2>/dev/null || true
else
  echo "[3/4] 手动开 Pages：Settings → Pages → Source 选 Deploy from a branch → main / docs → Save"
fi

echo "[4/4] 站点地址（Pages 首次构建约 1 分钟）"
echo "  https://$USER.github.io/$REPO/"
