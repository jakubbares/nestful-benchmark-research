
/* ================================ PROMPTS ================================ */
let TPL_SHOW='Hammer2.0-7b';
function renderPrompts(){
  const tpl=P.prompts.templates, names=Object.keys(tpl);
  const hammer=tpl['Hammer2.0-7b'];
  const a=hammer.indexOf('{FUNCTION_STR}'), b=hammer.indexOf('{ICL_EXAMPLES}'), c=hammer.indexOf('{QUERY}');
  let h=`<h2>The prompt, exactly</h2>
   <p class="sub">Both models were given the same prompt, built by the same code path IBM ships in
     <span class="mono">src/instruct_data_prep.py</span>: take the <span class="mono">"Hammer2.0-7b"</span> entry from
     <span class="mono">src/PROMPTS.json</span> and substitute three placeholders. Nothing else was changed —
     which is what makes the comparison paired, and also what makes one modelling choice worth stating plainly.</p>

   <div class="note"><b>We used their prompt, not ours.</b> There is no separate "our prompt" and "their prompt" here.
     Qwen3-4B was evaluated on Hammer2.0-7b's own template, verbatim, including its
     <span class="mono">&lt;|im_start|&gt;</span> chat markers — which happen to be valid for Qwen3 because Hammer2.0-7b
     is itself built on Qwen2.5. Qwen3's native Hermes-style tool-calling format was <em>not</em> used. That is a
     deliberate choice in favour of a controlled comparison, and it is also the single biggest open caveat: Qwen3 is
     being scored in a costume tailored for another model.</div>

   <div class="card"><h3>Substitution recipe</h3><div class="in">
     <table><thead><tr><th>Placeholder</th><th>Filled with</th><th style="width:130px">Varies per sample</th></tr></thead><tbody>
     <tr><td class="mono">{FUNCTION_STR}</td><td>The sample's tool catalog, <b>double-encoded</b>: the list of specs is
        serialised to JSON, then that string is serialised again, so the prompt contains a quoted string full of
        <span class="mono">\\"</span> escapes.</td><td>yes</td></tr>
     <tr><td class="mono">{ICL_EXAMPLES}</td><td>The first 1 or 3 entries of
        <span class="mono">src/icl_examples.json</span>, rendered as <span class="mono">#Example-n / Input: / Output:</span>.</td>
        <td>no — fixed for the whole run</td></tr>
     <tr><td class="mono">{QUERY}</td><td>The sample's natural-language question, raw.</td><td>yes</td></tr>
     </tbody></table>
     <p class="muted" style="font-size:12px;margin:12px 0 0">This viewer rebuilds prompts with the same recipe and has been
       verified byte-for-byte identical against all 7,444 stored prompts (1,861 samples × 4 matched runs). Open any sample
       and press <b>exact prompt</b> to see the real thing.</p>
   </div></div>

   <div class="card"><h3>The template, with placeholders in place</h3><div class="in">
     <div class="pblock"><pre>${esc(hammer.slice(0,a))}</pre></div>
     <div class="pblock tools"><div class="lb">{FUNCTION_STR}</div><pre class="muted">↳ this sample's tool catalog, JSON-in-JSON</pre></div>
     <div class="pblock"><pre>${esc(hammer.slice(a+14,b))}</pre></div>
     <div class="pblock icl"><div class="lb">{ICL_EXAMPLES}</div><pre class="muted">↳ the in-context examples below</pre></div>
     <div class="pblock"><pre>${esc(hammer.slice(b+15,c))}</pre></div>
     <div class="pblock query"><div class="lb">{QUERY}</div><pre class="muted">↳ this sample's question</pre></div>
     <div class="pblock"><pre>${esc(hammer.slice(c+7))}</pre></div>
   </div></div>

   <div class="note"><b>Instruction #2 is load-bearing.</b> "If none of the function can be used, point it out and refuse
     to answer" is what licenses the empty-list <span class="mono">[]</span> response. Both models take that branch far
     more often on math questions than on code ones — 99% of all refusals across both models and both shot counts land in
     the math domain. It is the dominant mechanism behind the 1-shot collapse.</div>

   <div class="card"><h3>In-context examples: 1-shot vs 3-shot</h3><div class="in">
     <div class="grid2">
       <div><div class="lb muted" style="font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px">1-shot — example 1 only</div>
         <div class="codebox"><pre>${esc(P.prompts.icl_str['1'])}</pre></div></div>
       <div><div class="lb muted" style="font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px">3-shot — examples 1–3</div>
         <div class="codebox"><pre>${esc(P.prompts.icl_str['3'])}</pre></div></div>
     </div>
     <p class="muted" style="font-size:12px;margin:12px 0 0">The only difference between a run's 1-shot and 3-shot prompt
       is this block. Example 3 is the only <em>code-domain</em> demonstration — dropping it is what removes every
       non-arithmetic pattern from the context, and both models lose roughly two thirds of their Full Accuracy when it goes.</p>
   </div></div>

   <div class="card"><h3>Every template IBM ships</h3><div class="in">
     <p class="muted" style="margin:0 0 11px;font-size:12.2px">The templates the NESTFUL authors used for each model in the
       paper's Table 1. Useful for judging how much of a model's score is prompt-shaped.</p>
     <div class="frow" style="margin-bottom:11px"><label>Template</label>
       <select id="tplsel">${names.map(n=>`<option value="${esc(n)}"${n===TPL_SHOW?' selected':''}>${esc(n)}${n==='Hammer2.0-7b'?' — used for every run here':''}</option>`).join('')}</select></div>
     <div class="codebox tall"><pre>${esc(tpl[TPL_SHOW])}</pre></div>
   </div></div>`;
  $('#promptsbody').innerHTML=h;
  $('#tplsel').onchange=e=>{TPL_SHOW=e.target.value;renderPrompts()};
}

