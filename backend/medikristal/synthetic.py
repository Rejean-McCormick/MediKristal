from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .util import artifact_ref, digest, now_iso

SYN = "urn:medikristal:synthetic"
MODEL = artifact_ref("synthetic-binary", "0.1.0")
SCORE_MODEL = artifact_ref("synthetic-score", "0.1.0")
PROTOCOL = artifact_ref("synthetic-protocol", "0.1.0")
POLICY = artifact_ref("synthetic-pareto", "0.1.0")
AUTH_POLICY = artifact_ref("engineering-only", "0.1.0")
RIGHTS = artifact_ref("synthetic-rights", "0.1.0")
CONSTRAINTS = artifact_ref("synthetic-constraints", "0.1.0")
SYN_RELEASE = artifact_ref("synthetic-release", "0.1.0")


def concept(code: str) -> dict:
    return {"system": SYN, "code": code, "version": "1"}


def _test_value(observations: list[dict]) -> bool | None:
    candidates = [o for o in observations if o.get("concept") == concept("SYN-T1") and o.get("status") != "entered_in_error" and o.get("quality") == "usable"]
    for obs in reversed(candidates):
        if obs.get("presence") in {"unknown", "not_assessed"}:
            return None
        value = obs.get("value")
        if obs.get("presence") == "absent":
            return False
        if isinstance(value, dict) and value.get("kind") == "boolean":
            return bool(value.get("value"))
    return None


def evaluate(case: dict, observations: list[dict], request: dict) -> dict:
    model_refs = request.get("model_refs", [])
    requested_model = next((m for m in model_refs if m.get("id") == MODEL["id"]), None)
    requested_score = next((m for m in model_refs if m.get("id") == SCORE_MODEL["id"]), None)
    base = {
        "case_id": case["id"],
        "case_revision": case["revision"],
        "knowledge_release": request["knowledge_release"],
        "evaluation_time": request["evaluation_time"],
        "intended_use": request["intended_use"],
        "stale": False,
        "synthetic": True,
        "limitations": ["Fixture d'ingénierie synthétique; aucune validation clinique."],
        "trace": [],
        "engine_version": "synthetic-oracle/1",
    }
    if request["intended_use"] != "engineering" or not case.get("synthetic", False):
        base.update({"status": "out_of_scope", "hypotheses": [], "missing_inputs": [], "limitations": base["limitations"] + ["Le modèle synthétique est interdit hors engineering."]})
    elif requested_model is None and requested_score is None:
        base.update({"status": "out_of_scope", "hypotheses": [], "missing_inputs": [], "limitations": base["limitations"] + ["Aucun modèle synthétique applicable demandé."]})
    elif requested_model is None and requested_score is not None:
        base.update({
            "status": "complete",
            "hypotheses": [{
                "concept": concept("SYN-D1"), "kind": "score", "probability": None, "score": 0.73,
                "qualitative": None, "interval": None, "target_event": "Similarité fictive SYN-D1",
                "horizon": "instant synthétique", "model_ref": SCORE_MODEL, "scope_status": "applicable",
                "calibration_ref": None, "evidence_refs": [], "reason_codes": ["not_estimable", "synthetic_only"],
            }],
            "missing_inputs": [],
            "trace": [{"node_id": "n-score", "kind": "model", "reference": "synthetic-score@0.1.0", "parent_ids": [], "summary": "Score de similarité fictif; ce score n'est pas une probabilité."}],
        })
    else:
        observed = _test_value(observations)
        if observed is None:
            base.update({
                "status": "insufficient_data",
                "hypotheses": [],
                "missing_inputs": [{"concept": concept("SYN-T1"), "reason": "required_by_model", "required_by": MODEL["id"]}],
                "trace": [{"node_id": "n-model", "kind": "model", "reference": "synthetic-binary@0.1.0", "parent_ids": [], "summary": "Entrée SYN-T1 manquante ou inconnue."}],
            })
        else:
            prior = 0.10
            sensitivity = 0.80
            specificity = 0.90
            if observed:
                posterior = sensitivity * prior / (sensitivity * prior + (1 - specificity) * (1 - prior))
                summary = "Oracle synthétique: test positif."
            else:
                posterior = (1 - sensitivity) * prior / ((1 - sensitivity) * prior + specificity * (1 - prior))
                summary = "Oracle synthétique: test négatif."
            source_obs = next((o for o in reversed(observations) if o.get("concept") == concept("SYN-T1")), None)
            base.update({
                "status": "complete",
                "hypotheses": [{
                    "concept": concept("SYN-D1"), "kind": "probability", "probability": posterior,
                    "score": None, "qualitative": None, "interval": None,
                    "target_event": "Maladie fictive SYN-D1 présente", "horizon": "instant synthétique",
                    "model_ref": MODEL, "scope_status": "applicable", "calibration_ref": None,
                    "evidence_refs": [], "reason_codes": ["synthetic_only"],
                }],
                "missing_inputs": [],
                "trace": [
                    {"node_id": "n1", "kind": "observation", "reference": source_obs["id"] if source_obs else "unknown", "parent_ids": [], "summary": summary},
                    {"node_id": "n2", "kind": "model", "reference": "synthetic-binary@0.1.0", "parent_ids": ["n1"], "summary": "Prior 0.10; sensibilité 0.80; spécificité 0.90; valeurs fictives."},
                ],
            })
    base["replay_digest"] = digest({
        "case": {"id": case["id"], "revision": case["revision"], "synthetic": case.get("synthetic")},
        "observations": [{k: o.get(k) for k in ("concept", "presence", "value", "effective_at", "status", "quality")} for o in observations],
        "request": request,
        "engine": base["engine_version"],
        "constants": {"prior": 0.10, "sensitivity": 0.80, "specificity": 0.90},
    })
    return base


