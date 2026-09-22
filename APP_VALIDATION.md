# Validation applicative de la livraison

Date : 2026-09-22

Cette page complète `VALIDATION.md`, lequel contrôle la cohérence de la spécification. Elle décrit uniquement les preuves logicielles exécutées sur l'implémentation de référence et **ne constitue aucune validation clinique**.

## Résultats exécutés

| Contrôle | Résultat |
| --- | --- |
| `PYTHONPATH="$PWD/backend:$PWD" pytest -q` | PASS — 18 tests |
| `python tools/build_contracts.py` | PASS — 107 schémas, 80 opérations, 12 exemples |
| `python tools/validate_reference.py` | PASS — 204 contrôles, 0 échec |
| comparaison routes runtime ↔ contrat | PASS — 80/80 présentes, 0 manquante, 0 supplémentaire sous `/api/v1` |
| `python -m compileall` sur backend/tests/scripts | PASS |
| `node --check frontend/app.js` | PASS |
| migration Alembic `upgrade head` sur base jetable | PASS |
| métadonnées de paquet installables hors-ligne (`--no-build-isolation --no-deps`) | PASS |

## Couverture logicielle ciblée

La suite vérifie notamment : vertical slice hors-ligne synthétique, idempotence, conflits de version source, score distinct d'une probabilité, corrections conservant l'historique, isolation inter-tenant, séparation mode payant/permission d'ordre, précondition `If-Match`, coût nul explicite, concurrence de réservation, coût conditionnel, suivi après résultat tardif, allergie inconnue sans ordonnance, contribution sans activation automatique, workflow sur révision périmée et budget fournisseur borné.

## Environnement non exercé ici

Le moteur Docker n’était pas disponible dans l’environnement de finalisation ; le démarrage Compose et la migration contre un serveur PostgreSQL réel n’ont donc pas été exécutés ici. Le schéma Alembic a été exécuté avec succès contre une base jetable, tandis que les tests applicatifs utilisent leur harnais SQLite.

## Ce que ces résultats ne prouvent pas

Ils ne prouvent ni sécurité clinique, ni performance à l'échelle, ni interopérabilité avec un partenaire réel, ni qualification FHIR/Kristal native, ni justesse d'un corpus médical. Ces validations nécessitent les profils externes, données, environnements et procédures de qualification correspondants.