/* ================================= METHOD ================================= */
function renderAbout(){
  const cats=P.diag_order;
  $('#aboutbody').innerHTML=`<h2>How to read this, and how it was built</h2>
   <p class="sub">Everything here is recomputed from the raw generation files, not copied from a report. The scoring code
     is IBM's own — <span class="mono">src/scorer.py</span>, <span class="mono">src/output_parsers.py</span> and
     <span class="mono">src/utils.py</span> from github.com/IBM/NESTFUL — driven per sample instead of per run, so every
     aggregate can be opened up and inspected one example at a time.</p>

   <div class="card"><h3>Metrics</h3><div class="in"><table><tbody>
     <tr><td style="width:150px"><b>Win Rate</b></td><td>Execute the predicted call chain against NESTFUL's real
       <span class="mono">executable_functions</span> and compare the final value to the gold answer. Any path that
       reaches the right number counts. The most semantically meaningful metric available, and the one this analysis trusts.</td></tr>
     <tr><td><b>Full Acc</b></td><td>Full Sequence Match — every function name <em>and</em> every argument identical to
       gold, in order. Strictest and most syntax-sensitive; penalises mathematically equivalent orderings.</td></tr>
     <tr><td><b>Partial Acc</b></td><td>Per-position agreement between the aligned gold and predicted call sequences, averaged.</td></tr>
     <tr><td><b>F1 Func / Param</b></td><td>Global multi-label macro-F1 over function names and over argument strings.
       Structurally unstable on this dataset — 904 function names, 91% appearing in exactly one example. Reported for
       completeness, not for ranking.</td></tr>
     <tr><td><b>Refusal</b></td><td>The model emitted <span class="mono">[]</span>. Tracked separately from "acted
       incorrectly", because declining to act is a different failure than acting wrongly.</td></tr>
   </tbody></table></div></div>

   <div class="card"><h3>Outcome categories</h3><div class="in"><table><tbody>
     ${cats.map(c=>`<tr><td style="width:180px"><b>${esc(P.diag_label[c])}</b></td><td>${esc(P.why[c])}</td></tr>`).join('')}
   </tbody></table><p class="muted" style="font-size:12px;margin:12px 0 0">Categories are assigned in that order, so each
     sample lands in exactly one. <b>Alternate trajectory win</b> is the interesting one: it is precisely the population
     that Win Rate credits and Full Sequence Match throws away.</p></div></div>

   <div class="card"><h3>Verification performed while building this</h3><div class="in"><table>
     <thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>
     <tr><td>All 7 runs rescored per sample with IBM's scorer</td><td class="best">F1 Func, F1 Param, Partial Acc, Full Acc
       and Win Rate reproduce REPORT.md's table exactly for all four matched runs</td></tr>
     <tr><td>Prompt reconstruction in this page vs the stored prompts</td><td class="best">7,444 / 7,444 byte-identical</td></tr>
     <tr><td>Deduplicated tool-spec table vs original tool strings</td><td class="best">1,861 / 1,861 byte-identical</td></tr>
     <tr><td>Module-caching shortcut in the executor</td><td style="color:var(--warn)">Rejected — caching executed modules
       changes 13 Win Rate outcomes, because NESTFUL's generated function files carry module-level state. This page reloads
       each module per call, exactly as IBM's scorer does.</td></tr>
     <tr><td>Domain classification</td><td style="color:var(--warn)">Corrected — see the note on the Overview tab.
       1,416 math / 445 code, against REPORT.md's 1,390 / 471.</td></tr>
   </tbody></table></div></div>

   <div class="card"><h3>Caveats carried over from REPORT.md</h3><div class="in"><table><tbody>
     <tr><td style="width:200px"><b>Template attribution</b></td><td>Qwen3-4B ran on Hammer2.0-7b's prompt template, not its
       native format. A modelling choice, not a bug — and the most valuable follow-up experiment.</td></tr>
     <tr><td><b>Possible contamination</b></td><td>The Hammer/xLAM-style prompt wording is reused across public tool-calling
       training sets. Cannot be ruled out from outside the training data.</td></tr>
     <tr><td><b>Single greedy run</b></td><td>One run per condition. The determinism spot-check covers 5 prompts per run,
       19/20 byte-identical; there is no multi-seed variance estimate.</td></tr>
     <tr><td><b>vLLM versions differ</b></td><td>0.6.3.post1 for Hammer, 0.8.5 for Qwen3 — unavoidable, Qwen3's architecture
       postdates 0.6.3. Everything else about the two runs is matched.</td></tr>
     <tr><td><b>F1 is not the paper's F1</b></td><td>The public scorer landed seven months after the paper, alongside a
       1,861-example dataset replacing an 85-example one. These F1 numbers are not comparable to the printed Table 1.</td></tr>
   </tbody></table></div></div>

   <div class="card"><h3>Provenance</h3><div class="in"><dl class="kv">
     <dt>dataset</dt><dd>IBM/NESTFUL data_v2/nestful_data.jsonl — 1,861 samples</dd>
     <dt>scorer</dt><dd>IBM/NESTFUL src/scorer.py + output_parsers.py (parse_Hammer2_0_7b), unmodified</dd>
     <dt>executor</dt><dd>IBM/NESTFUL data_v2/executable_functions — 4,350 files</dd>
     <dt>runs</dt><dd>matched_results/{hammer,qwen3}_{1,3}shot + results/{nestful_1,nestful_3,validation_hammer2.0-7b}</dd>
     <dt>Qwen3-4B-Instruct-2507</dt><dd>HF revision cdbee75f</dd>
     <dt>Hammer2.0-7b</dt><dd>HF revision 2e267cc2</dd>
   </dl></div></div>`;
}

