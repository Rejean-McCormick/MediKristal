# Validation applicative de la livraison

Date : 2026-09-22

Cette page complète `VALIDATION.md`, lequel contrôle la cohérence de la spécification. Elle décrit uniquement les preuves logicielles exécutées sur l'implémentation de référence et **ne constitue aucune validation clinique**.

## Résultats exécutés

| Contrôle | Résultat |
| --- | --- |
| `PYTHONPATH=backend pytest -q` | PASS — 73 tests |
| `PYTHONPATH=backend pytest --cov=medikristal --cov-report=term -q` | PASS — 73 tests, couverture globale 91 % (API 86 %) |
| `python tools/build_contracts.py` | PASS — 107 schémas, 80 opérations, 12 exemples |
| `python tools/validate_reference.py` | PASS — 211 contrôles, 0 échec |
| comparaison routes runtime ↔ contrat | PASS — 80/80 présentes, 0 manquante, 0 supplémentaire sous `/api/v1` |
| `/openapi.json` ↔ `contracts/openapi.json` | PASS — égalité exacte testée |
| erreurs domaine `application/problem+json` + corrélation | PASS |
| `python -m compileall` sur backend/tests/scripts/tools | PASS lors de la finalisation |
| `node --check frontend/app.js` | PASS |
| Alembic sur base SQLite jetable : `upgrade head → downgrade base → upgrade head` | PASS |
| schéma obtenu par migration ↔ tables/colonnes ORM | PASS |
| `PIP_NO_INDEX=1 python -m pip wheel ./backend --no-deps --no-build-isolation` | PASS — wheel `medikristal-0.2.0` |
| installation du wheel hors arborescence source (`pip --target`) + smoke `/healthz`, `/openapi.json`, `/` | PASS |
| parsing YAML de `deploy/docker-compose.yml` | PASS — 4 services (`db`, `migrate`, `api`, `worker`) |
| `python tools/build_sbom.py` | PASS — CycloneDX, 8 composants |

## Couverture logicielle ciblée

La suite vérifie notamment : vertical slice synthétique hors-ligne, idempotence, conflits de versions, score distinct d'une probabilité, replay déterministe, corrections avec historique append-only, isolation inter-tenant et grants par cas, permissions indépendantes du mode payant, préconditions `If-Match`, coûts inconnus vs zéro et séparation des perspectives, disponibilité et claims de capacité, annulation libérant une capacité, réservations distantes ambiguës en `reconciling`, suivi durable, workflow versionné, options thérapeutiques synthétiques, plans de soins, import CSV en quarantaine/reprise, releases publication/activation/révocation, filtrage des artefacts par release, outbox/inbox dédupliquée, budgets fournisseur/tenant et retrait de ressource avec analyse d'impact.

Les adaptateurs externes non configurés sont testés pour retourner `capability_unavailable` ou `not_configured`, jamais un succès fictif. Les exports Kristal/FHIR ne sont donc pas qualifiés comme réussis dans cette distribution.

## Environnement non exercé ici

Aucun moteur Docker ni serveur PostgreSQL n'était disponible dans l'environnement de finalisation. Le démarrage Compose et une migration contre PostgreSQL réel n'ont donc pas été exécutés ici. Le schéma Alembic a été rejoué sur une base SQLite jetable et comparé au modèle ORM ; les mécanismes de verrouillage `FOR UPDATE` et la concurrence réelle multi-processus devront être revalidés sur PostgreSQL dans l'environnement de déploiement. La vérification `build_sbom.py --verify-installed` n'est pas qualifiée dans cet environnement, car `psycopg==3.3.6` n'y est pas installé ; le SBOM est néanmoins généré depuis le verrou de dépendances.

## Ce que ces résultats ne prouvent pas

Ils ne prouvent ni sécurité clinique, ni performance à l'échelle, ni interopérabilité avec un partenaire réel, ni qualification FHIR/Kristal native, ni justesse d'un corpus médical. Ces validations nécessitent les profils externes, données, environnements et procédures de qualification correspondants. La couverture de code n'est pas un indicateur de validité clinique.
