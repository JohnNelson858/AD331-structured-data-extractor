'use strict';
const $ = id => document.getElementById(id);
let inputTab = 'paste', busy = false, lastResult = null, auditFrames = [];
const labels = {SUCCESS:'Accepted', REPAIRED_VIA_REFLECTION:'Repaired via reflection', REPAIRED_VIA_HEURISTIC:'Repaired via heuristic', DLQ_FAILED:'DLQ · human review', DLQ_WRITE_FAILED:'DLQ storage failure'};
function message(text, kind='') { $('message').textContent=text; $('message').className='notice '+kind; }
function tab(name) {
  inputTab=name;
  ['paste','upload'].forEach(key=>{ $(key+'-panel').hidden=key!==name; $(key+'-tab').setAttribute('aria-selected',String(key===name)); });
}
$('paste-tab').onclick=()=>tab('paste'); $('upload-tab').onclick=()=>tab('upload');
function modeChanged() {
  const live=$('mode').value==='live';
  $('live-confirm').hidden=!live; $('scenario-control').hidden=live;
  $('confirm-live').checked=false;
  $('mode-note').textContent=live?'Extract your document with native OpenAI Structured Outputs. Each run uses API credits.':'Fixed sample responses demonstrate the pipeline. Your own documents require live extraction.';
}
$('mode').onchange=modeChanged;
$('load-sample').onclick=async()=>{
  try {
    const response=await fetch('/api/sample'); if(!response.ok) throw Error();
    const sample=await response.json(); $('document').value=sample.text; $('input-kind').value='text'; tab('paste');
    $('source').textContent=sample.text; $('source-kind').textContent='SYNTHETIC SAMPLE'; $('source-meta').textContent='Bundled fictional commercial invoice';
    message('Sample loaded. Choose a scenario, then select Run extraction.');
  } catch { message('Could not load the sample. Check that the local server is running.','error'); }
};
$('file').onchange=()=>message($('file').files[0]?'File selected. Run extraction to read and validate it.':'Choose a document to continue.');
function setBusy(value) {
  busy=value;
  document.querySelectorAll('form button, form input, form textarea, form select').forEach(el=>{ el.disabled=value; });
  if(!value) $('mode').options[1].disabled=!$('mode').dataset.live;
  $('run').textContent=value?'Extracting…':'Run extraction →';
}
function reset() {
  lastResult=null; auditFrames=[]; $('audit-log').replaceChildren(); $('audit-empty').hidden=false;
  $('download-json').disabled=true; $('download-audit').disabled=true;
  $('status').textContent='Running'; $('status').className=''; $('attempts').textContent='0';
  $('reconciliation').textContent='Not yet validated'; $('reconciliation').className='';
  $('json').textContent='Waiting for a fully validated record…';
  $('result-meta').textContent='Strict schema + cross-field validation';
  $('reconciliation-detail').hidden=true; $('dlq-panel').hidden=true;
  $('source').textContent='Reading the document…'; $('source-meta').textContent='';
}
function addAudit(event) {
  $('audit-empty').hidden=true;
  $('attempts').textContent=String(event.attempt);
  const row=document.createElement('details'); row.className='audit-event';
  if(/failed|error|insufficient|refused/.test(event.stage)) row.classList.add('failure');
  if(/reflection|heuristic|backoff/.test(event.stage)) row.classList.add('repair');
  if(/passed|validated/.test(event.stage)) row.classList.add('success');
  row.open=['validation_failed','reflection_prompt','dlq_written','audit_sink_failure','dlq_storage_failure'].includes(event.stage);
  const summary=document.createElement('summary');
  const index=document.createElement('span'); index.className='event-index'; index.textContent=String($('audit-log').children.length+1).padStart(2,'0');
  const stage=document.createElement('span'); stage.className='event-stage'; stage.textContent=event.stage.replaceAll('_',' ');
  const attempt=document.createElement('span'); attempt.className='event-attempt'; attempt.textContent='Attempt '+event.attempt;
  summary.append(index,stage,attempt);
  const details=document.createElement('pre');
  // Every value is inserted as text. Neither HTML documents nor model output
  // can become executable markup; prompts are displayed exactly as dispatched.
  details.textContent=event.detail.messages ? event.detail.messages.map(m=>m.role.toUpperCase()+'\n'+m.content).join('\n\n') : JSON.stringify(event.detail,null,2);
  row.append(summary,details); $('audit-log').append(row);
}
function showResult(result, report) {
  lastResult=result; $('status').textContent=labels[result.execution_status]||result.execution_status;
  $('attempts').textContent=String(result.attempts_used);
  $('result-meta').textContent=`${result.execution_status} · ${(result.elapsed_ms/1000).toFixed(2)}s · ${result.error_log.length} logged issue(s)`;
  $('download-audit').disabled=false;
  if(result.validated_data) {
    const invoice=result.validated_data;
    $('json').textContent=JSON.stringify(invoice,null,2); $('download-json').disabled=false;
    $('status').className='good'; $('reconciliation').textContent='✓ Within 0.02 tolerance'; $('reconciliation').className='good';
    $('reconciliation-detail').hidden=false;
    $('equation').textContent=`${invoice.subtotal} + ${invoice.tax_amount} ≈ ${invoice.total_amount} ${invoice.currency}`;
    $('checks').replaceChildren();
    ['✓ Quantity × price checked per line',`Line sum: ${report.line_items_sum} · subtotal difference: ${report.subtotal_difference}`,`Grand total difference: ${report.grand_total_difference} · tolerance: ${report.tolerance}`].forEach(text=>{ const div=document.createElement('div'); div.textContent=text; $('checks').append(div); });
    message('Record accepted after full Pydantic validation. Review the audit trail below.');
  } else {
    $('json').textContent='No record accepted.\n\nThe payload failed validation and must not enter downstream systems.';
    $('status').className='bad'; $('reconciliation').textContent='✕ No validated record'; $('reconciliation').className='bad';
    if(result.dlq_path) {
      $('dlq-panel').hidden=false; $('dlq-path').textContent=result.dlq_path;
      message('Expected failure contained: the record was saved to the DLQ for human review.');
    } else message('No record accepted. DLQ storage failed; operator action is required.','error');
  }
}
function frame(value) {
  auditFrames.push(value);
  if(value.type==='source') {
    $('source').textContent=value.text; $('source-kind').textContent=value.kind.toUpperCase()+' · EXTRACTED TEXT';
    $('source-meta').textContent=`${value.text.length.toLocaleString()} characters · SHA-256 ${value.sha256.slice(0,16)}…`;
    $('mode-badge').textContent=value.mode==='offline'?'OFFLINE · FIXED SAMPLE':'LIVE OPENAI';
  } else if(value.type==='audit') addAudit(value.event);
  else if(value.type==='result') showResult(value.result,value.reconciliation_report);
  else if(value.type==='error') throw Error(value.message);
}
async function run(simulate=false) {
  if(busy) return;
  const live=!simulate&&$('mode').value==='live';
  if(live&&!$('confirm-live').checked) { message('Confirm separately billed API use before running live extraction.','error'); return; }
  const data=new FormData(); data.append('mode',live?'live':'offline');
  data.append('scenario',simulate?'dlq':live?'success':$('scenario').value);
  data.append('reflection',String($('reflection').checked));
  if(live) data.append('confirm_live','yes');
  if(!simulate) {
    if(inputTab==='upload') {
      if(!$('file').files[0]) { message('Choose a file first, or switch to Paste and load the sample.','error'); return; }
      data.append('file',$('file').files[0]);
    } else { data.append('text',$('document').value); data.append('input_kind',$('input-kind').value); }
  }
  reset(); setBusy(true);
  $('mode-badge').textContent=live?'LIVE OPENAI':'OFFLINE · FIXED SAMPLE';
  message(simulate?'Running a controlled offline hard failure against the bundled sample…':live?'Running live extraction. Audit events appear as each stage completes…':'Running the offline sample scenario. No API calls or charges.','running');
  try {
    const response=await fetch('/api/extract',{method:'POST',body:data});
    if(!response.ok) { const error=await response.json(); throw Error(typeof error.detail==='string'?error.detail:'The request could not be processed.'); }
    const reader=response.body.getReader(), decoder=new TextDecoder(); let pending='';
    while(true) {
      const {value,done}=await reader.read(); pending+=decoder.decode(value||new Uint8Array(),{stream:!done});
      let newline; while((newline=pending.indexOf('\n'))>=0) { const line=pending.slice(0,newline); pending=pending.slice(newline+1); if(line.trim()) frame(JSON.parse(line)); }
      if(done) break;
    }
    if(pending.trim()) frame(JSON.parse(pending));
    if(!lastResult) throw Error('The stream ended before a final result. No record was accepted.');
  } catch(error) {
    $('status').textContent='Run incomplete'; $('status').className='bad';
    $('reconciliation').textContent='No accepted record';
    $('json').textContent='No record accepted.';
    message(error.message||'Could not reach the local server.','error');
    $('download-audit').disabled=auditFrames.length===0;
  } finally { setBusy(false); }
}
$('extract-form').onsubmit=event=>{ event.preventDefault(); run(); };
$('simulate').onclick=()=>run(true);
function download(name,value) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  const a=document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('download-json').onclick=()=>{if(lastResult?.validated_data) download('validated-invoice.json',lastResult.validated_data);};
$('download-audit').onclick=()=>download('extraction-audit.json',{frames:auditFrames,result:lastResult});
fetch('/api/config').then(r=>{if(!r.ok) throw Error();return r.json();}).then(config=>{
  if(config.live_available) { $('mode').dataset.live='true'; $('mode').options[1].disabled=false; $('mode').options[1].textContent='Live OpenAI · uses API credits'; }
}).catch(()=>message('Cannot reach the local server. Reload after starting the application.','error'));
