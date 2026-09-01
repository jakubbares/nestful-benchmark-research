
/* ---------- align predicted chain against gold (LCS over function names) ---------- */
function align(gold,pred){
  const n=gold.length,m=pred.length;
  const d=Array.from({length:n+1},()=>new Int32Array(m+1));
  for(let i=n-1;i>=0;i--) for(let j=m-1;j>=0;j--)
    d[i][j]= gold[i].name===pred[j].name ? d[i+1][j+1]+1 : Math.max(d[i+1][j],d[i][j+1]);
  const out=[]; let i=0,j=0;
  while(i<n&&j<m){
    if(gold[i].name===pred[j].name){ out.push([gold[i],pred[j],i,j]); i++; j++; }
    else if(d[i+1][j]>=d[i][j+1]){ out.push([gold[i],null,i,-1]); i++; }
    else { out.push([null,pred[j],-1,j]); j++; }
  }
  while(i<n) out.push([gold[i],null,i++,-1]);
  while(j<m) out.push([null,pred[j],-1,j++]);
  return out;
}
function callHTML(c,idx,cls,badge,diffKeys){
  const args=Object.entries(c.arguments||c.parameters||{}).map(([k,v])=>{
    const t=esc(k)+'='+esc(typeof v==='string'?v:JSON.stringify(v));
    return diffKeys&&diffKeys.has(k)?`<em>${t}</em>`:t;
  }).join(', ');
  return `<div class="call ${cls||''}"><span class="n">${idx}</span>
    <span><span class="fn">${esc(c.name)}</span>(<span class="args">${args}</span>)</span>
    ${c.label?`<span class="lbl">→ ${esc(c.label)}</span>`:''}
    ${badge?`<span class="badge">${badge}</span>`:''}</div>`;
}
function chainHTML(calls){
  return '<div class="chain">'+calls.map((c,i)=>callHTML(c,i+1)).join('')+'</div>';
}
function diffChainHTML(gold,pred){
  const pairs=align(gold,pred); const out=[];
  for(const [g,p] of pairs){
    if(g&&p){
      const ga=g.arguments||{}, pa=p.arguments||{};
      const keys=new Set([...Object.keys(ga),...Object.keys(pa)]);
      const bad=new Set([...keys].filter(k=>JSON.stringify(ga[k])!==JSON.stringify(pa[k])));
      out.push(callHTML(p,'•',bad.size?'diffarg':'match',
        bad.size?`${bad.size} arg${bad.size>1?'s':''} differ`:'matches gold',bad));
    } else if(p){
      out.push(callHTML(p,'+','diffname','not in gold'));
    } else {
      out.push(callHTML(g,'−','miss','gold call missing'));
    }
  }
  return '<div class="chain">'+out.join('')+'</div>';
}

