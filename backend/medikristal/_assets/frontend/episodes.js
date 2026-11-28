"use strict";

const screen = document.querySelector("#screen");
const message = document.querySelector("#message");
const labels = {present: "Présent", absent: "Absent", unknown: "Incertain", not_assessed: "Non évalué"};
const testNames = {screen: "le test rapide", direct: "l’examen direct", confirm: "l’examen de confirmation"};
const resultNames = {screen: "du test rapide", direct: "de l’examen direct", confirm: "de l’examen de confirmation"};
const reviewLabels = {
  confirmed: "Syndrome fictif A retenu", excluded: "Syndrome fictif A écarté",
  no_indication: "Aucune indication dans ce scénario"
};
const money = new Intl.NumberFormat("fr-CA", {style: "currency", currency: "CAD"});
let catalog;
let active;
let view = "home";
let writing = false;
let polling = false;

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML.replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}
const h = escapeHtml;

function notify(text = "", error = false) {
  message.textContent = text;
  message.hidden = !text;
  message.classList.toggle("error", error);
}

async function api(path, method = "GET", body, revision) {
  const headers = {};
  const token = sessionStorage.getItem("medikristalEpisodeToken");
  if (token) headers.Authorization = `Bearer ${token}`;
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["Idempotency-Key"] = crypto.randomUUID();
    if (revision !== undefined) headers["If-Match"] = `"${revision}"`;
  }
  const response = await fetch(`/api/v2${path}`, {method, headers, body: JSON.stringify(body)});
  const value = await response.json();
  if (!response.ok) {
    const error = new Error(value.detail || "Action indisponible.");
    error.status = response.status;
    throw error;
  }
  return value;
}

function errorHandler(error) {
  if (error.status === 401) {
    screen.innerHTML = `<div class="panel"><h2 id="screen-heading">Accéder aux épisodes</h2>
      <form id="sign-in" class="fields"><label>Jeton professionnel
      <input type="password" name="token" required autocomplete="off"></label>
      <button class="primary">Ouvrir</button></form></div>`;
    return;
  }
  notify(error.message || "L’action a échoué.", true);
}

async function home() {
  view = "home";
  active = undefined;
  notify();
  const episodes = await api("/episodes");
  if (view !== "home") return;
  screen.innerHTML = `<div class="panel"><h2 id="screen-heading">Mes épisodes</h2>
    ${catalog.permissions.collect ? `<form id="start" class="fields"><label>Quel problème est à examiner ?
    <input name="title" required maxlength="120" placeholder="Ex. Inconfort depuis ce matin"></label>
    <button class="primary">Ouvrir un épisode</button></form>` : ""}
    <ul class="rows">${episodes.map(item => `<li><button type="button" data-open="${h(item.id)}">${h(item.title)}</button>
      <span class="meta">${item.status === "closed" ? "Clôturé" : "En cours"}</span></li>`).join("")}</ul>
    ${episodes.length ? "" : '<p class="meta">Aucun épisode ouvert.</p>'}
    </div>`;
}

function select(name, options, current) {
  return `<select name="${h(name)}">${Object.entries(options).map(([value, label]) =>
    `<option value="${h(value)}"${current === value ? " selected" : ""}>${h(label)}</option>`).join("")}</select>`;
}