/* ================================== BOOT ================================== */
let ACTIVE=new Set();
function select(i){ SEL=i; $$('#list .item').forEach(e=>e.classList.toggle('on',+e.dataset.i===i)); renderDetail(); }
function go(v){
  $$('#tabs button').forEach(b=>b.classList.toggle('on',b.dataset.v===v));
  $$('.view').forEach(s=>s.classList.toggle('on',s.id==='v-'+v));
  if(v==='compare') renderCompare();
  if(v==='overview') renderOverview();
  if(v==='prompts') renderPrompts();
  if(v==='about') renderAbout();
}
function renderChips(){
  $('#runchips').innerHTML=RUNS.map(k=>{
    const m=RMETA[k];
    return `<span class="chip${ACTIVE.has(k)?' on '+(m.side==='ours'?'ours':'base'):''}" data-run="${k}">${esc(m.short)}</span>`;
  }).join('');
  $$('#runchips .chip').forEach(el=>el.onclick=()=>{
    const k=el.dataset.run;
    ACTIVE.has(k)?ACTIVE.delete(k):ACTIVE.add(k);
    renderChips(); renderDetail();
  });
}
function optionsFor(sel,val){
  sel.innerHTML=RUNS.map(k=>`<option value="${k}"${k===val?' selected':''}>${esc(RMETA[k].label)}</option>`).join('');
}
function init(){
  S=P.samples; RUNS=P.run_order;
  RUNS.forEach(k=>RMETA[k]=P.runs[k].meta);
  RUNS.filter(k=>RMETA[k].tier==='matched').forEach(k=>ACTIVE.add(k));
  optionsFor($('#ffocus'),FOCUS); optionsFor($('#fvs'),VS);
  $('#fdiag').innerHTML='<option value="">any</option>'+P.diag_order.map(c=>`<option value="${c}">${esc(P.diag_label[c])}</option>`).join('');
  $('#fvsdiag').innerHTML='<option value="">any outcome</option>'+P.diag_order.map(c=>`<option value="${c}">${esc(P.diag_label[c])}</option>`).join('');

  const rerun=()=>applyFilters();
  ['#q','#fdom','#fcalls','#fdiag','#fvsmode','#fvsmetric','#fvsdiag'].forEach(s=>{
    const el=$(s); el.addEventListener(s==='#q'?'input':'change',rerun);
  });
  $('#ffocus').onchange=e=>{FOCUS=e.target.value;applyFilters();renderDetail()};
  $('#fvs').onchange=e=>{VS=e.target.value;applyFilters()};
  $('#qclr').onclick=()=>{$('#q').value='';applyFilters()};
  $('#freset').onclick=()=>{['#q','#fdom','#fcalls','#fdiag','#fvsmode','#fvsdiag'].forEach(s=>$(s).value='');applyFilters()};
  renderChips();
  $('#list').onclick=e=>{const it=e.target.closest('.item'); if(it) select(+it.dataset.i)};
  $$('#tabs button').forEach(b=>b.onclick=()=>go(b.dataset.v));
  $('#modalclose').onclick=()=>$('#modal').classList.remove('on');
  $('#modal').onclick=e=>{ if(e.target.id==='modal') $('#modal').classList.remove('on') };
  $('#themebtn').onclick=()=>{
    const t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',t);
    try{localStorage.setItem('nestful-theme',t)}catch(e){}
  };
  try{const t=localStorage.getItem('nestful-theme'); if(t) document.documentElement.setAttribute('data-theme',t)}catch(e){}
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape') $('#modal').classList.remove('on');
    if(e.key==='/'&&document.activeElement!==$('#q')){e.preventDefault();$('#q').focus()}
    if((e.key==='j'||e.key==='k')&&document.activeElement!==$('#q')&&!$('#modal').classList.contains('on')){
      const at=FILTERED.indexOf(SEL), nx=e.key==='j'?at+1:at-1;
      if(nx>=0&&nx<FILTERED.length){ select(FILTERED[nx]);
        const el=$(`#list .item[data-i="${FILTERED[nx]}"]`); if(el) el.scrollIntoView({block:'nearest'}); }
    }
  });
  applyFilters();
  if(FILTERED.length) select(FILTERED[0]);
  $('#boot').style.display='none';
  $('#app').style.visibility='visible';
}
(async function(){
  try{
    const b64=document.getElementById('payload').textContent.trim();
    const bin=Uint8Array.from(atob(b64),ch=>ch.charCodeAt(0));
    if(typeof DecompressionStream==='undefined') throw new Error('DecompressionStream unsupported');
    const ds=new DecompressionStream('gzip');
    const buf=await new Response(new Blob([bin]).stream().pipeThrough(ds)).arrayBuffer();
    P=JSON.parse(new TextDecoder().decode(buf));
    init();
  }catch(err){
    $('#boot').innerHTML='<div style="max-width:520px;text-align:center;line-height:1.6">'+
      '<b style="color:var(--bad)">Could not load the embedded data.</b><br>'+esc(err.message)+
      '<br><br>This page needs a browser with <span class="mono">DecompressionStream</span> '+
      '(Chrome 80+, Safari 16.4+, Firefox 113+).</div>';
  }
})();
