const state = {
  token: sessionStorage.getItem('mk_token') || '',
  case: null,
  evaluation: null,
  workflow: null,
  followup: null,
  carePlan: null,
  openapi: null,
  selectedOperation: null,
};

const $ = id => document.getElementById(id);
const show = (id, value) => { $(id).textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); };
const idempotencyKey = () => crypto.randomUUID();
const apiBase = '/api/v1';

function alertMessage(text) {
  const e = document.createElement('div');
  e.className = 'notice';
  e.textContent = text;
  $('alerts').replaceChildren(e);
  e.focus?.();
}

function clearAlert() { $('alerts').replaceChildren(); }

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
}

async function artifactRef(id, version = '0.1.0') {
  const canonical = JSON.stringify({id, version});
  return {id, version, digest: `sha256:${await sha256Hex(canonical)}`};
}

async function request(path, {method = 'GET', body = null, match = null, idempotent = body !== null, raw = false} = {}) {
  if (!state.token && path !== '/healthz') throw new Error('Jeton requis.');
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (body !== null) {
    headers['Content-Type'] = 'application/json';
    if (idempotent) headers['Idempotency-Key'] = idempotencyKey();
  }
  if (match !== null && match !== '') headers['If-Match'] = String(match).startsWith('"') ? String(match) : `"${match}"`;
  const url = raw ? path : `${apiBase}${path}`;
  const r = await fetch(url, {method, headers, body: body === null ? undefined : JSON.stringify(body)});
  const text = await r.text();
  let data = {};
  if (text) {
    try { data = JSON.parse(text); } catch { data = {detail: text}; }
  }
  if (!r.ok) {
    const err = new Error(`${data.code || r.status}: ${data.detail || data.title || 'Erreur'}`);
    err.status = r.status;
    err.payload = data;
    throw err;
  }
  return {data, etag: r.headers.get('ETag'), status: r.status, correlationId: r.headers.get('X-Correlation-ID')};
}

function guarded(fn) {
  return async (...args) => {
    try { clearAlert(); await fn(...args); }
    catch (e) { alertMessage(e instanceof Error ? e.message : String(e)); }
  };
}

function requireCase() {
  if (!state.case) throw new Error('Créer, sélectionner ou relire un cas avant cette action.');
  return state.case;
}

async function setCurrentCase(item) {
  state.case = item;
  if (item?.id) {
    sessionStorage.setItem('mk_case_id', item.id);
    $('case-badge').textContent = `cas ${item.id.slice(0, 8)} · r${item.revision}`;
  } else {
    sessionStorage.removeItem('mk_case_id');
    $('case-badge').textContent = 'aucun cas';
  }
  show('case-out', item || {});
}

async function refreshCurrentCase() {
  const id = state.case?.id || sessionStorage.getItem('mk_case_id');
  if (!id) return null;
  const {data} = await request(`/cases/${id}`);
  await setCurrentCase(data);
  return data;
}

function selectFirstCase(items) {
  if (!Array.isArray(items) || items.length === 0) return null;
  const remembered = sessionStorage.getItem('mk_case_id');
  return items.find(x => x.id === remembered) || items[items.length - 1];
}

$('token').value = state.token;
$('connect').onclick = guarded(async () => {
  state.token = $('token').value.trim();
  if (!state.token) throw new Error('Jeton requis.');
  sessionStorage.setItem('mk_token', state.token);
  const {data} = await request('/capabilities');
  $('mode-badge').textContent = `${data.mode} · ${data.network_scope}`;
  show('capabilities-out', data);
  try { await refreshCurrentCase(); } catch { await setCurrentCase(null); }
  await loadOpenApi();
});

$('disconnect').onclick = () => {
  state.token = '';
  state.case = null;
  state.evaluation = null;
  state.workflow = null;
  sessionStorage.removeItem('mk_token');
  sessionStorage.removeItem('mk_case_id');
  $('token').value = '';
  $('mode-badge').textContent = 'non connecté';
  $('case-badge').textContent = 'aucun cas';
  clearAlert();
};

document.querySelectorAll('nav button').forEach(btn => btn.onclick = guarded(async () => {
  document.querySelectorAll('nav button').forEach(x => x.setAttribute('aria-pressed', x === btn ? 'true' : 'false'));
  document.querySelectorAll('[data-panel]').forEach(p => { p.hidden = p.dataset.panel !== btn.dataset.view; });
  document.querySelector(`[data-panel="${btn.dataset.view}"] h1`)?.focus?.();
  if (btn.dataset.view === 'api') await loadOpenApi();
}));