def proposals_for(evaluation: dict) -> list[dict]:
    common = {"case_id": evaluation["case_id"], "case_revision": evaluation["case_revision"], "evaluation_id": evaluation["id"], "protocol_ref": PROTOCOL, "preconditions": [], "evidence_refs": [], "status": "proposed"}
    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    return [
        {**common, "kind": "ask", "target": concept("SYN-Q1"), "reason_codes": ["synthetic_information_gain"], "expires_at": expires},
        {**common, "kind": "observe", "target": concept("SYN-OBS1"), "reason_codes": ["synthetic_monitoring"], "expires_at": expires},
        {**common, "kind": "test", "target": concept("SYN-T1"), "reason_codes": ["synthetic_test_option"], "expires_at": expires},
    ]


def models() -> list[dict]:
    scope = {"population_id": "synthetic-only", "setting": "engineering", "jurisdiction": "TEST", "language": "fr", "valid_from": "2026-01-01T00:00:00Z", "valid_until": None}
    common={"scope": scope, "hypothesis_space": "multi_label", "evidence_refs": [], "qualification_refs": [], "missingness_policy": "abstain", "abstention_policy_ref": artifact_ref("synthetic-abstention"), "intended_use": "engineering"}
    return [
        {**MODEL, **common, "type": "synthetic", "input_concepts": [concept("SYN-T1")], "parameter_ref": artifact_ref("synthetic-binary-params"), "engine_version": "synthetic-oracle/1"},
        {**SCORE_MODEL, **common, "type": "synthetic", "input_concepts": [], "parameter_ref": artifact_ref("synthetic-score-params"), "engine_version": "synthetic-score/1"},
    ]


def protocols() -> list[dict]:
    scope = {"population_id": "synthetic-only", "setting": "engineering", "jurisdiction": "TEST", "language": "fr", "valid_from": "2026-01-01T00:00:00Z", "valid_until": None}
    return [{
        **PROTOCOL, "scope": scope, "entry_step_id": "evaluate", "steps": [
            {"step_id": "evaluate", "kind": "evaluate", "condition": None, "action_target": None, "transitions": [{"when": "true", "target_step_id": "propose"}], "max_visits": 1},
            {"step_id": "propose", "kind": "propose_action", "condition": None, "action_target": concept("SYN-T1"), "transitions": [{"when": "true", "target_step_id": "end"}], "max_visits": 1},
            {"step_id": "end", "kind": "terminate", "condition": None, "action_target": None, "transitions": [], "max_visits": 1},
        ], "library_refs": [], "model_refs": [MODEL], "source_refs": [], "intended_use": "engineering", "qualification_refs": [],
    }]


