
/* ================================ COMPARE ================================ */
let CMP_A='qwen3_3shot', CMP_B='hammer_3shot', CMP_M='wn';
const METRICS={wn:['Win Rate','executes the predicted chain and credits any path reaching the correct final answer'],
               fm:['Full Sequence Match','exact function names and exact arguments, in gold order'],
               ns:['Function-name sequence','the sequence of function names matches gold exactly, arguments ignored']};
function contingency(a,b,m,filter){
  let both=0,neither=0,aOnly=0,bOnly=0;
  const ids={aOnly:[],bOnly:[],both:[],neither:[]};
  for(let i=0;i<S.length;i++){
    if(filter&&!filter(S[i])) continue;
    const x=R(a).rows[i][m], y=R(b).rows[i][m];
    if(x&&y){both++;ids.both.push(i)} else if(x){aOnly++;ids.aOnly.push(i)}
    else if(y){bOnly++;ids.bOnly.push(i)} else {neither++;ids.neither.push(i)}
  }
  return {both,neither,aOnly,bOnly,ids,n:both+neither+aOnly+bOnly};
}
function renderCompare(){
  const A=RMETA[CMP_A], B=RMETA[CMP_B];
  const sel=(id,val)=>`<select id="${id}">`+RUNS.map(k=>`<option value="${k}"${k===val?' selected':''}>${esc(RMETA[k].label)}</option>`).join('')+'</select>';
  const c=contingency(CMP_A,CMP_B,CMP_M);
  const p=binomTwoSided(c.aOnly,c.bOnly);
  const winner=c.aOnly>c.bOnly?A:B;
  const sig=p<0.05;
  let h=`<h2>Paired comparison</h2>
   <p class="sub">Every sample is answered by both runs, so the honest test is a paired one. The 2×2 table below counts
     agreement and disagreement; McNemar's exact test (two-sided binomial on the discordant pairs only) says whether
     the imbalance between the two disagreement cells is more than chance.</p>
   <div class="frow" style="margin-bottom:16px;gap:10px">
     <label>Run A</label>${sel('cmpa',CMP_A)}
     <label>Run B</label>${sel('cmpb',CMP_B)}
     <label>Metric</label><select id="cmpm">${Object.entries(METRICS).map(([k,v])=>`<option value="${k}"${k===CMP_M?' selected':''}>${v[0]}</option>`).join('')}</select>
   </div>
   <div class="note" style="background:none;border-color:var(--bd)"><b style="color:var(--tx2)">${esc(METRICS[CMP_M][0])}</b> — ${esc(METRICS[CMP_M][1])}.</div>
   <div class="grid2">
    <div class="card"><h3>Contingency, n = ${c.n.toLocaleString()}</h3><div class="in">
      <table class="hm"><thead><tr><th></th><th>B right</th><th>B wrong</th><th>row total</th></tr></thead><tbody>
      <tr><th class="rh">A right</th>
          <td>${c.both}</td>
          <td style="background:color-mix(in srgb,var(--ok) 16%,transparent)"><span class="linkish" data-jump="aOnly">${c.aOnly}</span></td>
          <td class="muted">${c.both+c.aOnly}</td></tr>
      <tr><th class="rh">A wrong</th>
          <td style="background:color-mix(in srgb,var(--bad) 16%,transparent)"><span class="linkish" data-jump="bOnly">${c.bOnly}</span></td>
          <td>${c.neither}</td><td class="muted">${c.bOnly+c.neither}</td></tr>
      <tr><th class="rh muted">col total</th><td class="muted">${c.both+c.bOnly}</td><td class="muted">${c.aOnly+c.neither}</td><td class="muted">${c.n}</td></tr>
      </tbody></table>
      <div class="legend"><span>A = <b style="color:var(--${A.side==='ours'?'ours':'base'})">${esc(A.label)}</b></span>
        <span>B = <b style="color:var(--${B.side==='ours'?'ours':'base'})">${esc(B.label)}</b></span></div>
      <p class="muted" style="font-size:11.8px;margin:11px 0 0">Click a disagreement count to open those samples in the Explorer.</p>
    </div></div>
    <div class="card"><h3>McNemar's exact test</h3><div class="in">
      <dl class="kv">
        <dt>discordant pairs</dt><dd>${c.aOnly+c.bOnly}</dd>
        <dt>A-only-right</dt><dd>${c.aOnly}</dd>
        <dt>B-only-right</dt><dd>${c.bOnly}</dd>
        <dt>p-value</dt><dd style="color:var(--${sig?'ok':'warn'})">${pval(p)}</dd>
        <dt>A score</dt><dd>${pct(R(CMP_A).agg[CMP_M==='wn'?'win':CMP_M==='fm'?'full':'nameseq'])}</dd>
        <dt>B score</dt><dd>${pct(R(CMP_B).agg[CMP_M==='wn'?'win':CMP_M==='fm'?'full':'nameseq'])}</dd>
      </dl>
      <div class="note" style="margin:13px 0 0;${sig?'':'background:color-mix(in srgb,var(--tx3) 9%,transparent);border-color:var(--bd)'}">
        ${c.aOnly===c.bOnly?'<b>Perfectly balanced</b> — no evidence of any difference.':
          sig?`<b>Significant at p &lt; 0.05.</b> ${esc(winner.label)} is ahead on ${esc(METRICS[CMP_M][0])}; the imbalance between ${c.aOnly} and ${c.bOnly} is larger than chance would produce.`
             :`<b>Not significant.</b> ${c.aOnly} vs ${c.bOnly} discordant pairs is consistent with a genuine tie on ${esc(METRICS[CMP_M][0])}.`}
      </div>
    </div></div>
   </div>`;

  /* domain-stratified */
  h+=`<div class="card"><h3>Stratified by domain</h3><div class="in"><table>
    <thead><tr><th>Domain</th><th class="num">n</th><th class="num">A right</th><th class="num">B right</th>
      <th class="num">A only</th><th class="num">B only</th><th class="num">p</th></tr></thead><tbody>`;
  for(const d of ['math','code']){
    const cc=contingency(CMP_A,CMP_B,CMP_M,s=>s.d===d);
    const pp=binomTwoSided(cc.aOnly,cc.bOnly);
    h+=`<tr><td><span class="tag ${d}">${d}</span></td><td class="num">${cc.n}</td>
      <td class="num">${pct((cc.both+cc.aOnly)/cc.n)}</td><td class="num">${pct((cc.both+cc.bOnly)/cc.n)}</td>
      <td class="num">${cc.aOnly}</td><td class="num">${cc.bOnly}</td>
      <td class="num" style="color:var(--${pp<0.05?'ok':'tx3'})">${pval(pp)}</td></tr>`;
  }
  h+='</tbody></table></div></div>';

  /* diagnosis cross-tab */
  const cats=P.diag_order;
  const tab={}; cats.forEach(x=>{tab[x]={}; cats.forEach(y=>tab[x][y]=0)});
  for(let i=0;i<S.length;i++) tab[R(CMP_A).rows[i].c][R(CMP_B).rows[i].c]++;
  let max=0; cats.forEach(x=>cats.forEach(y=>{ if(x!==y) max=Math.max(max,tab[x][y]) }));
  h+=`<div class="card"><h3>Where the two runs land, side by side</h3><div class="in">
    <p class="muted" style="margin:0 0 11px;font-size:12.2px">Rows = A's outcome, columns = B's outcome. The diagonal is agreement;
      everything off it is a behavioural difference. Click any cell to inspect those samples.</p>
    <table class="hm"><thead><tr><th></th>${cats.map(y=>`<th title="${esc(P.diag_label[y])}">${esc(P.diag_label[y]).replace(/ /g,'<br>')}</th>`).join('')}<th>total</th></tr></thead><tbody>`;
  for(const x of cats){
    const rt=cats.reduce((a,y)=>a+tab[x][y],0);
    h+=`<tr><th class="rh" title="${esc(P.diag_label[x])}">${esc(P.diag_label[x])}</th>`;
    for(const y of cats){
      const v=tab[x][y];
      const bgv=x===y?`color-mix(in srgb,var(--tx3) ${Math.min(22,v/8)}%,transparent)`
                     :`color-mix(in srgb,var(--acc) ${max?Math.min(34,(v/max)*34):0}%,transparent)`;
      h+=`<td style="background:${bgv}">${v?`<span class="linkish" data-cell="${x}|${y}">${v}</span>`:'<span class="muted">·</span>'}</td>`;
    }
    h+=`<td class="muted">${rt}</td></tr>`;
  }
  h+='</tbody></table></div></div>';
  $('#comparebody').innerHTML=h;

  $('#cmpa').onchange=e=>{CMP_A=e.target.value;renderCompare()};
  $('#cmpb').onchange=e=>{CMP_B=e.target.value;renderCompare()};
  $('#cmpm').onchange=e=>{CMP_M=e.target.value;renderCompare()};
  $$('#comparebody [data-jump]').forEach(el=>el.onclick=()=>{
    FOCUS=CMP_A; VS=CMP_B;
    $('#ffocus').value=CMP_A; $('#fvs').value=CMP_B; $('#fvsmetric').value=CMP_M;
    $('#fvsmode').value=el.dataset.jump==='aOnly'?'focus_only':'vs_only';
    $('#fdiag').value=''; $('#fvsdiag').value=''; $('#q').value=''; $('#fdom').value=''; $('#fcalls').value='';
    go('explorer'); applyFilters(); if(FILTERED.length) select(FILTERED[0]);
  });
  $$('#comparebody [data-cell]').forEach(el=>el.onclick=()=>{
    const [x,y]=el.dataset.cell.split('|');
    FOCUS=CMP_A; VS=CMP_B;
    $('#ffocus').value=CMP_A; $('#fvs').value=CMP_B;
    $('#fdiag').value=x; $('#fvsdiag').value=y; $('#fvsmode').value='';
    $('#q').value=''; $('#fdom').value=''; $('#fcalls').value='';
    go('explorer'); applyFilters();
    if(FILTERED.length) select(FILTERED[0]);
  });
}

