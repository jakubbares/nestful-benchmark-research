import fs from 'fs';
import readline from 'readline';

// --- the exact functions the viewer will use -------------------------------
const ESC = {'"':'\\"','\\':'\\\\','\n':'\\n','\r':'\\r','\t':'\\t','\b':'\\b','\f':'\\f'};
function pyJsonStr(s){                     // Python json.dumps(<str>), ensure_ascii=True
  let o = '"';
  for (const ch of s){
    const c = ch.codePointAt(0);
    if (ESC[ch]) o += ESC[ch];
    else if (c < 0x20 || c >= 0x7f){
      if (c > 0xffff){
        const v = c - 0x10000;
        o += '\\u' + (0xd800 + (v >> 10)).toString(16).padStart(4,'0')
           + '\\u' + (0xdc00 + (v & 0x3ff)).toString(16).padStart(4,'0');
      } else o += '\\u' + c.toString(16).padStart(4,'0');
    } else o += ch;
  }
  return o + '"';
}
function unescapeFormatBraces(s){ return s.replace(/\{\{/g,'{').replace(/\}\}/g,'}'); }
function buildPrompt(P, sample, shots, model, checklist){
  const tools = '[' + sample.ts.map(i => P.specs[i]).join(', ') + ']';
  const inject = tpl => checklist ? tpl.replace('[BEGIN OF QUERY]', P.prompts.checklist + '[BEGIN OF QUERY]') : tpl;
  if (model === 'xLAM-7b-fc-r'){
    const tpl = inject(unescapeFormatBraces(P.prompts.templates['xLAM-7b-fc-r']));
    return tpl
      .replace('{FUNCTION_STR}', () => pyJsonStr(tools))
      .replace('{ICL_EXAMPLES}', () => P.prompts.icl_str_xlam[String(shots)])
      .replace('{QUERY}', () => sample.q);
  }
  return inject(P.prompts.templates['Hammer2.0-7b'])
    .replace('{FUNCTION_STR}', () => pyJsonStr(tools))
    .replace('{ICL_EXAMPLES}', () => P.prompts.icl_str[String(shots)])
    .replace('{QUERY}', () => sample.q);
}
// ---------------------------------------------------------------------------
const P = JSON.parse(fs.readFileSync('payload.json','utf8'));
const byId = Object.fromEntries(P.samples.map(s => [s.id, s]));
const ROOT = '/Users/jakubbares/Library/CloudStorage/GoogleDrive-bares.jakub@gmail.com/My Drive/CIIRC PhD/FIrst-Effort/nestful-qwen3-4b/';

for (const [rel, shots, model, checklist] of [
  ['matched_results/qwen3_3shot/output.jsonl',3,'Qwen3-4B-Instruct-2507',false],
  ['matched_results/hammer_1shot/output.jsonl',1,'Hammer2.0-7b',false],
  ['matched_results/hammer_3shot/output.jsonl',3,'Hammer2.0-7b',false],
  ['matched_results/qwen3_1shot/output.jsonl',1,'Qwen3-4B-Instruct-2507',false],
  ['matched_results/xlam_3shot/output.jsonl',3,'xLAM-7b-fc-r',false],
  ['matched_results/xlam_1shot/output.jsonl',1,'xLAM-7b-fc-r',false],
  ['matched_results/qwen3thinking_3shot/output.jsonl',3,'Qwen3-4B-Thinking-2507',false],
  ['matched_results/qwen3thinking_1shot/output.jsonl',1,'Qwen3-4B-Thinking-2507',false],
  ['matched_results/hammer_3shot_checklist/output.jsonl',3,'Hammer2.0-7b',true],
  ['matched_results/xlam_3shot_checklist/output.jsonl',3,'xLAM-7b-fc-r',true],
  ['matched_results/qwen3_3shot_checklist/output.jsonl',3,'Qwen3-4B-Instruct-2507',true],
  ['matched_results/qwen3thinking_3shot_checklist/output.jsonl',3,'Qwen3-4B-Thinking-2507',true],
]){
  let ok=0, bad=0, firstBad=null;
  const rl = readline.createInterface({input: fs.createReadStream(ROOT+rel), crlfDelay: Infinity});
  for await (const line of rl){
    const r = JSON.parse(line);
    const built = buildPrompt(P, byId[r.sample_id], shots, model, checklist);
    if (built === r.input) ok++; else { bad++; if(!firstBad) firstBad = r.sample_id; }
  }
  console.log(rel.padEnd(48), `exact ${ok}  mismatch ${bad}`, firstBad ? `first=${firstBad}` : '');
}
