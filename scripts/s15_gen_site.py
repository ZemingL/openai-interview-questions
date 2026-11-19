#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s15_gen_site.py — 生成 LeetCode 风格单文件站点（列表 → 详情 → 折叠答案 + 浏览器内 Python）"""
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
<title>OpenAI Interview Questions</title>
<style>
:root{
  --bg:#0b0e14;--bg2:#11151f;--card:#151a24;--card2:#1b212d;
  --line:#232a38;--txt:#e8ebf1;--dim:#8b95a8;--dim2:#5b6577;
  --ac:#10a37f;--ac2:#1ed7a4;--code:#0c1017;
  --coding:#10a37f;--sd:#5b8cff;--bq:#c084fc;--other:#f59e0b;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",Roboto,sans-serif;
  font-size:15px;line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--ac2);text-decoration:none}
.hide{display:none!important}

/* ---------- 顶栏 ---------- */
.top{position:sticky;top:0;z-index:40;background:rgba(11,14,20,.96);
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-bottom:1px solid var(--line)}
.topin{max-width:900px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:12px}
.brand{font-weight:700;font-size:17px;letter-spacing:-.3px;flex:1;min-width:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand .g{background:linear-gradient(90deg,var(--ac),var(--ac2));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.lang{display:flex;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:2px;flex:0 0 auto}
.lang span{padding:4px 10px;font-size:12.5px;color:var(--dim);cursor:pointer;border-radius:6px;user-select:none}
.lang span.on{background:var(--ac);color:#04120e;font-weight:600}

.wrap{max-width:900px;margin:0 auto;padding:0 16px 70px}

/* ---------- 列表页 ---------- */
.searchrow{padding:14px 0 8px;display:flex;gap:8px}
input[type=search]{flex:1;background:var(--card);border:1px solid var(--line);color:var(--txt);
  border-radius:10px;padding:10px 14px;font-size:14.5px;outline:none;font-family:inherit}
input[type=search]:focus{border-color:var(--ac)}
.tabs{display:flex;gap:6px;overflow-x:auto;padding-bottom:10px;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{flex:0 0 auto;padding:6px 14px;border-radius:999px;background:var(--card);
  border:1px solid var(--line);color:var(--dim);font-size:13px;cursor:pointer;white-space:nowrap;user-select:none}
.tab.on{background:var(--ac);border-color:var(--ac);color:#04120e;font-weight:600}

.qlist{border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:4px}
.qrow{display:flex;align-items:center;gap:12px;padding:13px 16px;background:var(--card);
  border-bottom:1px solid var(--line);cursor:pointer;transition:.12s}
.qrow:last-child{border-bottom:0}
.qrow:hover{background:var(--card2)}
.qrow.done{opacity:.65}
.qnum{flex:0 0 34px;color:var(--dim2);font-size:13px;font-variant-numeric:tabular-nums}
.qname{flex:1;min-width:0;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qmeta{flex:0 0 auto;display:flex;gap:6px;align-items:center}
.dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
.dot.coding{background:var(--coding)}.dot.system-design{background:var(--sd)}
.dot.behavioral{background:var(--bq)}.dot.other{background:var(--other)}
.qheat{font-size:11.5px;color:var(--dim2);font-variant-numeric:tabular-nums}
.chev{color:var(--dim2);font-size:16px;flex:0 0 auto}

/* ---------- 详情页 ---------- */
.back{display:inline-flex;align-items:center;gap:6px;color:var(--dim);font-size:14px;
  padding:14px 0 10px;cursor:pointer}
.back:hover{color:var(--txt)}
.dtitle{font-size:21px;font-weight:700;line-height:1.4;margin:0 0 10px;letter-spacing:-.3px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px}
.tag{font-size:11.5px;padding:3px 9px;border-radius:6px;background:var(--card2);
  color:var(--dim);border:1px solid var(--line)}
.tag.coding{background:rgba(16,163,127,.14);color:var(--ac2);border-color:rgba(16,163,127,.28)}
.tag.system-design{background:rgba(91,140,255,.14);color:#8aa9ff;border-color:rgba(91,140,255,.28)}
.tag.behavioral{background:rgba(192,132,252,.14);color:#d8b4fe;border-color:rgba(192,132,252,.28)}
.tag.other{background:rgba(245,158,11,.14);color:#fbbf24;border-color:rgba(245,158,11,.28)}
.tag.hot{background:rgba(239,68,68,.12);color:#f87171;border-color:rgba(239,68,68,.26)}

.block{margin-bottom:22px}
.block h2{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--dim2);
  margin:0 0 10px;font-weight:600}
.stmt{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;
  font-size:14.5px;line-height:1.8;white-space:pre-wrap;word-break:break-word;color:#cdd4e0}
.stmt .from{display:block;font-size:11.5px;color:var(--dim2);margin-top:10px}

/* 编辑器 */
.ed{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--code)}
.edbar{display:flex;justify-content:space-between;align-items:center;padding:8px 13px;
  background:var(--card2);border-bottom:1px solid var(--line);font-size:12px;color:var(--dim)}
.edbar .dot2{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ac);margin-right:6px}
textarea.code{width:100%;min-height:230px;background:var(--code);color:#cdd9e5;border:0;
  padding:14px;font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:13.5px;
  line-height:1.65;resize:vertical;outline:none;tab-size:4}
/* CodeMirror 适配 */
.CodeMirror{height:auto!important;min-height:230px;background:var(--code)!important;
  color:#cdd9e5!important;font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace!important;
  font-size:13.5px!important;line-height:1.65!important;padding:6px 0}
.CodeMirror-gutters{background:var(--code)!important;border-right:1px solid var(--line)!important}
.CodeMirror-linenumber{color:#3e4859!important;font-size:12px!important}
.CodeMirror-cursor{border-left:2px solid var(--ac2)!important}
.CodeMirror-selected{background:rgba(16,163,127,.18)!important}
.CodeMirror-activeline-background{background:rgba(255,255,255,.025)!important}
.CodeMirror-matchingbracket{color:var(--ac2)!important;border-bottom:1px solid var(--ac2)}
.cm-s-material-darker .cm-keyword{color:#c792ea!important}
.cm-s-material-darker .cm-def{color:#82aaff!important}
.cm-s-material-darker .cm-string{color:#c3e88d!important}
.cm-s-material-darker .cm-number{color:#f78c6c!important}
.cm-s-material-darker .cm-comment{color:#546e7a!important;font-style:italic}
.cm-s-material-darker .cm-builtin{color:#ffcb6b!important}
.cm-s-material-darker .cm-variable{color:#cdd9e5!important}
.cm-s-material-darker .cm-operator{color:#89ddff!important}
.ed.fs{position:fixed!important;top:0!important;left:0!important;right:0!important;bottom:0!important;
  width:100vw!important;height:100dvh!important;max-width:none!important;margin:0!important;
  z-index:200;border-radius:0;display:flex;flex-direction:column;background:var(--bg);padding:0}
.ed.fs .edbar,.ed.fs .edact{flex:0 0 auto}
.ed.fs textarea.code{flex:1;min-height:0;resize:none;font-size:15px}
.ed.fs .out{max-height:38vh;flex:0 0 auto}
.ed.fs .CodeMirror{flex:1 1 auto;height:auto!important;min-height:0;max-height:none}
.ed.fs .CodeMirror-scroll{max-height:none;min-height:100%}
.ed.fs .CodeMirror-sizer{min-height:100%!important}
.edact{display:flex;gap:8px;padding:9px 13px;background:var(--card2);border-top:1px solid var(--line);flex-wrap:wrap}
button{font-family:inherit;font-size:13.5px;border-radius:8px;border:1px solid var(--line);
  background:var(--card);color:var(--txt);padding:7px 16px;cursor:pointer;transition:.14s}
button:hover{border-color:var(--dim2)}
button.primary{background:var(--ac);border-color:var(--ac);color:#04120e;font-weight:600}
button.primary:disabled{opacity:.5}
button.ghost{font-size:12.5px;padding:6px 12px}
.out{display:none;padding:12px 14px;background:#05070a;border-top:1px solid var(--line);
  font-family:"SF Mono",ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.65;
  white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:auto;color:#cdd9e5}
.out.show{display:block}
.out .lbl{display:block;font-size:10.5px;letter-spacing:.8px;color:var(--dim2);
  text-transform:uppercase;margin-bottom:6px}
.out .err{color:#f87171}.out .ok{color:var(--ac2)}

/* 答案折叠 */
details.ans{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
details.ans summary{padding:14px 16px;cursor:pointer;font-size:14.5px;font-weight:600;
  color:var(--txt);list-style:none;display:flex;align-items:center;gap:8px;user-select:none}
details.ans summary::-webkit-details-marker{display:none}
details.ans summary::before{content:"▸";color:var(--ac);transition:.2s;display:inline-block}
details.ans[open] summary::before{transform:rotate(90deg)}
details.ans summary .cnt{font-size:12px;color:var(--dim2);font-weight:400;margin-left:auto}
.ansbody{padding:0 16px 16px;border-top:1px solid var(--line)}
.ansbody .piece{background:var(--bg2);border:1px solid var(--line);border-left:3px solid var(--ac);
  border-radius:9px;padding:13px;margin-top:13px;font-size:14px;line-height:1.8;
  white-space:pre-wrap;word-break:break-word;color:#cdd4e0;max-height:420px;overflow:auto}
.ansbody .src{display:block;font-size:11.5px;color:var(--dim2);margin-top:9px}
.ansbody .empty{color:var(--dim2);font-size:13.5px;padding:14px 0}

.empty{text-align:center;padding:56px 20px;color:var(--dim2);font-size:14px}
footer{text-align:center;padding:34px 16px;color:var(--dim2);font-size:12px;line-height:1.9}

@media(max-width:640px){
  .topin{padding:10px 12px}
  .brand{font-size:16px}
  .wrap{padding:0 12px 60px}
  .qrow{padding:12px 13px;gap:9px}
  .qnum{flex-basis:28px;font-size:12px}
  .qname{font-size:14.5px}
  .qheat{display:none}
  .dtitle{font-size:18.5px}
  .stmt{padding:13px;font-size:14px}
  textarea.code{min-height:210px;font-size:13px;padding:12px}
  button{padding:8px 15px;font-size:13.5px}
  .ansbody .piece{font-size:13.5px;max-height:340px}
  details.ans summary{padding:12px 13px;font-size:14px}
  .ansbody{padding:0 13px 14px}

}
</style>
</head>
<body>

<div class="top">
  <div class="topin">
    <div class="brand" id="brand"><span class="g">OpenAI</span> <span id="bTitle">题库</span></div>
    <div class="lang" id="lang"><span data-l="zh">中</span><span data-l="en">EN</span></div>
  </div>
</div>

<div class="wrap">
  <!-- 列表 -->
  <div id="listView">
    <div class="searchrow">
      <input type="search" id="qInput" placeholder="搜索题目…">
    </div>
    <div class="tabs" id="tabs"></div>
    <div class="qlist" id="qlist"></div>
    <div class="empty hide" id="listEmpty"></div>
  </div>

  <!-- 详情 -->
  <div id="detailView" class="hide"></div>
</div>

<footer id="foot"></footer>

<script id="DATA" type="application/json">__DATA__</script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/lib/codemirror.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/theme/material-darker.min.css">
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/lib/codemirror.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/mode/python/python.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/edit/matchbrackets.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/edit/closebrackets.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/codemirror@5.65.16/addon/selection/active-line.min.js"></script>
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>
<script>
const D = JSON.parse(document.getElementById('DATA').textContent);
const QS = D.questions;
const byId = {}; QS.forEach((q,i)=>{q._n=i+1; byId[q.id]=q;});

/* ---------------- i18n ---------------- */
const T={
 zh:{bTitle:'题库',search:'搜索题目…',all:'全部',
    coding:'Coding',sd:'系统设计',bq:'行为面',other:'其他',
    stmt:'题目描述',runtime:'写代码',answer:'查看答案',noAns:'该题原帖未给出完整解法',
    run:'▶ 运行',reset:'重置',copy:'复制',full:'全屏',exit:'退出',
    output:'输出',err:'报错',running:'运行中',done:'运行完成，没有输出',
    loadHint:'首次运行需下载 Python 运行时（约 10MB）',
    back:'返回列表',mentions:n=>`${n} 篇帖子提到`,src:'来自原帖',
    empty:'没有匹配的题目',foot:'数据来自公开社区论坛的 OpenAI 面经帖 · Python 在浏览器本地运行',
    noStmt:'原帖未提供可摘录的描述'},
 en:{bTitle:'Questions',search:'Search questions…',all:'All',
    coding:'Coding',sd:'System Design',bq:'Behavioral',other:'Other',
    stmt:'Description',runtime:'Code',answer:'Show answer',noAns:'No full solution in the original posts',
    run:'▶ Run',reset:'Reset',copy:'Copy',full:'Fullscreen',exit:'Exit',
    output:'Output',err:'Error',running:'Running',done:'Finished with no output',
    loadHint:'First run downloads the Python runtime (~10MB)',
    back:'Back to list',mentions:n=>`in ${n} posts`,src:'from post',
    empty:'No matching questions',foot:'Data from public community forum OpenAI interview posts · Python runs locally in your browser',
    noStmt:'No description captured from the original posts'}
};
let LANG = localStorage.getItem('lang') || ((navigator.language||'en').toLowerCase().startsWith('zh')?'zh':'en');
const t=k=>T[LANG][k];
const qName=q=>LANG==='en'?(q.name_en||q.name):q.name;
const catLabel=c=>({coding:t('coding'),'system-design':t('sd'),behavioral:t('bq'),other:t('other')})[c]||c;

/* ---------------- 状态 ---------------- */
const st={cat:'all', q:'', done:new Set(JSON.parse(localStorage.getItem('done')||'[]'))};

/* ---------------- 视图切换 ---------------- */
function route(){
  const h=location.hash||'#/';
  const m=h.match(/^#\/q\/(.+)$/);
  if(m && byId[m[1]]){ showDetail(byId[m[1]]); }
  else { showList(); }
}
window.addEventListener('hashchange',route);

function showList(){
  document.getElementById('listView').classList.remove('hide');
  document.getElementById('detailView').classList.add('hide');
  document.getElementById('foot').classList.remove('hide');
  renderList();
  window.scrollTo(0,0);
}

function showDetail(q){
  document.getElementById('listView').classList.add('hide');
  document.getElementById('foot').classList.add('hide');
  const v=document.getElementById('detailView');
  v.classList.remove('hide');
  v.innerHTML = detailHTML(q);
  window.scrollTo(0,0);
  attachDetail(q);
}

/* ---------------- 列表渲染 ---------------- */
function renderList(){
  document.getElementById('brand').innerHTML='<span class="g">OpenAI</span> <span id="bTitle">'+t('bTitle')+'</span>';
  document.getElementById('qInput').placeholder=t('search');
  document.getElementById('listEmpty').textContent=t('empty');
  document.getElementById('foot').textContent=t('foot');

  const cats=[['all',t('all')],['coding',t('coding')],['system-design',t('sd')],['behavioral',t('bq')],['other',t('other')]];
  document.getElementById('tabs').innerHTML=cats.map(([k,label])=>{
    const n=k==='all'?QS.length:QS.filter(q=>q.category===k).length;
    return `<div class="tab ${st.cat===k?'on':''}" data-c="${k}">${label} <span style="opacity:.6">${n}</span></div>`;
  }).join('');
  document.querySelectorAll('.tab').forEach(el=>el.onclick=()=>{st.cat=el.dataset.c;renderList();});

  let list=QS.filter(q=>{
    if(st.cat!=='all'&&q.category!==st.cat) return false;
    if(st.q){
      const hay=(q.name+' '+(q.name_en||'')+' '+q.category+' '+(q.roles||[]).join(' ')).toLowerCase();
      if(!hay.includes(st.q)) return false;
    }
    return true;
  });

  document.getElementById('listEmpty').classList.toggle('hide',list.length>0);
  document.getElementById('qlist').innerHTML=list.map(q=>`
    <div class="qrow ${st.done.has(q.id)?'done':''}" data-id="${q.id}">
      <div class="qnum">${q._n}.</div>
      <div class="qname">${esc(qName(q))}</div>
      <div class="qmeta">
        <span class="dot ${q.category}"></span>
        <span class="qheat">${q.heat||0}</span>
      </div>
      <div class="chev">›</div>
    </div>`).join('');
  document.querySelectorAll('.qrow').forEach(el=>{
    el.onclick=()=>{location.hash='#/q/'+el.dataset.id;};
  });
}

/* ---------------- 详情渲染 ---------------- */
function detailHTML(q){
  const tags = `<span class="tag ${q.category}">${catLabel(q.category)}</span>`
    + (q.heat?`<span class="tag hot">${t('mentions')(q.heat)}</span>`:'')
    + (q.roles||[]).map(r=>`<span class="tag">${(r||'').toUpperCase()}</span>`).join('');

  const stmt = (q.snippets&&q.snippets.length)
    ? q.snippets.slice(0,3).map(s=>
        `<div class="stmt">${esc(s.text)}<span class="from">${t('src')} #${s.tid}</span></div>`
      ).join('<div style="height:10px"></div>')
    : `<div class="stmt" style="color:var(--dim2)">${t('noStmt')}</div>`;

  const editor = q.runnable ? `
    <div class="block">
      <h2>${t('runtime')}</h2>
      <div class="ed" id="ed-${q.id}">
        <div class="edbar"><span><span class="dot2"></span>main.py</span><span>Pyodide</span></div>
        <textarea class="code" spellcheck="false" id="code-${q.id}">${esc(tpl(q))}</textarea>
        <div class="edact">
          <button class="primary" data-act="run">${t('run')}</button>
          <button class="ghost" data-act="reset">${t('reset')}</button>
          <button class="ghost" data-act="copy">${t('copy')}</button>
          <button class="ghost" data-act="fs">${t('full')}</button>
        </div>
        <div class="out" id="out-${q.id}"></div>
      </div>
    </div>` : '';

  const ans = (q.answer&&q.answer.length) ? `
    <div class="block">
      <details class="ans">
        <summary>${t('answer')}<span class="cnt">${q.answer.length}</span></summary>
        <div class="ansbody">
          ${q.answer.map(a=>`<div class="piece">${esc(a.text)}<span class="src">${t('src')} #${a.tid}</span></div>`).join('')}
        </div>
      </details>
    </div>`
    : `<div class="block"><details class="ans"><summary>${t('answer')}<span class="cnt">0</span></summary>
        <div class="ansbody"><div class="empty" style="padding:14px 0">${t('noAns')}</div></div></details></div>`;

  return `
    <div class="back" id="backBtn">‹ ${t('back')}</div>
    <h1 class="dtitle">${q._n}. ${esc(qName(q))}</h1>
    <div class="tags">${tags}</div>
    <div class="block"><h2>${t('stmt')}</h2>${stmt}</div>
    ${editor}
    ${ans}`;
}

function attachDetail(q){
  document.getElementById('backBtn').onclick=()=>{location.hash='#/';};
  if(!q.runnable) return;
  const ed=document.getElementById('ed-'+q.id);
  const ta=document.getElementById('code-'+q.id);
  const out=document.getElementById('out-'+q.id);

  // ---- CodeMirror 初始化（CDN 失败则退回原生 textarea）----
  let cm=null;
  if(window.CodeMirror){
    cm=CodeMirror.fromTextArea(ta,{
      mode:{name:'python',version:3,singleLineStringErrors:false},
      theme:'material-darker',lineNumbers:true,lineWrapping:true,
      matchBrackets:true,autoCloseBrackets:true,indentUnit:4,tabSize:4,
      styleActiveLine:true,viewportMargin:Infinity
    });
    setTimeout(()=>{ try{cm.refresh();}catch(e){} },60);
  }
  const getCode=()=>cm?cm.getValue():ta.value;
  const setCode=v=>{ if(cm) cm.setValue(v); else ta.value=v; };

  ed.querySelectorAll('[data-act]').forEach(b=>{
    b.onclick=()=>{
      const a=b.dataset.act;
      if(a==='run') runPy(q,getCode(),out,b);
      else if(a==='reset'){ setCode(tpl(q)); }
      else if(a==='copy'){ navigator.clipboard.writeText(getCode()).then(()=>{const o=b.textContent;b.textContent='✓';setTimeout(()=>b.textContent=o,1100);}); }
      else if(a==='fs'){
        ed.classList.toggle('fs');
        b.textContent = ed.classList.contains('fs')?t('exit'):t('full');
        document.body.style.overflow = ed.classList.contains('fs')?'hidden':'';
        setTimeout(()=>{ if(cm) cm.refresh(); },80);
        if(ed.classList.contains('fs') && ed.scrollIntoView) ed.scrollIntoView({block:'start'});
      }
    };
  });
}

/* ---------------- Python ---------------- */
let pyodide=null, loading=null;
function ensurePy(){
  if(pyodide) return Promise.resolve(pyodide);
  if(loading) return loading;
  loading = loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"}).then(p=>{pyodide=p;return p;});
  return loading;
}
function tpl(q){
  const nm=qName(q);
  return `# ${nm}
# 先写思路，再动手；用 assert 验证边界

def solve(*args, **kwargs):
    # TODO
    pass

if __name__ == "__main__":
    print("${nm.replace(/"/g,'')}")
    # assert solve(...) == ...
`;
}
async function runPy(q,code,out,btn){
  out.className='out show';
  out.innerHTML=`<span class="lbl">${t('running')}</span>${t('loadHint')}`;
  btn.disabled=true; const old=btn.textContent; btn.textContent=t('running')+'…';
  try{
    const py=await ensurePy();
    const buf=[];
    py.setStdout({batched:s=>buf.push(s)});
    py.setStderr({batched:s=>buf.push(s)});
    let err=null;
    try{ await py.runPythonAsync(code); }catch(e){ err=e.message||String(e); }
    const txt=buf.join('');
    out.innerHTML = (txt?`<span class="lbl">${t('output')}</span>${esc(txt)}`:'')
      + (err?`<span class="lbl">${t('err')}</span><span class="err">${esc(err)}</span>`
           :(txt?'':`<span class="ok">${t('done')}</span>`));
  }catch(e){
    out.innerHTML=`<span class="lbl">${t('err')}</span><span class="err">${esc(e.message||e)}</span>`;
  }finally{ btn.disabled=false; btn.textContent=old; }
}

/* ---------------- 语言 ---------------- */
function applyLang(){
  document.documentElement.lang = LANG==='zh'?'zh-CN':'en';
  document.querySelectorAll('#lang span').forEach(el=>el.classList.toggle('on',el.dataset.l===LANG));
  localStorage.setItem('lang',LANG);
  route();
}
document.querySelectorAll('#lang span').forEach(el=>{
  el.onclick=()=>{LANG=el.dataset.l;applyLang();};
});
document.getElementById('qInput').oninput=e=>{st.q=e.target.value.trim().toLowerCase();renderList();};

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

/* ---------------- 启动 ---------------- */
applyLang();
</script>
</body>
</html>
"""

html = (HTML.replace("__DATA__", blob))
open(OUT, "w").write(html)
print(f"[+] {OUT}  {os.path.getsize(OUT)/1024:.0f} KB  ({len(d['questions'])} 题)")