/* ================================ OVERVIEW ================================ */
function renderOverview(){
  const key={f1_func:'F1 Func',f1_param:'F1 Param',partial:'Partial Acc',full:'Full Acc',win:'Win Rate',
             refusal:'Refusal',parse_err:'Parse fail'};
  const matched=RUNS.filter(k=>RMETA[k].tier==='matched');
  const best={};
  for(const m of ['partial','full','win'])
    best[m]=Math.max(...matched.map(k=>R(k).agg[m]));
  let h=`<h2>All runs at a glance</h2>
   <p class="sub">Recomputed from the raw generations with IBM's own <span class="mono">scorer.py</span> and
     <span class="mono">output_parsers.py</span>, executing every predicted call chain against NESTFUL's
     <span class="mono">executable_functions</span>. Every figure below reproduces REPORT.md exactly.</p>
   <div class="card"><h3>Metrics</h3><div class="in"><table><thead><tr><th>Run</th><th>Tier</th>
     ${Object.entries(key).map(([k2,v])=>`<th class="num"${k2.startsWith('f1')?' style="color:var(--tx3)" title="Structurally unstable on this dataset — see the note below"':''}>${v}</th>`).join('')}</tr></thead><tbody>`;
  for(const k of RUNS){
    const a=R(k).agg, m=RMETA[k];
    h+=`<tr><td><span class="runname" style="color:var(--${m.side==='ours'?'ours':'base'})">${esc(m.label)}</span></td>
      <td><span class="tag">${m.tier}</span></td>`;
    for(const mk of Object.keys(key)){
      const v=a[mk];
      const isBest=m.tier==='matched'&&['partial','full','win'].includes(mk)&&v===best[mk];
      h+=`<td class="num${isBest?' best':''}">${mk.startsWith('f1')?v.toFixed(3):pct(v)}</td>`;
    }
    h+='</tr>';
  }
  h+=`</tbody></table></div></div>
   <div class="note"><b>F1 Func / F1 Param are internally comparable only.</b> NESTFUL's F1 is a global multi-label
     macro-F1 over 904 function names, 91% of which appear in exactly one example — mechanically unstable, and the
     public scorer post-dates the paper by seven months. Win Rate is the metric to trust.</div>`;

  /* checklist experiment — does an explicit output checklist fix the errors
     the user flagged (missing labels, wrong-argument-shaped failures, refusals)? */
  if(P.checklist_experiment && P.checklist_experiment.length){
    const sig=p=>p<0.001?'p&lt;0.001':`p=${p.toFixed(p<0.01?4:3)}`;
    const cell=(base,ck,delta,p,goodDir)=>{
      const good=goodDir==='up'?delta>0:delta<0;
      const flat=Math.abs(delta)<1e-9;
      const sigOk=p!==undefined&&p<0.05;
      return `<td class="num">${pct(base)} &rarr; ${pct(ck)}
        <div style="font-size:11px;font-weight:700;color:var(--${flat?'tx3':good?'ok':'bad'})">${delta>=0?'+':''}${(delta*100).toFixed(2)}pp${p!==undefined?` <span style="font-weight:400;color:var(--tx3)">(${sig(p)}${sigOk?'':', n.s.'})</span>`:''}</div></td>`;
    };
    h+=`<div class="card"><h3>Does an explicit output checklist fix the errors we found?</h3><div class="in">
      <p class="sub">Reviewed raw generations first, confirmed two real failure modes — function calls missing their
        own <span class="mono">"label"</span> field, and refusals (<span class="mono">[]</span>) on samples the
        provided tools can always solve — then added a 7-item verification checklist before
        <span class="mono">[BEGIN OF QUERY]</span> and reran, same infra/revision/shot-count as the baseline, so this
        is a clean paired before/after on the same 1,861 samples. xLAM's <span class="mono">max_tokens</span> was also
        raised 1000&rarr;2000 in the same run (its baseline showed truncation-driven parse failures).
        p-values are paired McNemar exact tests on discordant outcomes.</p>
      <table><thead><tr><th>Model (3-shot)</th><th class="num">Partial Acc</th><th class="num">Full Acc</th>
        <th class="num">Win Rate</th><th class="num">Refusal</th><th class="num">Parse fail</th>
        <th class="num">Missing-label calls</th></tr></thead><tbody>`;
    for(const c of P.checklist_experiment){
      h+=`<tr><td><span class="runname">${esc(c.model)}</span></td>
        ${cell(c.partial.base,c.partial.checklist,c.partial.delta,undefined,'up')}
        ${cell(c.metrics.full.base,c.metrics.full.checklist,c.metrics.full.delta,c.metrics.full.p,'up')}
        ${cell(c.metrics.win.base,c.metrics.win.checklist,c.metrics.win.delta,c.metrics.win.p,'up')}
        ${cell(c.metrics.refusal.base,c.metrics.refusal.checklist,c.metrics.refusal.delta,c.metrics.refusal.p,'down')}
        ${cell(c.parse_err.base,c.parse_err.checklist,c.parse_err.delta,undefined,'down')}
        <td class="num">${pct(c.missing_label.base)} &rarr; ${pct(c.missing_label.checklist)}</td></tr>`;
    }
    h+=`</tbody></table>
      <div class="note" style="margin-top:14px"><b>Reading this:</b> the checklist is not a uniform win. It
        significantly <em>helps</em> Win Rate for three of four models — Hammer +5.4pp, xLAM +3.1pp, Thinking
        +2.6pp (all p&lt;0.001) — and refusals collapse everywhere (Hammer 16.0%&rarr;2.4%, Thinking
        6.3%&rarr;1.5%, both p&lt;0.001). But it significantly <em>hurts</em> Qwen3-Instruct's Win Rate
        (&minus;1.6pp, p=0.042) and Full Acc (&minus;2.5pp, p&lt;0.001) despite also cutting its refusals
        (10.6%&rarr;3.7%, p&lt;0.001) — traced to real generations, not a scoring artifact: of 636 samples
        Qwen3-Instruct got right at baseline, 110 flip to wrong under the checklist (mostly new wrong answers or
        execution errors, not parse failures), against only 81 previously-wrong samples it newly gets right.
        Qwen3-Instruct also never had much of a missing-label problem to begin with (0.1% at baseline, vs. Hammer's
        8.4% and xLAM's 38.4%) — the checklist's core fix targets a failure mode this model barely has, while its
        "never refuse" item still pushes it into attempting hard cases it would otherwise have correctly avoided.
        Hammer's Full Acc also dips slightly (&minus;1.0pp, p=0.045) even as its Win Rate rises — the checklist makes
        answers more likely to reach the <em>correct value</em> by an alternate valid path, not more likely to
        reproduce gold's exact call sequence. xLAM's missing-label rate falls but stays high (38.4%&rarr;29.8%) — a
        real, only-partial fix, reported as such rather than rounded up to "solved." Net: worth keeping for Hammer,
        xLAM and Thinking; not recommended as-is for Qwen3-Instruct.</div></div></div>`;
  }

  /* vs. paper — direct comparison for the models we actually reproduced */
  const PAPER=P.paper.models, PKEY=Object.fromEntries(PAPER.map(m=>[m.key,m]));
  const MLBL={f1_func:'F1 Func',f1_param:'F1 Param',partial:'Partial Acc',full:'Full Acc',win:'Win Rate'};
  const overlap=RUNS.filter(k=>PKEY[RMETA[k].model]);
  if(overlap.length){
    h+=`<div class="card"><h3>Ours vs. the paper's published Table 1</h3><div class="in">
      <p class="sub">${esc(P.paper.source)}. Only the two models below were actually run through the paper's own
        evaluation — this is the real, apples-to-apples check. F1 columns are shown for completeness but are known
        unreliable (see note above) even here; the meaningful columns are Partial/Full/Win.</p>
      <table><thead><tr><th>Run</th>
        ${P.paper.metric_order.map(mk=>`<th class="num" colspan="3"${mk.startsWith('f1')?' style="color:var(--tx3)"':''}>${MLBL[mk]}</th>`).join('')}
      </tr><tr><th></th>
        ${P.paper.metric_order.map(()=>'<th class="num">paper</th><th class="num">ours</th><th class="num">&Delta;</th>').join('')}
      </tr></thead><tbody>`;
    for(const k of overlap){
      const m=RMETA[k], pm=PKEY[m.model], pvals=m.shots===1?pm.one:pm.three, a=R(k).agg;
      h+=`<tr><td><span class="runname" style="color:var(--${m.side==='ours'?'ours':'base'})">${esc(m.label)}</span></td>`;
      P.paper.metric_order.forEach((mk,idx)=>{
        const pv=pvals[idx], ov=a[mk], d=ov-pv;
        const isF1=mk.startsWith('f1');
        const big=isF1?Math.abs(d)>0.15:Math.abs(d)>0.08;
        h+=`<td class="num"${isF1?' style="color:var(--tx3)"':''}>${pv.toFixed(3)}</td>
            <td class="num"${isF1?' style="color:var(--tx3)"':''}>${ov.toFixed(3)}</td>
            <td class="num" style="${big?'color:var(--bad);font-weight:700':(isF1?'color:var(--tx3)':'')}">${d>=0?'+':''}${d.toFixed(3)}</td>`;
      });
      h+='</tr>';
    }
    h+=`</tbody></table>
      <div class="note" style="margin-top:14px"><b>Reading the deltas:</b> 3-shot Partial Accuracy lands almost exactly
        on the paper (xLAM: +0.000, Hammer: &minus;0.02) — the strongest evidence this pipeline is faithful. 1-shot
        Full Acc and Win Rate run meaningfully <em>below</em> the paper for both models (&minus;0.10 to &minus;0.18) —
        a real, open gap, not explained away here.</div></div></div>`;
  }

  /* full paper leaderboard, our runs inserted by their own measured Win Rate */
  const lbRows=[
    ...PAPER.map(m=>({label:m.label,params:m.params,win:m.three[4],src:'paper'})),
    ...RUNS.filter(k=>RMETA[k].tier==='matched'&&RMETA[k].shots===3).map(k=>({
      label:RMETA[k].short,params:null,win:R(k).agg.win,
      src:PKEY[RMETA[k].model]?'ours-repro':'ours-new'})),
  ].sort((a,b)=>b.win-a.win);
  h+=`<div class="card"><h3>Full paper leaderboard, in context — 3-shot Win Rate</h3><div class="in">
    <p class="sub">All 15 models from the paper's Table 1, plus every one of our own 3-shot runs, ranked together
      by the metric this report trusts most. The two rows tagged <span class="tag" style="background:var(--ours)">not
      in paper</span> are Qwen3 — the paper never tested them, so "ranks #1" is a real number but not literally a
      "beats the paper" claim in the way the "our repro" rows are.</p>
    <table><thead><tr><th>#</th><th>Model</th><th class="num">Params</th><th class="num">Win Rate</th><th>Source</th></tr></thead><tbody>`;
  lbRows.forEach((r,i)=>{
    const tag=r.src==='paper'?'<span class="tag">paper</span>'
      :r.src==='ours-repro'?'<span class="tag" style="background:var(--base)">our repro</span>'
      :'<span class="tag" style="background:var(--ours)">not in paper</span>';
    h+=`<tr${r.src!=='paper'?' style="background:color-mix(in srgb, var(--acc) 7%, transparent)"':''}>
      <td class="num">${i+1}</td><td>${esc(r.label)}</td>
      <td class="num">${r.params?r.params+'B':'—'}</td>
      <td class="num" style="font-weight:700">${pct(r.win)}</td><td>${tag}</td></tr>`;
  });
  h+=`</tbody></table></div></div>`;

  /* diagnosis distribution */
  const cats=P.diag_order;
  const shortLab={exact:'Exact',alt_win:'Alt win',args:'Args',order:'Order',partial_funcs:'Partial fn',
                  wrong_funcs:'Wrong fn',exec_error:'Exec fail',refusal:'Refusal',unparsable:'Unparsable'};
  const col={exact:'var(--ok)',alt_win:'var(--alt)',args:'var(--bad)',order:'#d2554f',
             partial_funcs:'#b8433f',wrong_funcs:'#94322f',exec_error:'#7a2a28',
             refusal:'var(--warn)',unparsable:'var(--tx3)'};
  h+=`<div class="card"><h3>What each run actually did, across all 1,861 samples</h3><div class="in"><table>
     <thead><tr><th>Run</th><th style="width:46%">Outcome mix</th>
       ${cats.map(c=>`<th class="num" title="${esc(P.why[c])}">${esc(shortLab[c])}</th>`).join('')}</tr></thead><tbody>`;
  for(const k of RUNS){
    const d=R(k).agg.diag, n=R(k).agg.n;
    h+=`<tr><td class="runname" style="color:var(--${RMETA[k].side==='ours'?'ours':'base'})">${esc(RMETA[k].short)}</td>
      <td><div class="bar">${cats.map(c=>d[c]?`<span style="width:${(d[c]/n*100)}%;background:${col[c]}" title="${esc(P.diag_label[c])}: ${d[c]}"></span>`:'').join('')}</div></td>
      ${cats.map(c=>`<td class="num${c==='exact'||c==='alt_win'?' best':''}">${d[c]||0}</td>`).join('')}</tr>`;
  }
  h+=`</tbody></table><div class="legend">${cats.map(c=>`<span><i style="background:${col[c]}"></i>${esc(P.diag_label[c])}</span>`).join('')}</div></div></div>`;

  /* domain */
  h+=`<div class="card"><h3>Domain split — the aggregate hides two different benchmarks</h3><div class="in">
   <table><thead><tr><th>Run</th><th>Domain</th><th class="num">n</th><th class="num">Name-seq match</th>
     <th class="num">Full Acc</th><th class="num">Win Rate</th><th class="num">Refusal</th></tr></thead><tbody>`;
  for(const k of matched) for(const d of ['math','code']){
    const b=R(k).agg.by_domain[d];
    h+=`<tr><td>${d==='math'?`<span class="runname" style="color:var(--${RMETA[k].side==='ours'?'ours':'base'})">${esc(RMETA[k].short)}</span>`:''}</td>
      <td><span class="tag ${d}">${d}</span></td><td class="num">${b.n}</td><td class="num">${pct(b.nameseq)}</td>
      <td class="num">${pct(b.full)}</td><td class="num">${pct(b.win)}</td><td class="num">${pct(b.refusal)}</td></tr>`;
  }
  h+=`</tbody></table>
   <div class="note" style="margin:14px 0 0"><b>Domain labels differ slightly from REPORT.md.</b> This viewer calls a
     sample <em>math</em> when every gold function is defined in NESTFUL's
     <span class="mono">basic_functions.py</span> — giving 1,416 math / 445 code. REPORT.md used a hand-written list of
     33 function names that omitted 16 real basic functions (<span class="mono">reminder</span>,
     <span class="mono">speed</span>, <span class="mono">cube_edge_by_volume</span> and others), so it counted 26 MathQA
     samples as code and reported 1,390 / 471. The per-domain percentages shift by well under a point; the finding is
     unchanged.</div></div></div>`;

  /* determinism */
  h+=`<div class="card"><h3>Determinism spot-check</h3><div class="in"><table>
    <thead><tr><th>Run</th><th class="num">Prompts byte-identical across two independent generate() calls</th></tr></thead><tbody>`;
  for(const k of RUNS){
    const d=P.determinism[k];
    if(!d) continue;
    const ok=d.filter(x=>x.identical_across_two_fresh_calls).length;
    h+=`<tr><td>${esc(RMETA[k].label)}</td><td class="num ${ok===d.length?'best':''}"
        style="${ok===d.length?'':'color:var(--warn)'}">${ok}/${d.length}</td></tr>`;
  }
  h+=`</tbody></table><p class="muted" style="font-size:12px;margin:11px 0 0">Qwen3 1-shot shows one divergence at
    temperature 0.0 — genuine floating-point non-determinism in vLLM 0.8.5's V1 engine, not a configuration error.</p></div></div>`;
  $('#overviewbody').innerHTML=h;
}