function renderEpisode() {
  const a = active;
  const phase = a.assessment;
  const open = a.status === "open";
  const permissions = catalog.permissions;
  const candidates = a.choices.map((choice, i) => `<div class="choice">
    <strong>${h(choice.label)}${choice.conditional ? " puis confirmation selon le résultat" : ""}</strong>
    <p class="meta">${choice.minutes ?? "Délai inconnu"}${choice.minutes === null ? "" : " min jusqu’au résultat"}
      · ${choice.expected_cost_minor === null ? "Coût inconnu" : money.format(choice.expected_cost_minor / 100)}
      ${choice.conditional ? " en moyenne" : ""}</p>
    ${choice.reason ? `<p class="meta">${h(choice.reason)}</p>` : ""}
    ${permissions.order && choice.available ? `<button class="${i === 0 ? "primary" : ""}" type="button" data-order="${h(choice.test)}">Demander ${h(testNames[choice.test])}</button>` : ""}
    </div>`).join("");
  const resultHistory = Object.values(a.reported_orders || {}).map(item => `<li>${h(item.label)} ·
    <strong>${h(catalog.results[item.value])}</strong>${item.result_version > 1 ? " · corrigé" : ""}
    ${permissions.lab ? `<details class="no-print"><summary>Corriger le résultat</summary>
    <form class="lab fields" data-id="${h(item.id)}" data-version="${item.result_version + 1}">
    <label>Nouveau résultat${select("value", catalog.results, item.value)}</label><button>Transmettre la correction</button></form></details>` : ""}</li>`).join("");
  const canAccept = Object.hasOwn(reviewLabels, phase.review_kind);
  const blocked = a.choices.length > 0 && !a.choices.some((option) => option.available);
  const showDecision = canAccept || blocked || phase.phase === "urgent" || phase.phase === "review";
  const plansPanel = open && candidates ? `<section class="panel"><h3>Examens possibles</h3>${candidates}</section>` : "";
  screen.innerHTML = `<h2 id="screen-heading">${h(a.title)}</h2>
    <section class="next ${phase.phase === "urgent" ? "urgent" : ""}" aria-live="polite">
      <h3>${open ? h(phase.phase === "urgent" ? phase.next : a.order ? "Résultat en attente" : blocked ? "Revoir les options avec l’équipe." : phase.next) : "Épisode clôturé"}</h3>
      <p>${h(open && a.order && phase.phase !== "urgent" ? a.order.label + " · demande acceptée par le laboratoire simulé." : phase.reason)}</p>
      ${phase.hypothesis ? `<p><strong>${h(phase.hypothesis)}</strong></p>` : ""}
      ${phase.estimate ? `<p class="meta">Estimation du scénario · ${phase.estimate.value_percent} %</p>` : ""}
      ${open && phase.review_kind === "confirmed" ? "<p>Proposition du scénario : suivi fictif A.</p>" : ""}
      ${a.decision_needs_review ? "<p><strong>Le résultat a changé depuis la décision signée.</strong></p>" : ""}
    </section>
    <div class="grid"><div>
      ${plansPanel}
      <section class="panel"><h3>Observations</h3>
      ${open && permissions.collect ? `<form id="observations" class="fields">
        ${Object.entries(catalog.observations).map(([code, name]) =>
          `<label>${h(name)}${select(code, labels, a.observations[code] || "not_assessed")}</label>`).join("")}
        <button class="primary">Enregistrer les observations</button></form>`
        : `<ul class="rows">${Object.entries(a.observations).map(([code, value]) =>
          `<li>${h(catalog.observations[code])} · ${h(labels[value])}</li>`).join("")}</ul>`}
      </section>
      ${resultHistory || a.order ? `<section class="panel"><h3>Résultats</h3><ul class="rows">${resultHistory}</ul>
        ${a.order && permissions.order ? `<details class="no-print"><summary>Annuler la demande</summary>
        <form class="cancel fields" data-id="${h(a.order.id)}"><label>Motif<input name="reason" maxlength="300" required></label>
        <button>Annuler l’examen</button></form></details>` : ""}
        ${a.order && permissions.lab ? `<details class="no-print"><summary>Laboratoire simulé</summary>
        <form class="lab fields" data-id="${h(a.order.id)}" data-version="1">
          <label>Résultat ${h(resultNames[a.order.test])}${select("value", catalog.results, "positive")}</label>
          <button class="primary">Transmettre le résultat</button>
        </form></details>` : ""}</section>` : ""}
      ${open && permissions.sign && !a.order ? `<section class="panel">${showDecision ? "<h3>Décision</h3>" : ""}
      ${showDecision ? "" : "<details><summary>Transférer pour revue</summary>"}
      <form id="decision" class="fields">
        <label>Décision${select("disposition", {...(canAccept ? {accept: "Valider la proposition"} : {}), escalate: "Transférer pour revue"}, canAccept ? "accept" : "escalate")}</label>
        <label>Motif ou note<input name="note" maxlength="500"></label><button>Signer et clôturer</button>
      </form>${showDecision ? "" : "</details>"}</section>` : ""}
      ${a.decision ? `<section class="panel"><h3>${a.decision_needs_review ? "Décision précédente" : "Décision signée"}</h3>
        <p>${h(a.decision.summary)} · ${h(a.decision.principal)}</p>
        <p>${h(a.decision.reason)} ${h(a.decision.note)}</p>
        ${open ? "" : '<button type="button" id="print">Imprimer le compte rendu</button>'}</section>` : ""}
      ${!open && permissions.verify && !a.outcome_verified ? `<details class="panel"><summary>Vérifier l’issue de façon indépendante</summary>
        <form id="outcome" class="fields"><label>Issue${select("value", {confirmed: "Confirmée", excluded: "Écartée", unverified: "Non vérifiée"})}</label>
        <label>Référence de la preuve<input name="evidence" maxlength="300" required></label><button>Enregistrer l’issue</button></form>
      </details>` : ""}
      </div>
      <aside class="panel no-print"><h3>Suivi de l’épisode</h3>
        ${permissions.share ? `<details><summary>Transmettre à un professionnel</summary>
        <form id="share"><label>Identifiant du professionnel<input name="principal" required maxlength="128"></label><button>Donner accès</button></form></details>` : ""}
        ${permissions.collect ? `<details><summary>Contribution aux statistiques</summary>
        <form id="consent" class="fields"><label>Inclure dans les statistiques de simulation${select("include", {no: "Non", yes: "Oui"}, a.sharing ? "yes" : "no")}</label><button>Enregistrer le choix</button></form></details>` : ""}
        <details><summary>Procédure et sources</summary><p>${h(a.procedure.source)} · v${h(a.procedure.version)}</p><p>${h(a.model.source)}</p></details>
      </aside></div>`;
}

