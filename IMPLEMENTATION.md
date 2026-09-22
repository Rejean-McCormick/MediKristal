# Implémentation de référence MediKristal

## Statut

Ce dépôt contient désormais une **implémentation logicielle de référence d'ingénierie** du contrat MediKristal 0.2.0. Elle est conçue pour exécuter les scénarios synthétiques du dépôt et pour servir de socle aux intégrations réelles.

Elle **n'est pas une base clinique validée**, n'est pas un dispositif médical autorisé et ne doit pas être utilisée pour produire des recommandations cliniques réelles. Les calculs fournis utilisent exclusivement l'espace `urn:medikristal:synthetic` et l'`intended_use` `engineering`.

## Ce qui est implémenté

- API FastAPI sous `/api/v1`, avec les **80 couples méthode/route du contrat OpenAPI** montés dans le runtime.
- Contrat OpenAPI livré par `contracts/openapi.json` comme source d'autorité.
- Authentification bearer HMAC, permissions par opération et isolation de tenant.
- Révisions, `ETag`, garde `If-Match`, idempotence persistante et détection des requêtes conflictuelles.
- Cas, observations, corrections, évaluations, propositions, plans et ordres gardés.
- Moteur d'inférence synthétique reproductible et distinction stricte score/probabilité.
- Ressources, coûts, disponibilité, réservations et calcul de coût conditionnel.
- Sources, artefacts, releases, activation/révocation, modèles, protocoles et politiques d'optimisation synthétiques.
- Contributions, workflows, résultats, suivis et plans de soins.
- Budget fournisseur avec réservation/reconciliation et verrouillage transactionnel.
- Outbox transactionnelle et worker.
- PostgreSQL + Alembic pour le déploiement de référence.
- Interface Web légère accessible couvrant les surfaces patient, professionnel, administration, scientifique et exploitation.
- Import local CSV avec prévisualisation/diff/confirmation pour les profils documentés.
- Docker Compose pour PostgreSQL, migrations, API et worker.

## Limites intentionnelles

Les documents source interdisent d'inventer les contrats ou contenus externes absents. En conséquence :

- les profils natifs Kristal/FHIR/partenaires non fournis sont représentés par des ports d'adaptateur et exposent `capability_unavailable` tant qu'un contrat réel n'est pas branché ;
- l'API d'import de source ne simule pas un upload binaire dont le transport n'est pas spécifié ; le traitement local documenté est disponible via `scripts/import_local_catalog.py` ;
- aucune dose, ordonnance, prévalence ou connaissance clinique réelle n'est fabriquée ;
- aucune promotion automatique d'une contribution ou d'une release n'est réalisée ;
- aucune réussite externe n'est simulée lorsqu'un fournisseur n'est pas disponible.

## Démarrage Docker

Depuis la racine :

```sh
cp deploy/.env.example deploy/.env
# Modifier la valeur de MEDIKRISTAL_AUTH_SECRET dans deploy/.env.
cd deploy
docker compose up --build
```

L'interface et l'API sont alors exposées sur `http://localhost:8000`. La documentation développeur FastAPI est disponible sous `/developer/docs`; le schéma retourné reste celui de `contracts/openapi.json`.

## Démarrage local

Avec PostgreSQL disponible :

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.lock
export MEDIKRISTAL_DATABASE_URL='postgresql+psycopg://medikristal:motdepasse@localhost:5432/medikristal'
export MEDIKRISTAL_AUTH_SECRET='une-cle-secrete-de-developpement-longue-de-plus-de-32-caracteres'
cd backend
alembic upgrade head
cd ..
PYTHONPATH=backend uvicorn medikristal.app:app --host 127.0.0.1 --port 8000
```

Créer un jeton de développement explicite :

```sh
MEDIKRISTAL_AUTH_SECRET="$MEDIKRISTAL_AUTH_SECRET" \
PYTHONPATH=backend python -m medikristal.token_cli \
  --tenant 00000000-0000-4000-8000-000000000001 \
  --principal dev \
  --permission '*'
```

Le jeton de test spécial `test-all` n'est accepté que si `MEDIKRISTAL_ALLOW_TEST_TOKEN=1`; il n'est jamais activé par la configuration de production Docker.

## Tests et validation

```sh
make test
make validate
```

Lors de la finalisation de cette livraison :

- tests applicatifs : **18/18 réussis** ;
- contrôles documentaires/contractuels du dépôt : **204/204 réussis** ;
- parité de routage vérifiée : **80/80 opérations contractuelles présentes, 0 route contractuelle manquante**.

Les tests utilisent SQLite uniquement comme harnais isolé et rapide. Le stockage de déploiement de référence reste PostgreSQL.

## Structure ajoutée

| Chemin | Rôle |
| --- | --- |
| `backend/medikristal/` | API, domaine, persistance, auth, moteur synthétique, worker |
| `backend/alembic/` | migrations PostgreSQL |
| `frontend/` | interface Web sans chaîne de build |
| `deploy/` | Docker Compose |
| `scripts/import_local_catalog.py` | import local à deux phases |
| `tests/` | tests d'acceptation logicielle |
| `IMPLEMENTATION.md` | statut, exécution et limites de l'implémentation |