/* ---------- detail pane ---------- */
function renderDetail(){
  const i=SEL, s=S[i];
  if(!s){ $('#detail').innerHTML='<div class="empty">Select a sample on the left.</div>'; return; }
  const gnames=s.gold.map(c=>c.name);
  const usedByGold=new Set(gnames);
  const specs=s.ts.map(k=>JSON.parse(P.specs[k]));

  let h=`<div class="pad" style="max-width:none">
   <h2>Sample ${i+1} <span class="tag ${s.d}">${s.d}</span> <span class="tag">${s.nc} calls</span>
       <span class="tag">${s.nn} nested arg${s.nn===1?'':'s'}</span>
       <span class="tag">${specs.length} tools offered</span></h2>
   <p class="sub mono" style="font-size:11.3px">${esc(s.id)}
      <span class="linkish" onclick="copy('${s.id}','Sample id copied')">copy id</span></p>

   <div class="card"><h3>Query</h3><div class="in"><pre>${esc(s.q)}</pre></div></div>

   <div class="card"><h3>Gold solution
       <span class="spacer"></span>
       <span class="tag ok">answer ${esc(fmt(s.ga))}</span>
       <button class="iconbtn" onclick="copy(${JSON.stringify(JSON.stringify(s.gold,null,2)).replace(/"/g,'&quot;')},'Gold chain copied')">copy JSON</button>
     </h3><div class="in">${chainHTML(s.gold)}</div></div>`;

  /* run panels */
  const order=RUNS.slice().sort((a,b)=>(RMETA[a].tier==='matched'?0:1)-(RMETA[b].tier==='matched'?0:1));
  for(const k of order){
    if(!ACTIVE.has(k)) continue;
    const m=RMETA[k], r=row(k,i), pred=parseGen(r.g);
    const sideCls=m.side==='ours'?'ours':'base';
    const okAns=r.wn===1;
    const badges=[
      r.fm?'<span class="tag ok">full match</span>':'',
      r.wn?'<span class="tag ok">win</span>':'<span class="tag bad">no win</span>',
      `<span class="tag">partial ${pct(r.pt)}</span>`,
      r.ns?'<span class="tag ok">name seq ✓</span>':'',
    ].join('');
    const dcls={exact:'ok',alt_win:'alt',refusal:'warn',unparsable:'',args:'bad',order:'bad',
                partial_funcs:'bad',wrong_funcs:'bad',exec_error:'bad'}[r.c]||'';
    h+=`<div class="card"><h3>
        <span class="runhead"><span class="nm ${sideCls}">${esc(m.label)}</span>
        <span class="tag ${sideCls}">${m.side==='ours'?'our run':'baseline'}</span>
        ${m.tier==='legacy'?'<span class="tag">legacy</span>':''}
        <span class="tag ${dcls}">${esc(P.diag_label[r.c])}</span>${badges}</span>
        <span class="spacer"></span>
        <button class="iconbtn" onclick="showPrompt(${i},'${k}')">exact prompt</button>
      </h3><div class="in">
      <p class="why">${esc(P.why[r.c])}</p>
      <div class="ansrow">
        <span class="muted">executed answer</span>
        <span class="box ${okAns?'ok':'bad'}">${r.ee?'<span class="muted">could not execute</span>':esc(fmt(r.pa))}</span>
        <span class="muted">gold</span><span class="box">${esc(fmt(s.ga))}</span>
        ${r.ee?`<span class="tag bad" title="${esc(r.ee)}">exec error</span>`:''}
      </div>
      ${r.ee?`<div class="note" style="margin-bottom:11px"><b>Execution error</b> — ${esc(r.ee)}</div>`:''}
      ${pred&&pred.length?`<div class="muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Predicted chain, aligned against gold</div>${diffChainHTML(s.gold,pred)}`:''}
      ${r.gr?`<details open><summary><b>Full generation trace</b> (${r.gr.length.toLocaleString()} chars — includes the model's private reasoning, one unbroken generation, no real execution until after it finished)</summary>
        <div class="codebox tall"><pre>${esc(r.gr)}</pre></div></details>
      <details><summary>What actually got scored (${r.g.length.toLocaleString()} chars — &lt;think&gt; block stripped)</summary>
        <div class="codebox"><pre>${esc(r.g)}</pre></div></details>`
      :`<details><summary>Raw generation (${r.g.length.toLocaleString()} chars)</summary>
        <div class="codebox"><pre>${esc(r.g)}</pre></div></details>`}
      <details><summary>Run configuration</summary>
        <dl class="kv"><dt>model</dt><dd>${esc(m.model)} @ ${esc(m.rev)}</dd>
        <dt>ICL shots</dt><dd>${m.shots}</dd>
        <dt>prompt template</dt><dd>Hammer2.0-7b (IBM src/PROMPTS.json)</dd>
        <dt>infrastructure</dt><dd>${esc(m.infra)}</dd></dl></details>
      </div></div>`;
  }

  /* tool catalog */
  const predNames=new Set();
  for(const k of ACTIVE) (row(k,i).pn||[]).forEach(n=>n&&predNames.add(n));
  h+=`<div class="card"><h3>Tool catalog shown to the model
      <span class="spacer"></span><span class="muted">${specs.length} functions · ${toolsString(s).length.toLocaleString()} chars of the prompt</span></h3>
     <div class="in"><details><summary>Show all ${specs.length} tool specifications</summary>
     <table><thead><tr><th>#</th><th>function</th><th>description</th><th>params</th><th>used by</th></tr></thead><tbody>`;
  specs.forEach((t,ix)=>{
    const tags=[usedByGold.has(t.name)?'<span class="tag ok">gold</span>':'',
                predNames.has(t.name)?'<span class="tag">predicted</span>':''].join(' ');
    h+=`<tr${usedByGold.has(t.name)?' class="hl"':''}><td class="num muted">${ix+1}</td>
        <td class="mono">${esc(t.name)}</td><td>${esc(t.description||'')}</td>
        <td class="mono muted" style="font-size:11px">${esc(Object.keys(t.parameters||{}).join(', '))}</td>
        <td>${tags}</td></tr>`;
  });
  h+='</tbody></table></details></div></div></div>';
  $('#detail').innerHTML=h;
  $('#detail').scrollTop=0;
}

/* ---------- prompt modal ---------- */
let PROMPT_MODE='blocks', PROMPT_CTX=null;
function showPrompt(i,k){ PROMPT_CTX=[i,k]; renderPrompt(); $('#modal').classList.add('on'); }
function renderPrompt(){
  const [i,k]=PROMPT_CTX, s=S[i], m=RMETA[k];
  const full=buildPrompt(s,m.shots,m.model,m.tier==='checklist');
  $('#modaltitle').innerHTML=`Exact prompt · <b>${esc(m.label)}</b> · sample ${i+1}
     <span class="muted" style="font-weight:400"> ${full.length.toLocaleString()} chars</span>`;
  $('#modaltools').innerHTML=`<span class="seg">
      <button class="${PROMPT_MODE==='blocks'?'on':''}" onclick="PROMPT_MODE='blocks';renderPrompt()">annotated</button>
      <button class="${PROMPT_MODE==='raw'?'on':''}" onclick="PROMPT_MODE='raw';renderPrompt()">raw</button>
    </span>
    <button class="iconbtn" onclick="copyPrompt()">copy</button>`;
  if(PROMPT_MODE==='raw'){
    $('#modalbody').innerHTML=`<div class="codebox tall"><pre>${esc(full)}</pre></div>`;
    return;
  }
  const toolsQ=pyJsonStr(toolsString(s));
  const isXlam=m.model==='xLAM-7b-fc-r';
  const iclS=isXlam?P.prompts.icl_str_xlam[String(m.shots)]:P.prompts.icl_str[String(m.shots)];
  const tpl=P.prompts.templates[isXlam?'xLAM-7b-fc-r':'Hammer2.0-7b'];
  const FS='{FUNCTION_STR}', IS='{ICL_EXAMPLES}', QS='{QUERY}';
  const a=tpl.indexOf(FS), b=tpl.indexOf(IS), c=tpl.indexOf(QS);
  // xLAM's non-placeholder braces are pre-escaped ({{ }}) for Python's
  // .format(); un-escape each displayed segment so this shows what the model
  // actually received, not the raw PROMPTS.json source text.
  const seg=(x,y)=>{const raw=tpl.slice(x,y); return isXlam?unescapeFormatBraces(raw):raw;};
  const templateLabel=isXlam
    ? 'IBM PROMPTS.json → "xLAM-7b-fc-r" — xLAM\'s own template, not Hammer\'s'
    : 'IBM PROMPTS.json → "Hammer2.0-7b"';
  const note=isXlam
    ? `<div class="note" style="margin-top:14px"><b>xLAM's own template.</b> Unlike Qwen3, xLAM-7b-fc-r uses its
        dedicated <span class="mono">PROMPTS.json["xLAM-7b-fc-r"]</span> template — a real, separate template
        native to IBM's code, not a reuse of Hammer's. Its expected output is also different:
        <span class="mono">{"tool_calls": [...]}</span> wrapping the call list, rather than a bare list. Applied via
        Python's <span class="mono">.format()</span> (its JSON example braces are pre-escaped for this), which
        this view replicates by un-escaping <span class="mono">{{ }}</span> after substitution.</div>`
    : `<div class="note" style="margin-top:14px"><b>Same template for both models.</b> Qwen3-4B was run on Hammer2.0-7b's
        template, unchanged — the deliberate modelling choice recorded in REPORT.md, not Qwen3's native
        Hermes-style tool-calling format. The <span class="mono">&lt;|im_start|&gt;</span> markers work for both because
        Hammer2.0-7b is itself Qwen2.5-based.</div>`;
  $('#modalbody').innerHTML=
    `<div class="pblock"><div class="lb">Template — task instruction (${templateLabel})</div><pre>${esc(seg(0,a))}</pre></div>
     <div class="pblock tools"><div class="lb">{FUNCTION_STR} — this sample's ${s.ts.length} tool specs, JSON-encoded twice (a string inside the prompt)</div><pre>${esc(toolsQ)}</pre></div>
     <div class="pblock"><div class="lb">Template — format instruction</div><pre>${esc(seg(a+FS.length,b))}</pre></div>
     <div class="pblock icl"><div class="lb">{ICL_EXAMPLES} — ${m.shots} in-context example${m.shots>1?'s':''} from IBM src/icl_examples.json (fixed for every sample)${isXlam?', wrapped as {"tool_calls":[...]} for this template':''}</div><pre>${esc(iclS)}</pre></div>
     <div class="pblock"><div class="lb">Template — query framing</div><pre>${esc(seg(b+IS.length,c))}</pre></div>
     <div class="pblock query"><div class="lb">{QUERY} — this sample's question</div><pre>${esc(s.q)}</pre></div>
     <div class="pblock"><div class="lb">Template — assistant turn opener</div><pre>${esc(seg(c+QS.length))}</pre></div>
     ${note}`;
}
function copyPrompt(){ const [i,k]=PROMPT_CTX; copy(buildPrompt(S[i],RMETA[k].shots,RMETA[k].model,RMETA[k].tier==='checklist'),'Full prompt copied'); }
