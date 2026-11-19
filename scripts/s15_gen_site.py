#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s15_gen_site.py — 生成单文件静态站（内嵌数据 + Pyodide 浏览器内跑 Python）。"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "site", "data.json")
OUT = os.path.join(BASE, "site", "index.html")

d = json.load(open(DATA))
blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
meta = d["meta"]

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>OpenAI 面试题库 · 一亩三分地面经</title>
<style>
:root{
  --bg:#0b0e14; --bg2:#11151f; --card:#161b26; --card2:#1c2230;
  --line:#232a3a; --txt:#e6e9ef; --dim:#8b95a8; --dim2:#5e6878;
  --accent:#10a37f; --accent2:#1ed7a4; --code:#0d1117;
  --coding:#10a37f; --sd:#4f7cff; --bq:#c084fc; --other:#f59e0b;
  --radius:14px;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro SC","PingFang SC","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent2);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 80px}

/* ---------- header ---------- */
header{padding:28px 0 18px;border-bottom:1px solid var(--line);margin-bottom:18px}
h1{margin:0 0 6px;font-size:24px;letter-spacing:-.4px;font-weight:700}
h1 .g{background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;
  background-clip:text;color:transparent}
.sub{color:var(--dim);font-size:13px;margin:0}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:12px;color:var(--dim)}
.stat b{color:var(--txt);font-size:15px;font-variant-numeric:tabular-nums;margin-right:3px}

/* ---------- filters ---------- */
.filters{position:sticky;top:0;z-index:30;background:rgba(11,14,20,.94);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line);padding:12px 0;margin-bottom:18px}
.searchrow{display:flex;gap:8px;margin-bottom:10px}
input[type=search]{flex:1;background:var(--card);border:1px solid var(--line);color:var(--txt);
  border-radius:10px;padding:10px 14px;font-size:14px;outline:none;font-family:inherit}
input[type=search]:focus{border-color:var(--accent)}
select{background:var(--card);border:1px solid var(--line);color:var(--txt);border-radius:10px;
  padding:10px 12px;font-size:13px;outline:none;font-family:inherit;cursor:pointer}
.chips{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;background:var(--card);border:1px solid var(--line);color:var(--dim);
  border-radius:999px;padding:6px 13px;font-size:12.5px;cursor:pointer;white-space:nowrap;
  transition:.15s;user-select:none}