def assertions() -> list[dict]:
    scope = {"population_id": "synthetic-only", "setting": "engineering", "jurisdiction": "TEST", "language": "fr", "valid_from": "2026-01-01T00:00:00Z", "valid_until": None}
    return [
        {
            "id": "synthetic-assertion-t1-d1", "subject": concept("SYN-T1"), "predicate": "synthetic_supports",
            "object": concept("SYN-D1"), "scope": scope,
            "source_refs": [{"source_id": "synthetic-fixture", "source_version": "1", "record_id": "assertion-1"}],
            "status": "reviewed", "certainty": "not_applicable", "evidence_refs": [artifact_ref("synthetic-evidence-t1")],
        },
        {
            # Mapping relation fixture for AT-005: a broader relation is deliberately not
            # interchangeable with an exact-equivalence query.
            "id": "synthetic-mapping-broader-t1", "subject": concept("SYN-T1-BROAD"), "predicate": "broader_than",
            "object": concept("SYN-T1"), "scope": scope,
            "source_refs": [{"source_id": "synthetic-fixture", "source_version": "1", "record_id": "mapping-broader-1"}],
            "status": "reviewed", "certainty": "not_applicable", "evidence_refs": [],
        },
    ]


def evidence() -> list[dict]:
    source = [{"source_id": "synthetic-fixture", "source_version": "1", "record_id": "binary-parameters"}]
    return [
        {"id": "synthetic-evidence-prevalence", "measure": "prevalence", "value": 0.10, "population_ref": "synthetic-only", "setting": "engineering", "target": concept("SYN-D1"), "test": None, "threshold_description": None, "sample_size": None, "interval_description": None, "source_refs": source, "limitations": ["Valeur fictive réservée aux tests d'ingénierie."], "review_status": "reviewed"},
        {"id": "synthetic-evidence-sensitivity", "measure": "sensitivity", "value": 0.80, "population_ref": "synthetic-only", "setting": "engineering", "target": concept("SYN-D1"), "test": concept("SYN-T1"), "threshold_description": "Résultat booléen synthétique.", "sample_size": None, "interval_description": None, "source_refs": source, "limitations": ["Valeur fictive réservée aux tests d'ingénierie."], "review_status": "reviewed"},
        {"id": "synthetic-evidence-specificity", "measure": "specificity", "value": 0.90, "population_ref": "synthetic-only", "setting": "engineering", "target": concept("SYN-D1"), "test": concept("SYN-T1"), "threshold_description": "Résultat booléen synthétique.", "sample_size": None, "interval_description": None, "source_refs": source, "limitations": ["Valeur fictive réservée aux tests d'ingénierie."], "review_status": "reviewed"},
    ]


def optimization_policies() -> list[dict]:
    scope = {"population_id": "synthetic-only", "setting": "engineering", "jurisdiction": "TEST", "language": "fr", "valid_from": "2026-01-01T00:00:00Z", "valid_until": None}
    return [{**POLICY, "scope": scope, "method": "pareto", "utility_model_ref": None, "constraint_set_ref": CONSTRAINTS, "objective_refs": [], "tie_break": "eligible_at_then_id", "qualification_refs": []}]


def treatment_option(case: dict, allergy_known: bool) -> dict:
    check_status = "pass" if allergy_known else "unknown"
    status = "proposed" if allergy_known else "needs_information"
    return {
        "case_id": case["id"], "case_revision": case["revision"], "target": concept("SYN-DRUG"), "protocol_ref": PROTOCOL,
        "goal": "Option fictive pour tester le contrôle de sécurité.",
        "checks": [{"name": "synthetic_allergy_check", "status": check_status, "reason": "Fixture engineering uniquement.", "evidence_refs": []}],
        "status": status, "evidence_refs": [], "limitations": ["Aucune dose, prescription ou administration n'est générée."],
    }