$('create-case').onclick = guarded(async () => {
  const body = {subject_ref: $('subject').value.trim(), intended_use: 'engineering', language: 'fr', synthetic: true, context_refs: []};
  const created = (await request('/cases', {method: 'POST', body})).data;
  const active = (await request(`/cases/${created.id}/transitions`, {
    method: 'POST', body: {target: 'active', reason: 'Activation du cas synthétique depuis la console engineering.'}, match: created.revision,
  })).data;
  await setCurrentCase(active);
});

$('list-cases').onclick = guarded(async () => {
  const page = (await request('/cases')).data;
  show('case-out', page);
  const selected = selectFirstCase(page.items);
  if (selected) await setCurrentCase(selected);
});

$('refresh-case').onclick = guarded(async () => { requireCase(); await refreshCurrentCase(); });

$('add-observation').onclick = guarded(async () => {
  const current = requireCase();
  const presence = $('obs-presence').value;
  const value = presence === 'present' ? {kind: 'boolean', value: $('obs-value').value === 'true'} : null;
  const body = {
    concept: {system: 'urn:medikristal:synthetic', code: 'SYN-T1', version: '1'}, kind: 'test_result', presence, value,
    effective_at: new Date().toISOString(), status: 'final',
    source: {source_id: 'synthetic-ui', source_version: '1', record_id: crypto.randomUUID()}, quality: 'usable', method_ref: null, dependency_refs: [],
  };
  const {data} = await request(`/cases/${current.id}/observations`, {method: 'POST', body, match: current.revision});
  show('obs-out', data);
  await refreshCurrentCase();
});

$('list-observations').onclick = guarded(async () => { const c = requireCase(); show('obs-out', (await request(`/cases/${c.id}/observations`)).data); });

$('evaluate').onclick = guarded(async () => {
  const current = requireCase();
  const models = (await request('/knowledge/models')).data.items;
  const model = models.find(x => x.id === 'synthetic-binary') || models[0];
  if (!model) throw new Error('Aucun modèle synthétique disponible.');
  const body = {
    case_revision: current.revision, knowledge_release: await artifactRef('synthetic-release'),
    model_refs: [{id: model.id, version: model.version, digest: model.digest}], evaluation_time: new Date().toISOString(), intended_use: 'engineering',
  };
  const operation = (await request(`/cases/${current.id}/evaluations`, {method: 'POST', body, match: current.revision})).data;
  $('operation-id').value = operation.id;
  if (!operation.result_ref) throw new Error('L’opération ne contient pas encore de résultat.');
  state.evaluation = (await request(`/evaluations/${operation.result_ref}`)).data;
  sessionStorage.setItem('mk_evaluation_id', state.evaluation.id);
  show('evaluation-out', state.evaluation);
});

$('reload-evaluation').onclick = guarded(async () => {
  const id = state.evaluation?.id || sessionStorage.getItem('mk_evaluation_id');
  if (!id) throw new Error('Aucune évaluation connue.');
  state.evaluation = (await request(`/evaluations/${id}`)).data;
  show('evaluation-out', state.evaluation);
});

$('load-proposals').onclick = guarded(async () => { const c = requireCase(); show('proposal-out', (await request(`/cases/${c.id}/proposals`)).data); });

$('create-workflow').onclick = guarded(async () => {
  const current = requireCase();
  const protocols = (await request('/knowledge/protocols')).data.items;
  const protocol = protocols.find(x => x.id === 'synthetic-protocol') || protocols[0];
  if (!protocol) throw new Error('Aucun protocole synthétique disponible.');
  const body = {case_id: current.id, case_revision: current.revision, protocol_ref: {id: protocol.id, version: protocol.version, digest: protocol.digest}, authorization_policy_ref: await artifactRef('engineering-only'), intended_use: 'engineering'};
  state.workflow = (await request('/workflows', {method: 'POST', body})).data;
  show('workflow-out', state.workflow);
});

$('list-workflows').onclick = guarded(async () => {
  const c = requireCase();
  const page = (await request(`/cases/${c.id}/workflows`)).data;
  show('workflow-out', page);
  state.workflow = page.items?.at(-1) || state.workflow;
});

