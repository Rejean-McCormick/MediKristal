"""Versioned engineering fixture for the episode engine.

The virtual syndrome and every number are fictional. Nothing from a public
terminology index enters this model.
"""
from __future__ import annotations

from .planning import BranchCost, expected_cost
from .util import digest

OBSERVATIONS = {
    "discomfort": "Inconfort",
    "itch": "Démangeaisons",
    "alarm": "Signal d’urgence de la simulation",
}
TESTS = {
    "screen": "Test rapide",
    "confirm": "Examen de confirmation",
    "direct": "Examen direct",
}
RESULTS = {
    "positive": "Positif",
    "negative": "Négatif",
    "indeterminate": "Indéterminé",
    "unusable": "Échantillon inexploitable",
    "not_performed": "Non effectué",
}
DEMO_PACKAGE = {
    "namespace": "urn:medikristal:synthetic",
    "procedure": {"id": "hospital-ops-demo", "version": "1", "deadline_minutes": 60,
                  "source": "Procédure Hospital Ops de démonstration",
                  "coverage": "Épisodes fictifs de l’atelier",
                  "steps": [
                      {"id": "collect", "role": "collect", "next": ["urgent", "investigate", "review"]},
                      {"id": "urgent", "role": "sign", "next": ["closed"]},
                      {"id": "investigate", "role": "order", "next": ["waiting", "closed"]},
                      {"id": "waiting", "role": "lab", "next": ["investigate", "review"]},
                      {"id": "review", "role": "sign", "next": ["closed"]},
                      {"id": "closed", "role": "lab", "next": ["review"]},
                  ]},
    "model": {"id": "synthetic-episode-model", "version": "1", "population": "Épisodes fictifs",
              "source": "Table de simulation v1",
              "synthetic_estimates": {"one_symptom": 20, "two_symptoms": 40},
              "measurement": "Fréquence de l’issue fictive A dans les groupes virtuels",
              "denominator": "100 observations fictives pour chaque groupe de symptômes",
              "uncertainty": "Valeurs de fixture définies pour la simulation",
              "branch_weights": {"positive": 20, "negative": 70, "indeterminate": 5,
                                 "unusable": 5, "not_performed": 0}},
}
DEMO_PACKAGE_REF = digest(DEMO_PACKAGE)
DEFAULT_RESOURCES = {
    "screen": {"minutes": 10, "cost_minor": 1500, "capacity": 2},
    "confirm": {"minutes": 40, "cost_minor": 18000, "capacity": 1},
    "direct": {"minutes": 35, "cost_minor": 18000, "capacity": 1},
}


def assessment(observations: dict, results: dict, package: dict = DEMO_PACKAGE) -> dict:
    if observations.get("alarm") == "present":
        return {"phase": "urgent", "next": "Passer à la prise en charge du scénario urgent.",
                "reason": "Le signal d’urgence du protocole de démonstration est présent.",
                "hypothesis": None, "review_kind": "urgent"}
    for code in OBSERVATIONS:
        if observations.get(code) not in {"present", "absent"}:
            return {"phase": "collect", "next": f"Préciser « {OBSERVATIONS[code]} »",
                    "reason": "Cette information complète le scénario avant toute demande.",
                    "observation": code, "hypothesis": None}
    if observations["discomfort"] == "absent" and observations["itch"] == "absent":
        return {"phase": "review", "next": "Confirmer la fin du scénario.",
                "reason": "Aucun des deux symptômes du parcours fictif n’est présent.",
                "hypothesis": None, "review_kind": "no_indication"}
    for test in ("confirm", "direct"):
        if test in results:
            result = results[test]
            if result in {"positive", "negative"}:
                return {"phase": "review", "next": "Examiner la décision et la signer.",
                        "reason": f"{TESTS[test]} : {RESULTS[result].lower()}.",
                        "hypothesis": "Syndrome fictif A" if result == "positive" else "Syndrome fictif A écarté",
                        "review_kind": "confirmed" if result == "positive" else "excluded"}
            return {"phase": "review", "next": "Réexaminer le résultat avec l’équipe.",
                    "reason": f"{TESTS[test]} : {RESULTS[result].lower()}.",
                    "hypothesis": "Syndrome fictif A à vérifier", "review_kind": "unresolved"}
    if results.get("screen") == "negative":
        return {"phase": "review", "next": "Examiner la décision et la signer.",
                "reason": "Le test rapide fictif est négatif selon les règles du scénario.",
                "hypothesis": "Syndrome fictif A écarté", "review_kind": "excluded"}
    probability = None
    if not results:
        table = package["model"]["synthetic_estimates"]
        group = "two_symptoms" if observations["discomfort"] == observations["itch"] == "present" else "one_symptom"
        probability = {"value_percent": table[group], "source": package["model"]["source"],
                       "population": package["model"]["population"], "denominator": package["model"]["denominator"]}
    return {"phase": "investigate", "next": "Choisir le prochain examen.",
            "reason": "Les observations permettent de comparer les examens du scénario.",
            "hypothesis": "Syndrome fictif A à vérifier", "estimate": probability}


def plans(state: dict, results: dict, resources: dict, remaining: float, package: dict) -> list[dict]:
    if state["phase"] != "investigate":
        return []

    def option(test: str, confirmation: bool) -> dict:
        steps = [resources[test]]
        if confirmation:
            steps.append(resources["confirm"])
        costs = [step["cost_minor"] for step in steps]
        delays = [step["minutes"] for step in steps]
        reason = None
        minutes = None if None in delays else sum(delays)
        expected = None
        if None not in costs:
            followups = []
            if confirmation:
                weights = package["model"]["branch_weights"]
                total = sum(weights.values())
                followups = [BranchCost(weight / total, costs[1])
                             for outcome, weight in weights.items() if outcome != "negative"]
            expected = round(expected_cost(costs[0], followups), 2)
        if any(step["available"] <= 0 for step in steps):
            reason = "Capacité insuffisante pour ce parcours."
        elif minutes is None:
            reason = "Délai de rendu inconnu."
        elif minutes > remaining:
            reason = "Le résultat dépasserait le délai du parcours."
        return {"test": test, "label": TESTS[test], "conditional": confirmation,
                "minutes": minutes, "expected_cost_minor": expected,
                "available": reason is None, "reason": reason}

    # A screening result remains relevant until replaced by an authorized correction.
    options = [option("confirm", False), option("direct", False)] if "screen" in results else [
        option("screen", True), option("direct", False),
    ]
    return sorted(options, key=lambda item: (
        not item["available"], item["expected_cost_minor"] is None,
        item["expected_cost_minor"] or 0, item["minutes"] is None, item["minutes"] or 0, item["test"],
    ))
