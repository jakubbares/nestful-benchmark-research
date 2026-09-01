'use strict';
let P=null, S=[], RUNS=[], RMETA={}, SEL=0, FOCUS='qwen3_3shot', VS='hammer_3shot';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=v=>(v*100).toFixed(1)+'%';
const fmt=v=>v===null||v===undefined?'—':(typeof v==='string'?v:JSON.stringify(v));

/* ---------- Python-compatible json.dumps(<str>) so prompts rebuild byte-exactly ---------- */
const ESCMAP={'"':'\\"','\\':'\\\\','\n':'\\n','\r':'\\r','\t':'\\t','\b':'\\b','\f':'\\f'};
function pyJsonStr(s){
  let o='"';
  for(const ch of s){
    const c=ch.codePointAt(0);
    if(ESCMAP[ch]) o+=ESCMAP[ch];
    else if(c<0x20||c>=0x7f){
      if(c>0xffff){const v=c-0x10000;
        o+='\\u'+(0xd800+(v>>10)).toString(16).padStart(4,'0')+'\\u'+(0xdc00+(v&0x3ff)).toString(16).padStart(4,'0');
      } else o+='\\u'+c.toString(16).padStart(4,'0');
    } else o+=ch;
  }
  return o+'"';
}
function toolsString(s){ return '['+s.ts.map(i=>P.specs[i]).join(', ')+']'; }
// Python's str.format() collapses {{ -> { and }} -> } ONLY in the template
// text itself, before substitution - never in the inserted values (a real
// nested "}}" from JSON inside FUNCTION_STR must survive untouched). So the
// unescape has to happen on the template first, then substitute into that.
function unescapeFormatBraces(s){ return s.replace(/\{\{/g,'{').replace(/\}\}/g,'}'); }
function buildPrompt(s,shots,model,checklist){
  // Matches run_matched.py's build_prompts(): checklist is injected before
  // [BEGIN OF QUERY] into the RAW template, ahead of any placeholder
  // substitution. The checklist text itself has no { or } characters, so
  // doing this before or after unescapeFormatBraces() is equivalent.
  const inject=tpl=>checklist?tpl.replace('[BEGIN OF QUERY]',P.prompts.checklist+'[BEGIN OF QUERY]'):tpl;
  if(model==='xLAM-7b-fc-r'){
    const tpl=inject(unescapeFormatBraces(P.prompts.templates['xLAM-7b-fc-r']));
    return tpl
      .replace('{FUNCTION_STR}',()=>pyJsonStr(toolsString(s)))
      .replace('{ICL_EXAMPLES}',()=>P.prompts.icl_str_xlam[String(shots)])
      .replace('{QUERY}',()=>s.q);
  }
  return inject(P.prompts.templates['Hammer2.0-7b'])
    .replace('{FUNCTION_STR}',()=>pyJsonStr(toolsString(s)))
    .replace('{ICL_EXAMPLES}',()=>P.prompts.icl_str[String(shots)])
    .replace('{QUERY}',()=>s.q);
}

/* ---------- stats: two-sided exact McNemar (binomial on discordant pairs) ---------- */
function lgamma(x){
  const g=[676.5203681218851,-1259.1392167224028,771.32342877765313,-176.61502916214059,
           12.507343278686905,-0.13857109526572012,9.9843695780195716e-6,1.5056327351493116e-7];
  if(x<0.5) return Math.log(Math.PI/Math.sin(Math.PI*x))-lgamma(1-x);
  x-=1; let a=0.99999999999980993, t=x+7.5;
  for(let i=0;i<8;i++) a+=g[i]/(x+i+1);
  return 0.5*Math.log(2*Math.PI)+(x+0.5)*Math.log(t)-t+Math.log(a);
}
function binomTwoSided(b,c){
  const n=b+c; if(n===0) return 1;
  const k=Math.min(b,c); let s=0;
  for(let i=0;i<=k;i++) s+=Math.exp(lgamma(n+1)-lgamma(i+1)-lgamma(n-i+1)+n*Math.log(0.5));
  return Math.min(1,2*s);
}
function pval(p){ return p<1e-6?'< 0.000001':p.toFixed(p<0.001?6:4); }

