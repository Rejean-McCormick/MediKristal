# Démarrage d’une intervention de codage

Le dossier `docs/` décrit l’évolution du dépôt MediKristal 0.2.0. Commencer par **MK-SF-01** du [backlog](BACKLOG_SYSTEME_FINAL.md). Le premier objectif est de reproduire le socle d’ingénierie sur un checkout complet, puis de livrer le parcours synthétique du cas.

## Sources de décision

1. Lire l’[AGENTS.md du dépôt](../AGENTS.md) et les consignes locales applicables.
2. Identifier la révision, lire [l’état de la capture](ETAT_2026-11-27.md) et vérifier les écarts avec le checkout.
3. Pour le comportement en place, lire le code, les tests et les [contrats livrés](../contracts/README.md). Un écart runtime/contrat appelle une correction tracée.
4. Pour le comportement à construire, lire le ticket, le [système final](SYSTEME_FINAL.md), les [décisions](20-decisions.md) et le chapitre propriétaire. Relier ticket, exigences, opérations et scénarios via la [matrice](../contracts/traceability.json).
5. Pour une frontière externe, travailler avec les fichiers de contrat effectivement épinglés. Le statut reste indisponible tant que la capacité correspondante n’a pas de preuve.

## Où intervenir dans le checkout

| Besoin | Points d’entrée à lire |
| --- | --- |
| API, droits, contrat | `backend/medikristal/app.py`, `api.py`, `security.py`, `contracts.py`, `tools/build_contracts.py`, `tools/contract_extensions.py` |
| Cas, transactions et historique | `backend/medikristal/store.py`, `db.py`, `backend/alembic/versions/` |
| Réservations, messages et reprise | `api.py` pour les opérations de booking, `adapters.py`, `worker.py`, `db.py` pour claims, inbox et outbox |
| Données synthétiques et calcul | `synthetic.py`, `planning.py`, `examples/`, `tests/test_core_acceptance.py` |
| Sources et export | `importers.py`, `scripts/import_local_catalog.py`, port de publication et route `/api/v1/knowledge/exports` |
| Interface | `frontend/index.html`, `app.js`, `styles.css`. Les actifs embarqués se synchronisent via `tools/sync_runtime_assets.py`. |
| Déploiement et preuves | `backend/pyproject.toml`, `backend/requirements.lock`, `deploy/docker-compose.yml`, `.github/workflows/ci.yml`, `tools/check_delivery_integrity.py` |

Les noms courts dans le tableau désignent les modules de `backend/medikristal/` ou les fichiers du dossier cité dans la même ligne.

## Boucle de travail par ticket

- Vérifier les chemins, états et permissions sur le code actuel. Définir le comportement à couvrir et les cas de refus avant de modifier le contrat.
- Réutiliser les mécanismes de révision, d’idempotence et d’autorisation. Modifier ensemble générateur, schémas, exemples et matrice si le contrat change. Conserver les lecteurs de données antérieures ou prévoir une migration.
- Prouver le changement avec une fixture synthétique et les tests pertinents. Couvrir les courses, refus et reprises quand ils concernent le ticket. Un partenaire synthétique produit des reçus marqués comme tels.
- Régénérer les actifs et le manifeste selon le processus du checkout. Enregistrer commandes exécutées, versions, résultats et limites. Les tests documentaires, applicatifs et de qualification clinique ont des portées distinctes.

## Commandes de base

Depuis la racine d’un checkout complet, dans un environnement Python 3.12 isolé préparé avec les dépendances verrouillées et pytest :

```sh
python tools/check_delivery_integrity.py
PYTHONPATH=backend:. python -m pytest -q
node --check frontend/app.js
```

Le validateur documentaire écrit `VALIDATION.md` et `validation-report.json`. Pour un contrôle sans altérer les preuves de départ, l’exécuter dans une copie de travail. Pour une livraison volontaire, régénérer le manifeste après les actifs et rapports. Les procédures PostgreSQL, Docker et déconnexion WAN sont dans le [profil de qualification](PROFIL_QUALIFICATION.md).

## Compte rendu attendu

Pour chaque ticket, fournir les exigences et fichiers touchés, les décisions, la méthode de migration ou l’absence de changement de schéma, les tests exécutés et leur environnement, les résultats et les vérifications restantes. Le projet avance avec des profils synthétiques. Les paramètres cliniques, droits de redistribution, contrats de partenaires et habilitations de site exigent les preuves du propriétaire compétent.