.chip:hover{border-color:var(--dim2);color:var(--txt)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#04120e;font-weight:600}
.chip .n{opacity:.65;margin-left:4px;font-variant-numeric:tabular-nums}

/* ---------- cards ---------- */
.list{display:flex;flex-direction:column;gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;transition:.18s}
.card:hover{border-color:#2c3548}
.head{padding:15px 16px;cursor:pointer;display:flex;gap:12px;align-items:flex-start}
.rank{flex:0 0 34px;height:34px;border-radius:9px;background:var(--card2);
  display:grid;place-items:center;font-size:12px;font-weight:700;color:var(--dim);
  font-variant-numeric:tabular-nums}
.rank.hot{background:linear-gradient(135deg,#7c2d12,#b45309);color:#fff}
.body{flex:1;min-width:0}
.title{font-weight:600;font-size:15.5px;margin-bottom:7px;word-break:break-word}
.tags{display:flex;flex-wrap:wrap;gap:5px}
.tag{font-size:11px;padding:2.5px 8px;border-radius:6px;background:var(--card2);
  color:var(--dim);border:1px solid var(--line)}
.tag.cat-coding{background:rgba(16,163,127,.14);color:var(--accent2);border-color:rgba(16,163,127,.28)}
.tag.cat-system-design{background:rgba(79,124,255,.14);color:#8aa9ff;border-color:rgba(79,124,255,.28)}
.tag.cat-behavioral{background:rgba(192,132,252,.14);color:#d8b4fe;border-color:rgba(192,132,252,.28)}
.tag.cat-other{background:rgba(245,158,11,.14);color:#fbbf24;border-color:rgba(245,158,11,.28)}
.tag.heat{background:rgba(239,68,68,.12);color:#f87171;border-color:rgba(239,68,68,.25)}
.tag.run{background:rgba(16,163,127,.18);color:var(--accent2);border-color:rgba(16,163,127,.35)}
.metrics{display:flex;gap:14px;color:var(--dim2);font-size:12px;margin-top:8px;flex-wrap:wrap}
.metrics b{color:var(--dim);font-variant-numeric:tabular-nums}
.panel{display:none;border-top:1px solid var(--line);padding:16px;background:var(--bg2)}
.card.open .panel{display:block}
.sec{margin-bottom:18px}
.sec:last-child{margin-bottom:0}
.sec h3{font-size:12px;text-transform:uppercase;letter-spacing:.9px;color:var(--dim2);
  margin:0 0 9px;font-weight:600}

/* ---------- snippets ---------- */
.snip{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:8px;padding:11px 13px;margin-bottom:8px;font-size:13.5px;color:#c8cfdb;
  white-space:pre-wrap;word-break:break-word;max-height:340px;overflow:auto;line-height:1.65}
.snip .from{display:block;font-size:11px;color:var(--dim2);margin-bottom:6px}
.snip .from a{color:var(--dim)}

/* ---------- posts ---------- */
.posts{display:flex;flex-direction:column;gap:6px}
.post{display:flex;gap:10px;align-items:baseline;background:var(--card);border:1px solid var(--line);
  border-radius:8px;padding:9px 12px;font-size:13px}
.post .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt)}
.post .m{color:var(--dim2);font-size:11.5px;white-space:nowrap;font-variant-numeric:tabular-nums}

/* ---------- editor ---------- */
.editor-wrap{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--code)}
.editor-bar{display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;background:var(--card2);border-bottom:1px solid var(--line);font-size:12px;color:var(--dim)}
.editor-bar .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--accent);margin-right:6px}
textarea.code{width:100%;min-height:180px;background:var(--code);color:#c9d1d9;border:0;
  padding:13px;font-family:"SF Mono",ui-monospace,Menlo,Consolas,"Liberation Mono",monospace;
  font-size:13px;line-height:1.6;resize:vertical;outline:none;tab-size:4}
.runs{display:flex;gap:8px;padding:9px 12px;background:var(--card2);border-top:1px solid var(--line);flex-wrap:wrap}
button{font-family:inherit;font-size:13px;border-radius:8px;border:1px solid var(--line);
  background:var(--card);color:var(--txt);padding:7px 15px;cursor:pointer;transition:.15s}
button:hover{border-color:var(--dim2)}
button.primary{background:var(--accent);border-color:var(--accent);color:#04120e;font-weight:600}
button.primary:disabled{opacity:.5;cursor:wait}
button.ghost{font-size:12px;padding:5px 11px}
.out{background:#05070a;border-top:1px solid var(--line);padding:12px 13px;font-family:"SF Mono",ui-monospace,Menlo,monospace;
  font-size:12.5px;line-height:1.6;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:auto;display:none;color:#c9d1d9}
.out.show{display:block}
.out .err{color:#f87171}
.out .ok{color:var(--accent2)}
.out .label{color:var(--dim2);font-size:11px;text-transform:uppercase;letter-spacing:.6px;display:block;margin-bottom:6px}
.hint{font-size:11.5px;color:var(--dim2);margin-top:6px}
.empty{text-align:center;padding:60px 20px;color:var(--dim2)}
footer{text-align:center;padding:36px 16px;color:var(--dim2);font-size:12px;line-height:1.9}
.backtop{position:fixed;right:16px;bottom:16px;width:44px;height:44px;border-radius:50%;
  background:var(--card);border:1px solid var(--line);display:none;place-items:center;
  font-size:18px;cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.5);z-index:50;color:var(--dim)}
.backtop.show{display:grid}
/* ---- 移动端：折叠筛选 + 紧凑卡片 ---- */
.fbtn{display:none}
.fbody{}
@media(max-width:640px){
  body{font-size:15px}
  .wrap{padding:0 10px 70px}
  header{padding:18px 0 12px}
  h1{font-size:21px}
  .sub{font-size:12px;line-height:1.5}
  .stats{gap:6px;margin-top:10px}
  .stat{padding:6px 9px;font-size:11px;border-radius:8px}
  .stat b{font-size:13px}

  /* 筛选：默认折叠 */
  .filters{padding:9px 0}
  .searchrow{gap:6px;margin-bottom:0}
  input[type=search],select{padding:9px 12px;font-size:14px;border-radius:9px}
  select{max-width:96px}
  .fbtn{display:flex;align-items:center;gap:6px;margin-top:8px;padding:8px 12px;
    background:var(--card);border:1px solid var(--line);border-radius:9px;
    font-size:13px;color:var(--dim);cursor:pointer;user-select:none}
  .fbtn i{margin-left:auto;font-style:normal;transition:.2s;font-size:11px}
  .fbtn.open i{transform:rotate(180deg)}
  #fcount{color:var(--accent2);font-variant-numeric:tabular-nums}
  .fbody{display:none;padding-top:8px}
  .fbody.open{display:block}
  .chips{gap:5px;padding-bottom:5px;-webkit-overflow-scrolling:touch}
  .chip{padding:6px 11px;font-size:12px}

  /* 卡片 */
  .list{gap:9px}
  .card{border-radius:12px}
  .head{padding:12px 12px;gap:9px}
  .rank{flex-basis:28px;height:28px;font-size:10.5px;border-radius:8px}
  .title{font-size:15px;line-height:1.45;margin-bottom:6px}
  .tags{gap:4px}
  .tag{font-size:10.5px;padding:2px 7px}
  .metrics{gap:10px;font-size:11.5px;margin-top:6px}
  .panel{padding:12px}
  .sec{margin-bottom:15px}
  .sec h3{font-size:11px;margin-bottom:7px}
  .snip{font-size:14px;line-height:1.7;padding:10px 11px;max-height:280px}
  .post{padding:8px 10px;font-size:13px;gap:7px}
  .post .t{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;
    -webkit-box-orient:vertical;overflow:hidden;line-height:1.45}
  .post .m{font-size:11px}

  /* 编辑器：手机上更宽松 */
  textarea.code{min-height:200px;font-size:13px;padding:11px;line-height:1.65}
  .editor-bar{font-size:11.5px;padding:7px 11px}
  .runs{padding:8px 10px;gap:6px}
  button{padding:8px 14px;font-size:13.5px}
  button.ghost{padding:6px 11px;font-size:12.5px}
  .out{font-size:12px;max-height:240px}
  .hint{font-size:11px}

  /* 全屏编辑 */
  .editor-wrap.fs{position:fixed;inset:0;z-index:200;border-radius:0;
    display:flex;flex-direction:column;background:var(--bg)}
  .editor-wrap.fs textarea.code{flex:1;min-height:0;font-size:15px;
    max-height:none;resize:none}
  .editor-wrap.fs .out{max-height:40vh}
  .backtop{bottom:14px;right:12px;width:40px;height:40px;font-size:16px}
}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1><span class="g">OpenAI</span> 面试题库</h1>
  <p class="sub">数据来自一亩三分地 /bbs/ 论坛 openai 面经帖，已去重归类 · 生成于 __GEN__</p>
  <div class="stats">
    <div class="stat"><b>__NQ__</b>道题</div>
    <div class="stat"><b>__NP__</b>篇原帖</div>
    <div class="stat"><b>__NC__</b>万字正文</div>
    <div class="stat"><b id="shown">0</b>条当前筛选</div>
  </div>
</header>

<div class="filters">
  <div class="searchrow">
    <input type="search" id="q" placeholder="搜题目、标签、原帖标题…">
    <select id="sort">
      <option value="heat">按热度</option>
      <option value="name">按名称</option>
      <option value="cat">按分类</option>
    </select>
  </div>
  <div class="fbtn" id="fbtn">筛选 <span id="fcount"></span><i>▾</i></div>
  <div class="fbody" id="fbody">
    <div class="chips" id="catChips"></div>
    <div class="chips" id="roleChips"></div>
    <div class="chips" id="stageChips"></div>
  </div>
</div>

<div class="list" id="list"></div>
<div class="empty" id="empty" style="display:none">没有匹配的题目，清一下筛选试试</div>

<footer>
  数据源：一亩三分地论坛 openai 面经帖 · <span id="fmeta"></span><br>
  原帖链接指向 1point3acres.com，部分内容需论坛积分<br>
  Python 在浏览器本地运行（Pyodide），代码不上传任何服务器
</footer>
</div>
<div class="backtop" id="backtop">↑</div>

<script id="DATA" type="application/json">__DATA__</script>
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>
<script>
const D = JSON.parse(document.getElementById('DATA').textContent);
const state = {cat:new Set(), role:new Set(), stage:new Set(), q:'', sort:'heat'};

/* ---------- chips ---------- */
function buildChips(el, items, key){
  el.innerHTML = items.map(it=>{
    const id = it.id ?? it;
    const label = it.name ?? it;
    const n = it.count ?? '';
    return `<div class="chip" data-k="${key}" data-v="${id}">${label}${n!==''?`<span class="n">${n}</span>`:''}</div>`;
  }).join('');
}
buildChips(document.getElementById('catChips'), D.categories, 'cat');
const roleNames={swe:'SWE',mle:'MLE',research:'Research',infra:'Infra',pm:'PM',ds:'DS',em:'EM',all:'通用'};
buildChips(document.getElementById('roleChips'), D.roles.map(r=>({id:r.id,name:roleNames[r.id]||r.id,count:r.count})), 'role');
buildChips(document.getElementById('stageChips'), D.stages.map(s=>({id:s,name:s})), 'stage');

document.querySelectorAll('.chip').forEach(c=>{
  c.onclick=()=>{
    const k=c.dataset.k, v=c.dataset.v;
    if(state[k].has(v)){state[k].delete(v);c.classList.remove('on')}
    else{state[k].add(v);c.classList.add('on')}
    render();
  };
});

/* ---------- search / sort ---------- */
document.getElementById('q').oninput=e=>{state.q=e.target.value.trim().toLowerCase();render()};
const fbtn=document.getElementById('fbtn'), fbody=document.getElementById('fbody');
fbtn.onclick=()=>{fbody.classList.toggle('open');fbtn.classList.toggle('open')};
document.getElementById('sort').onchange=e=>{state.sort=e.target.value;render()};

/* ---------- render ---------- */
const CATNAME={coding:'Coding','system-design':'System Design',behavioral:'Behavioral',other:'Other'};
function match(q){
  if(state.cat.size && !state.cat.has(q.category)) return false;
  if(state.role.size && !q.roles.some(r=>state.role.has(r))) return false;
  if(state.stage.size && !q.stages.some(s=>state.stage.has(s))) return false;
  if(state.q){
    const hay=(q.name+' '+(q.name_en||'')+' '+q.category+' '+q.roles.join(' ')+' '+
      (q.tags||[]).join(' ')+' '+q.posts.map(p=>p.title).join(' ')).toLowerCase();
    if(!hay.includes(state.q)) return false;
  }
  return true;
}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}

function render(){
  let qs=D.questions.filter(match);
  if(state.sort==='heat') qs.sort((a,b)=>b.heat-a.heat||a.name.localeCompare(b.name,'zh'));
  else if(state.sort==='name') qs.sort((a,b)=>a.name.localeCompare(b.name,'zh'));
  else qs.sort((a,b)=>a.category.localeCompare(b.category)||b.heat-a.heat);

  document.getElementById('shown').textContent=qs.length;
  const nf=state.cat.size+state.role.size+state.stage.size;
  const fc=document.getElementById('fcount');
  if(fc) fc.textContent=nf?`(${nf})`:'';
  document.getElementById('empty').style.display=qs.length?'none':'block';

  document.getElementById('list').innerHTML=qs.map((q,i)=>{
    const hot=q.heat>=10?'hot':'';
    const roles=q.roles.map(r=>`<span class="tag">${roleNames[r]||r}</span>`).join('');
    const stages=q.stages.map(s=>`<span class="tag">${s}</span>`).join('');
    const snips=(q.snippets||[]).map(s=>
      `<div class="snip"><span class="from">原帖 <a href="https://www.1point3acres.com/bbs/thread-${s.tid}-1-1.html" target="_blank" rel="noopener">${s.tid}</a></span>${esc(s.text)}</div>`
    ).join('') || '<div class="snip">该题在已抓帖子中暂无题面摘录</div>';
    const posts=(q.posts||[]).slice(0,10).map(p=>
      `<div class="post"><a class="t" href="${p.url}" target="_blank" rel="noopener">${esc(p.title)}</a>
       <span class="m">${p.floors} 楼 · ${p.chars.toLocaleString()} 字</span></div>`
    ).join('');
    const more=(q.posts||[]).length>10?`<div class="hint">另有 ${q.posts.length-10} 篇相关原帖</div>`:'';

    const editor = q.runnable ? `
      <div class="sec">
        <h3>Python 运行环境</h3>
        <div class="editor-wrap">
          <div class="editor-bar"><span><span class="dot"></span>main.py</span><span>Pyodide · 浏览器本地执行</span></div>
          <textarea class="code" id="code-${q.id}" spellcheck="false">${esc(templateFor(q))}</textarea>
          <div class="runs">
            <button class="primary" onclick="runPy('${q.id}',this)">▶ 运行</button>
            <button class="ghost" onclick="resetPy('${q.id}')">重置</button>
            <button class="ghost" onclick="copyPy('${q.id}',this)">复制</button>
            <button class="ghost fs" onclick="fullPy('${q.id}')">全屏</button>
          </div>
          <div class="out" id="out-${q.id}"></div>
        </div>
        <div class="hint">首次运行需下载 Python 运行时（约 10MB），之后秒开</div>
      </div>` : '';

    return `<div class="card" id="card-${q.id}">
      <div class="head" onclick="toggle('${q.id}',event)">
        <div class="rank ${hot}">${i+1}</div>
        <div class="body">
          <div class="title">${esc(q.name)}</div>
          <div class="tags">
            <span class="tag cat-${q.category}">${CATNAME[q.category]||q.category}</span>
            ${q.heat?`<span class="tag heat">${q.heat} 篇帖子提到</span>`:''}
            ${q.runnable?'<span class="tag run">可运行</span>':''}
            ${roles}${stages}
          </div>
          <div class="metrics">
            <span>关联原帖 <b>${(q.posts||[]).length}</b></span>
            <span>题面摘录 <b>${(q.snippets||[]).length}</b></span>
            ${q.frequency?`<span>官方频率 <b>${q.frequency}</b></span>`:''}
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="sec"><h3>题面摘录（来自原帖）</h3>${snips}</div>
        ${posts?`<div class="sec"><h3>关联原帖</h3><div class="posts">${posts}</div>${more}</div>`:''}
        ${editor}
      </div>
    </div>`;
  }).join('');
}

function toggle(id,e){
  if(e && e.target.tagName==='A') return;
  document.getElementById('card-'+id).classList.toggle('open');
}

/* ---------- python ---------- */
let pyodide=null, loading=null;
function ensurePy(){
  if(pyodide) return Promise.resolve(pyodide);
  if(loading) return loading;
  loading = loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"}).then(py=>{
    pyodide=py; return py;
  });
  return loading;
}
function templateFor(q){
  const n=q.name;
  return `# ${n}
# 这是 OpenAI 面经里的原题，先写下你的思路再运行验证

import sys, io

def solve(*args, **kwargs):
    # TODO: 按题面实现
    raise NotImplementedError("先实现 solve()")

# ---- 本地测试 ----
if __name__ == "__main__":
    print("题面：${n.replace(/"/g,'')}")
    print("把思路写下来，用 assert 验证边界条件")
    # 示例：assert solve(...) == ...
    print("(改这块，然后点运行)")
`;
}
function fullPy(id){
  const w=document.querySelector('#card-'+id+' .editor-wrap');
  if(!w) return;
  w.classList.toggle('fs');
  if(w.classList.contains('fs')){
    document.body.style.overflow='hidden';
    w.querySelector('.fs').textContent='退出';
  }else{
    document.body.style.overflow='';
    w.querySelector('.fs').textContent='全屏';
  }
}
function resetPy(id){
  const q=D.questions.find(x=>x.id===id);
  document.getElementById('code-'+id).value=templateFor(q);
}
function copyPy(id,btn){
  const ta=document.getElementById('code-'+id);
  navigator.clipboard.writeText(ta.value).then(()=>{
    const t=btn.textContent; btn.textContent='已复制'; setTimeout(()=>btn.textContent=t,1200);
  });
}
async function runPy(id,btn){
  const out=document.getElementById('out-'+id);
  const code=document.getElementById('code-'+id).value;
  out.className='out show';
  out.innerHTML='<span class="label">运行中</span>正在加载 Python 运行时…';
  btn.disabled=true; btn.textContent='运行中…';
  try{
    const py=await ensurePy();
    py.setStdout({batched:(s)=>{}});
    const buf=[];
    py.setStdout({batched:s=>buf.push(s)});
    py.setStderr({batched:s=>buf.push(s)});
    let err=null;
    try{
      await py.runPythonAsync(code);
    }catch(e){ err=e.message||String(e); }
    const txt=buf.join('');
    out.innerHTML = (txt?`<span class="label">输出</span>${esc(txt)}`:'')
      + (err?`<span class="label">报错</span><span class="err">${esc(err)}</span>`:
         (txt?'':'<span class="ok">运行完成，没有输出</span>'));
  }catch(e){
    out.innerHTML=`<span class="label">失败</span><span class="err">${esc(e.message||e)}</span>`;
  }finally{
    btn.disabled=false; btn.textContent='▶ 运行';
  }
}

/* ---------- misc ---------- */
document.getElementById('fmeta').textContent =
  `${D.meta.questions} 道题 / ${D.meta.posts} 篇原帖`;
const bt=document.getElementById('backtop');
window.addEventListener('scroll',()=>{bt.classList.toggle('show',window.scrollY>600)});
bt.onclick=()=>window.scrollTo({top:0,behavior:'smooth'});

render();
</script>
</body>
</html>
"""

html = (HTML.replace("__DATA__", blob)
            .replace("__GEN__", meta["generated"])
            .replace("__NQ__", str(meta["questions"]))
            .replace("__NP__", str(meta["posts"]))
            .replace("__NC__", f'{meta["total_chars"]/10000:.0f}'))
open(OUT, "w").write(html)
print(f"[+] {OUT}  {os.path.getsize(OUT)/1024:.0f} KB")