/* ---------- helpers ---------- */
const R=k=>P.runs[k];
const row=(k,i)=>P.runs[k].rows[i];
function parseGen(txt){
  try{ const v=JSON.parse(String(txt).replace(/```/g,'').trim()); return Array.isArray(v)?v:null; }
  catch(e){ return null; }
}
function argStr(a){
  if(!a||typeof a!=='object') return '';
  return Object.entries(a).map(([k,v])=>k+'='+(typeof v==='string'?v:JSON.stringify(v))).join(', ');
}
function toast(m){ const t=$('#toast'); t.textContent=m; t.classList.add('on'); clearTimeout(t._t);
  t._t=setTimeout(()=>t.classList.remove('on'),1400); }
function copy(text,msg){ navigator.clipboard.writeText(text).then(()=>toast(msg||'Copied')); }

/* ---------- filtering ---------- */
let FILTERED=[], TERMS=[];
function hl(text){
  if(!TERMS.length) return esc(text);
  let out=esc(text);
  for(const t of TERMS){
    if(t.length<2) continue;
    const re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig');
    out=out.replace(re,'<mark>$1</mark>');
  }
  return out;
}
function applyFilters(){
  const q=$('#q').value.trim().toLowerCase();
  const dom=$('#fdom').value, calls=$('#fcalls').value, diag=$('#fdiag').value;
  const vsMode=$('#fvsmode').value, vsMetric=$('#fvsmetric').value, vsDiag=$('#fvsdiag').value;
  const fr=R(FOCUS), vr=R(VS);
  const terms=q?q.split(/\s+/):[]; TERMS=terms;
  FILTERED=[];
  for(let i=0;i<S.length;i++){
    const s=S[i];
    if(dom&&s.d!==dom) continue;
    if(calls){ if(calls==='5+'){ if(s.nc<5) continue; } else if(s.nc!==+calls) continue; }
    const f=fr.rows[i];
    if(diag&&f.c!==diag) continue;
    if(vsDiag&&vr.rows[i].c!==vsDiag) continue;
    if(vsMode){
      const a=f[vsMetric], b=vr.rows[i][vsMetric];
      if(vsMode==='focus_only'&&!(a&&!b)) continue;
      if(vsMode==='vs_only'&&!(b&&!a)) continue;
      if(vsMode==='both'&&!(a&&b)) continue;
      if(vsMode==='neither'&&(a||b)) continue;
      if(vsMode==='differ'&&a===b) continue;
    }
    if(terms.length){
      if(!s._hay) s._hay=(s.q+' '+s.id+' '+s.gold.map(c=>c.name).join(' ')+' '+s.ga).toLowerCase();
      const hay=s._hay+' '+f.g.toLowerCase()+' '+(f.pn||[]).join(' ').toLowerCase();
      let ok=true;
      for(const t of terms) if(!hay.includes(t)){ ok=false; break; }
      if(!ok) continue;
    }
    FILTERED.push(i);
  }
  $('#nshown').textContent=FILTERED.length.toLocaleString();
  renderList();
  if(FILTERED.length && !FILTERED.includes(SEL)) select(FILTERED[0]);
  else if(!FILTERED.length){ SEL=-1; renderDetail(); }
}
function renderList(){
  const l=$('#list');
  if(!FILTERED.length){ l.innerHTML='<div class="empty">No samples match these filters.</div>'; return; }
  const parts=[];
  for(const i of FILTERED){
    const s=S[i];
    const dots=RUNS.filter(k=>RMETA[k].tier==='matched')
      .map(k=>`<i class="dot ${row(k,i).c}" title="${esc(RMETA[k].short)}: ${esc(P.diag_label[row(k,i).c])}"></i>`).join('');
    parts.push(`<div class="item${i===SEL?' on':''}" data-i="${i}">
      <div class="idx">${i+1}</div>
      <div class="body">
        <div class="q">${hl(s.q)}</div>
        <div class="meta"><span class="tag ${s.d}">${s.d}</span>
          <span class="tag">${s.nc} call${s.nc>1?'s':''}</span>
          <span class="dots">${dots}</span></div>
      </div></div>`);
  }
  l.innerHTML=parts.join('');
}