$('transition-workflow').onclick = guarded(async () => {
  const c = requireCase();
  if (!state.workflow) throw new Error('Créer ou lister un workflow avant une transition.');
  const body = {action: $('workflow-action').value, reason: 'Action depuis la console engineering.', case_revision: c.revision};
  state.workflow = (await request(`/workflows/${state.workflow.id}/transitions`, {method: 'POST', body, match: state.workflow.revision})).data;
  show('workflow-out', state.workflow);
});

$('treatments').onclick = guarded(async () => {
  const c = requireCase();
  if (!state.evaluation) {
    const id = sessionStorage.getItem('mk_evaluation_id');
    if (id) state.evaluation = (await request(`/evaluations/${id}`)).data;
  }
  if (!state.evaluation) throw new Error('Une évaluation est requise.');
  const protocols = (await request('/knowledge/protocols')).data.items;
  const protocol = protocols.find(x => x.id === 'synthetic-protocol') || protocols[0];
  const body = {case_revision: c.revision, evaluation_id: state.evaluation.id, protocol_refs: [{id: protocol.id, version: protocol.version, digest: protocol.digest}]};
  const operation = (await request(`/cases/${c.id}/treatment-evaluations`, {method: 'POST', body, match: c.revision})).data;
  $('operation-id').value = operation.id;
  show('treatment-out', (await request(`/cases/${c.id}/treatment-options`)).data);
});

$('load-treatments').onclick = guarded(async () => { const c = requireCase(); show('treatment-out', (await request(`/cases/${c.id}/treatment-options`)).data); });

$('create-followup').onclick = guarded(async () => {
  const c = requireCase();
  const due = new Date(Date.now() + 60 * 60 * 1000).toISOString();
  state.followup = (await request('/followups', {method: 'POST', body: {case_id: c.id, origin_ref: `ui:${crypto.randomUUID()}`, owner_ref: 'professional:engineering', due_at: due, reason: 'Suivi synthétique depuis la console.'}})).data;
  show('followup-out', state.followup);
});

$('load-followups').onclick = guarded(async () => { const c = requireCase(); const page = (await request(`/cases/${c.id}/followups`)).data; show('followup-out', page); state.followup = page.items?.at(-1) || state.followup; });

$('create-care-plan').onclick = guarded(async () => {
  const c = requireCase();
  const tasks = (await request(`/cases/${c.id}/followups`)).data.items;
  const options = (await request(`/cases/${c.id}/treatment-options`)).data.items;
  const body = {case_revision: c.revision, treatment_option_ids: options.filter(x => x.status === 'proposed').map(x => x.id), followup_task_ids: tasks.filter(x => x.status !== 'completed' && x.status !== 'cancelled').map(x => x.id), reason: 'Plan synthétique depuis la console.'};
  state.carePlan = (await request(`/cases/${c.id}/care-plans`, {method: 'POST', body, match: c.revision})).data;
  show('care-plan-out', state.carePlan);
});

$('load-care-plans').onclick = guarded(async () => { const c = requireCase(); const page = (await request(`/cases/${c.id}/care-plans`)).data; show('care-plan-out', page); state.carePlan = page.items?.at(-1) || state.carePlan; });

$('create-site').onclick = guarded(async () => {
  const body = {owner: 'synthetic-facility', external_id: `site-${crypto.randomUUID()}`, name: 'Site synthétique', timezone: 'America/Toronto', status: 'active'};
  show('site-out', (await request('/sites', {method: 'POST', body})).data);
});

$('list-sites').onclick = guarded(async () => show('site-out', (await request('/sites')).data));
$('list-resources').onclick = guarded(async () => show('resource-out', (await request('/managed-resources')).data));
$('list-procedures').onclick = guarded(async () => show('procedure-out', (await request('/procedure-catalog')).data));
$('list-resource-capabilities').onclick = guarded(async () => show('resource-capability-out', (await request('/resource-capabilities')).data));
$('list-costs').onclick = guarded(async () => show('cost-out', (await request('/cost-quotes')).data));
$('load-config').onclick = guarded(async () => show('config-out', (await request('/configuration')).data));
$('load-capabilities').onclick = guarded(async () => show('capabilities-out', (await request('/capabilities')).data));