async function openEpisode(id) {
  const next = await api(`/episodes/${id}`);
  view = "episode";
  active = next;
  history.replaceState(null, "", `/episodes#${id}`);
  renderEpisode();
}

async function references() {
  view = "references";
  screen.innerHTML = `<div class="panel"><h2 id="screen-heading">Référentiels publics</h2>
    <form id="search" class="fields"><label>Nom ou code<input name="q" required maxlength="120"></label>
    <button class="primary">Rechercher</button></form><ul class="rows" id="lookup"></ul></div>`;
}

async function operations() {
  view = "operations";
  const resources = await api("/resources");
  if (view !== "operations") return;
  screen.innerHTML = `<h2 id="screen-heading">Ressources de simulation</h2>${Object.entries(resources).map(([test, row]) => `
    <section class="panel"><h3>${h(row.label)} · ${row.available} disponible(s)</h3>
    <form class="capacity fields" data-test="${h(test)}" data-revision="${row.revision}">
    <label>Délai jusqu’au résultat (min)<input type="number" name="minutes" min="1" max="1440" value="${row.minutes ?? ""}"></label>
    <label>Coût en dollars<input type="number" name="cost" min="0" max="1000000" step=".01" value="${row.cost_minor === null ? "" : row.cost_minor / 100}"></label>
    <label>Capacité<input type="number" name="capacity" min="0" max="100" required value="${row.capacity}"></label>
    <button>Mettre à jour</button></form></section>`).join("")}`;
}

async function statistics() {
  view = "statistics";
  const data = await api("/statistics");
  if (view !== "statistics") return;
  screen.innerHTML = `<section class="panel"><h2 id="screen-heading">Statistiques de simulation</h2>
  <p>Épisodes clôturés dont le créateur a choisi la contribution.</p>
  <ul class="rows">${Object.entries(data.scenario_counts).map(([code, count]) =>
    `<li>${h(reviewLabels[code] || "Autre issue")} · ${count}</li>`).join("") || "<li>Aucune contribution.</li>"}
  </ul><p>Issues indépendamment vérifiées · ${data.verified_evaluation.count}
    ${data.verified_evaluation.brier === null ? "" : ` · Score de Brier ${data.verified_evaluation.brier.toLocaleString("fr-CA")}`}</p>
  <p class="meta">${h(data.model.source)} · ${h(data.model.population)}</p></section>`;
}

