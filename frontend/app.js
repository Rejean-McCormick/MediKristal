const state = { token: sessionStorage.getItem('mk_token') || '', case: null, evaluation: null, workflow: null };
const $ = id => document.getElementById(id);
const show = (id, value) => { $(id).textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); };
const key = () => crypto.randomUUID();
function alertMessage(text) { const e=document.createElement('div'); e.className='notice'; e.textContent=text; $('alerts').replaceChildren(e); }

async function api(path, {method='GET', body=null, match=null}={}) {
  if (!state.token) throw new Error('Jeton requis.');
  const headers = {Authorization:`Bearer ${state.token}`};
  if (body !== null) { headers['Content-Type']='application/json'; headers['Idempotency-Key']=key(); }
  if (match !== null) headers['If-Match']=`"${match}"`;
  const r = await fetch(`/api/v1${path}`, {method, headers, body: body===null ? undefined : JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) throw new Error(`${data.code || r.status}: ${data.detail || data.title || 'Erreur'}`);
  return {data, etag:r.headers.get('ETag')};
}
function guarded(fn){ return async (...args)=>{ try { $('alerts').replaceChildren(); await fn(...args); } catch(e){ alertMessage(e.message); } }; }

$('token').value = state.token;
$('connect').onclick = guarded(async()=>{
  state.token=$('token').value.trim(); sessionStorage.setItem('mk_token',state.token);
  const {data}=await api('/capabilities'); $('mode-badge').textContent=`${data.mode} · ${data.network_scope}`; show('capabilities-out',data);
});

document.querySelectorAll('nav button').forEach(btn=>btn.onclick=()=>{
  document.querySelectorAll('nav button').forEach(x=>x.setAttribute('aria-pressed', x===btn ? 'true':'false'));
  document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==btn.dataset.view);
  document.querySelector(`[data-panel="${btn.dataset.view}"] h1`)?.focus?.();
});

$('create-case').onclick=guarded(async()=>{
  const body={subject_ref:$('subject').value,intended_use:'engineering',language:'fr',synthetic:true,context_refs:[]};
  const {data}=await api('/cases',{method:'POST',body}); state.case=data; show('case-out',data);
});
$('add-observation').onclick=guarded(async()=>{
  if(!state.case) throw new Error('Créer ou relire un cas avant d’ajouter une observation.');
  let presence=$('obs-presence').value; let value=null;
  if(presence==='present') value={kind:'boolean',value:$('obs-value').value==='true'};
  const body={concept:{system:'urn:medikristal:synthetic',code:'SYN-T1',version:'1'},kind:'test_result',presence,value,effective_at:new Date().toISOString(),status:'final',source:{source_id:'synthetic-ui',source_version:'1',record_id:crypto.randomUUID()},quality:'usable',method_ref:null,dependency_refs:[]};
  const {data}=await api(`/cases/${state.case.id}/observations`,{method:'POST',body,match:state.case.revision}); show('obs-out',data);
  state.case=(await api(`/cases/${state.case.id}`)).data; show('case-out',state.case);
});
$('evaluate').onclick=guarded(async()=>{
  if(!state.case) throw new Error('Cas requis.');
  const model=(await api('/knowledge/models')).data.items[0];
  const body={case_revision:state.case.revision,knowledge_release:{id:'synthetic-release',version:'0.1.0',digest:'sha256:'+'a'.repeat(64)},model_refs:[{id:model.id,version:model.version,digest:model.digest}],evaluation_time:new Date().toISOString(),intended_use:'engineering'};
  const op=(await api(`/cases/${state.case.id}/evaluations`,{method:'POST',body,match:state.case.revision})).data;
  $('operation-id').value=op.id;
  state.evaluation=(await api(`/evaluations/${op.result_ref}`)).data; show('evaluation-out',state.evaluation);
});
$('load-proposals').onclick=guarded(async()=>{ if(!state.case) throw new Error('Cas requis.'); show('proposal-out',(await api(`/cases/${state.case.id}/proposals`)).data); });
$('refresh-case').onclick=guarded(async()=>{ if(!state.case) throw new Error('Cas requis.'); state.case=(await api(`/cases/${state.case.id}`)).data; show('professional-case',state.case); });
$('create-workflow').onclick=guarded(async()=>{ if(!state.case) throw new Error('Cas requis.'); const body={case_id:state.case.id,case_revision:state.case.revision,protocol_ref:{id:'synthetic-protocol',version:'0.1.0',digest:(await api('/knowledge/protocols')).data.items[0].digest},authorization_policy_ref:{id:'engineering-only',version:'0.1.0',digest:'sha256:'+'b'.repeat(64)},intended_use:'engineering'}; state.workflow=(await api('/workflows',{method:'POST',body})).data; show('workflow-out',state.workflow); });
$('treatments').onclick=guarded(async()=>{ if(!state.case||!state.evaluation) throw new Error('Cas et évaluation requis.'); const body={case_revision:state.case.revision,evaluation_id:state.evaluation.id,protocol_refs:[{id:'synthetic-protocol',version:'0.1.0',digest:'sha256:'+'c'.repeat(64)}]}; const o=(await api(`/cases/${state.case.id}/treatment-evaluations`,{method:'POST',body,match:state.case.revision})).data; show('treatment-out',(await api(`/cases/${state.case.id}/treatment-options`)).data); $('operation-id').value=o.id; });
$('load-followups').onclick=guarded(async()=>{ if(!state.case) throw new Error('Cas requis.'); show('followup-out',(await api(`/cases/${state.case.id}/followups`)).data); });
$('create-site').onclick=guarded(async()=>{ const body={owner:'synthetic-facility',external_id:'site-'+crypto.randomUUID(),name:'Site synthétique',timezone:'America/Toronto',status:'active'}; show('site-out',(await api('/sites',{method:'POST',body})).data); });
$('list-sites').onclick=guarded(async()=>show('site-out',(await api('/sites')).data));
$('load-config').onclick=guarded(async()=>show('config-out',(await api('/configuration')).data));
$('load-capabilities').onclick=guarded(async()=>show('capabilities-out',(await api('/capabilities')).data));
$('load-models').onclick=guarded(async()=>show('models-out',(await api('/knowledge/models')).data));
$('load-protocols').onclick=guarded(async()=>show('protocols-out',(await api('/knowledge/protocols')).data));
$('load-contributions').onclick=guarded(async()=>show('contrib-out',(await api('/contributions')).data));
$('load-operation').onclick=guarded(async()=>show('operation-out',(await api(`/operations/${$('operation-id').value}`)).data));

if(state.token) $('connect').click();