$('load-concepts').onclick = guarded(async () => show('concepts-out', (await request('/knowledge/concepts?q=SYN')).data));
$('load-assertions').onclick = guarded(async () => show('assertions-out', (await request('/knowledge/assertions')).data));
$('load-evidence').onclick = guarded(async () => show('evidence-out', (await request('/knowledge/evidence')).data));
$('load-models').onclick = guarded(async () => show('models-out', (await request('/knowledge/models')).data));
$('load-protocols').onclick = guarded(async () => show('protocols-out', (await request('/knowledge/protocols')).data));
$('load-policies').onclick = guarded(async () => show('policies-out', (await request('/knowledge/optimization-policies')).data));
$('load-sources').onclick = guarded(async () => show('sources-out', (await request('/sources')).data));
$('load-contributions').onclick = guarded(async () => show('contrib-out', (await request('/contributions')).data));

$('load-operation').onclick = guarded(async () => {
  const id = $('operation-id').value.trim();
  if (!id) throw new Error('Operation UUID requis.');
  show('operation-out', (await request(`/operations/${id}`)).data);
});
$('load-health').onclick = guarded(async () => show('health-out', (await request('/healthz', {raw: true})).data));

function openApiOperations(doc) {
  const operations = [];
  for (const [path, item] of Object.entries(doc.paths || {})) {
    for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
      const op = item[method];
      if (!op) continue;
      operations.push({method: method.toUpperCase(), path, operationId: op.operationId || '', permission: op['x-permission'] || '', summary: op.summary || ''});
    }
  }
  return operations.sort((a, b) => a.path.localeCompare(b.path) || a.method.localeCompare(b.method));
}

function renderOperations() {
  if (!state.openapi) return;
  const filter = $('api-filter').value.trim().toLowerCase();
  const list = $('api-operation-list');
  list.replaceChildren();
  for (const operation of openApiOperations(state.openapi)) {
    const haystack = `${operation.method} ${operation.path} ${operation.operationId} ${operation.permission}`.toLowerCase();
    if (filter && !haystack.includes(filter)) continue;
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('role', 'listitem');
    button.innerHTML = `<span class="method"></span><span class="operation-path"></span>`;
    button.querySelector('.method').textContent = operation.method;
    button.querySelector('.operation-path').textContent = operation.path;
    button.onclick = () => selectOperation(operation, button);
    list.append(button);
  }
}

function selectOperation(operation, button) {
  state.selectedOperation = operation;
  document.querySelectorAll('#api-operation-list button').forEach(x => x.removeAttribute('aria-current'));
  button?.setAttribute('aria-current', 'true');
  $('api-title').textContent = operation.operationId || `${operation.method} ${operation.path}`;
  $('api-meta').textContent = `${operation.method} ${operation.path}${operation.permission ? ` · permission ${operation.permission}` : ''}`;
  $('api-path').value = operation.path;
  $('api-query').value = '';
  $('api-match').value = '';
  $('api-body').value = ['POST', 'PUT', 'PATCH'].includes(operation.method) ? '{\n  \n}' : '';
  $('api-result').textContent = '';
}

async function loadOpenApi() {
  if (state.openapi) { renderOperations(); return; }
  const r = await fetch('/openapi.json');
  if (!r.ok) throw new Error(`Impossible de charger OpenAPI (${r.status}).`);
  state.openapi = await r.json();
  renderOperations();
}

$('api-filter').oninput = renderOperations;
$('api-clear').onclick = () => { $('api-result').textContent = ''; $('api-body').value = ''; $('api-query').value = ''; $('api-match').value = ''; };
$('api-execute').onclick = guarded(async () => {
  const operation = state.selectedOperation;
  if (!operation) throw new Error('Sélectionner une opération.');
  let path = $('api-path').value.trim();
  if (!path) throw new Error('Chemin requis.');
  if (path.includes('{')) throw new Error('Remplacer tous les paramètres {…} du chemin avant exécution.');
  const qs = $('api-query').value.trim().replace(/^\?/, '');
  if (qs) path += `?${qs}`;
  let body = null;
  const rawBody = $('api-body').value.trim();
  if (rawBody) {
    try { body = JSON.parse(rawBody); } catch (e) { throw new Error(`JSON invalide: ${e.message}`); }
  }
  const result = await request(path, {method: operation.method, body, match: $('api-match').value.trim() || null, idempotent: body !== null});
  show('api-result', {status: result.status, correlation_id: result.correlationId, etag: result.etag, body: result.data});
});

if (state.token) $('connect').click();