async function init() {
  catalog = await api("/catalog");
  document.querySelector("#operations").hidden = !catalog.permissions.resources;
  document.querySelector("#statistics").hidden = !catalog.permissions.statistics;
  const id = location.hash.slice(1);
  if (/^[0-9a-f-]{36}$/i.test(id)) {
    await openEpisode(id);
  } else {
    await home();
  }
}

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button");
  if (!target || writing) return;
  try {
    if (target.id === "home") {
      history.replaceState(null, "", "/episodes");
      await home();
    } else if (target.id === "references") {
      notify();
      await references();
    } else if (target.id === "statistics") {
      notify();
      await statistics();
    } else if (target.id === "operations") {
      notify();
      await operations();
    } else if (target.id === "print") {
      window.print();
    } else if (target.dataset.open) {
      notify();
      await openEpisode(target.dataset.open);
    } else if (target.dataset.order) {
      writing = true;
      target.disabled = true;
      active = await api(`/episodes/${active.id}/orders`, "POST", {test: target.dataset.order}, active.revision);
      renderEpisode();
      notify("Demande transmise au laboratoire simulé.");
    }
  } catch (error) {
    errorHandler(error);
    if (active && view === "episode" && [409, 412].includes(error.status)) {
      active = await api(`/episodes/${active.id}`).catch(() => active);
      renderEpisode();
    }
  } finally {
    writing = false;
    target.disabled = false;
  }
});

document.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (writing) return;
  const form = event.target;
  const fields = Object.fromEntries(new FormData(form));
  const button = form.querySelector("button");
  writing = true;
  button.disabled = true;
  try {
    if (form.id === "sign-in") {
      sessionStorage.setItem("medikristalEpisodeToken", fields.token);
      await init();
      return;
    }
    if (form.id === "start") {
      const created = await api("/episodes", "POST", fields);
      await openEpisode(created.id);
      return;
    }
    if (form.id === "search") {
      const results = await api(`/references?q=${encodeURIComponent(fields.q)}`);
      const lookup = document.querySelector("#lookup");
      if (lookup) lookup.innerHTML = results.items.map(item =>
        `<li><strong>${h(item.label || item.code)}</strong> · ${h(item.code)}<br>
        <span class="meta">${h(item.source)} · ${h(item.filename)}</span></li>`).join("") || "<li>Aucun résultat.</li>";
      return;
    }
    if (form.classList.contains("capacity")) {
      await api(`/resources/${form.dataset.test}`, "PUT", {
        minutes: fields.minutes ? Number(fields.minutes) : null,
        cost_minor: fields.cost ? Math.round(Number(fields.cost) * 100) : null,
        capacity: Number(fields.capacity)
      }, Number(form.dataset.revision));
      await operations();
      notify("Disponibilité mise à jour.");
      return;
    }
    let path;
    let payload = fields;
    if (form.classList.contains("lab")) {
      path = `orders/${form.dataset.id}/result`;
      payload = {...fields, version: Number(form.dataset.version)};
    } else if (form.classList.contains("cancel")) {
      path = `orders/${form.dataset.id}/cancel`;
    } else if (form.id === "outcome") {
      path = "verified-outcome";
    } else if (form.id === "observations") {
      path = "observations";
      payload = {values: fields};
    } else if (form.id === "decision") {
      path = "decision";
    } else if (form.id === "share") {
      path = "grants";
    } else if (form.id === "consent") {
      path = "statistics-consent";
      payload = {include: fields.include === "yes"};
    } else {
      return;
    }
    active = await api(`/episodes/${active.id}/${path}`, "POST", payload, active.revision);
    renderEpisode();
    notify("Mise à jour enregistrée.");
  } catch (error) {
    errorHandler(error);
    if (active && view === "episode" && [409, 412].includes(error.status)) {
      active = await api(`/episodes/${active.id}`).catch(() => active);
      renderEpisode();
    }
  } finally {
    writing = false;
    button.disabled = false;
  }
});

setInterval(async () => {
  if (view !== "episode" || !active || writing || polling || screen.contains(document.activeElement)) return;
  const {id, revision, choices} = active;
  polling = true;
  try {
    const next = await api(`/episodes/${id}`);
    if (active?.id !== id || active.revision !== revision || view !== "episode" || writing ||
        screen.contains(document.activeElement)) return;
    if (next.revision !== revision || JSON.stringify(next.choices) !== JSON.stringify(choices)) {
      active = next;
      renderEpisode();
      notify("La fiche a été actualisée.");
    }
  } catch (error) {
    errorHandler(error);
  } finally {
    polling = false;
  }
}, 2500);

init().catch(errorHandler);
