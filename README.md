# MediKristal

Plateforme autonome de connaissances médicales et d’orchestration du parcours diagnostique : observations, hypothèses, investigations, ressources et options thérapeutiques. Elle expose des contrats utilisables par d’autres logiciels et s’intègre à Kristal et à l’écosystème kOA sans en dépendre pour fonctionner.

**Statut : spécification 1.1 + implémentation logicielle de référence d’ingénierie.** Le contrat d’API et le package de référence portent la version 0.2.0 ; les 80 opérations contractuelles sont montées dans le runtime. La base clinique n’est pas validée : les exemples, modèles et protocoles exécutables fournis ici restent synthétiques et réservés à l’ingénierie.

## Documentation

Consulter [l’index de la documentation](docs/README.md). Chaque sujet possède son propre fichier Markdown ; les liens fonctionnent dans un lecteur de dépôt.

Pour commencer à coder :

1. Lire les [instructions aux agents de développement](AGENTS.md).
2. Lire la [vision et les exigences](docs/01-vision.md), l’[architecture](docs/02-architecture.md) et le [modèle de données](docs/03-data.md).
3. Suivre le [plan de livraison](docs/19-delivery.md) ; lire les chapitres correspondant au module développé.
4. Appliquer les [contrats d’API](docs/13-api.md), les [invariants](docs/24-errors.md) et les [critères de test](docs/18-tests.md).

## Organisation du dépôt

| Chemin | Contenu |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Règles pour l’IA qui implémente le système |
| [docs/README.md](docs/README.md) | Index, parcours de lecture et 33 chapitres de référence |
| [contracts/](contracts/README.md) | Schémas de données et contrat OpenAPI initial |
| [examples/](examples/README.md) | Douze exemples JSON synthétiques |
| tools/ | Génération des contrats et contrôles documentaires |
| backend/ | Monolithe FastAPI, persistance, migrations et worker |
| frontend/ | Interface Web de référence |
| deploy/ | Déploiement Docker Compose |
| tests/ | Tests applicatifs synthétiques |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Exécution, architecture livrée et limites intentionnelles |
| [APP_VALIDATION.md](APP_VALIDATION.md) | Résultats de validation logicielle exécutés |
| [VALIDATION.md](VALIDATION.md) | Portée et résultats des contrôles documentaires |
| [source-snapshots.json](source-snapshots.json) | Provenance des snapshots utilisés |
| [manifest.json](manifest.json) | Empreintes des fichiers de cette livraison |

## Modes de fonctionnement

- **Hors ligne gratuit** : noyau local et contenus disponibles localement.
- **En ligne gratuit** : enrichissement par sources et services gratuits autorisés.
- **En ligne avec fournisseurs payants** : connecteurs facultatifs, budgets et autorisations explicites.

Les fournisseurs payants ne sont jamais requis par le noyau. La connaissance sémantique, les calculs probabilistes et la planification des ressources possèdent des responsabilités séparées ; voir l’[architecture](docs/02-architecture.md).

## Autorité et statut des spécifications

Les instructions explicites les plus récentes de l’utilisateur gouvernent le produit. Pour la cible définie ici : exigences identifiées et ADR > contrats structurés > exemples > illustrations. Les schémas externes restent autoritaires pour leurs formats natifs. Toute contradiction interne doit être résolue explicitement.

Les contrats restent l’autorité de spécification. Le dépôt contient maintenant une implémentation de référence `implemented` pour le socle logiciel synthétique, avec preuves listées dans [APP_VALIDATION.md](APP_VALIDATION.md). Les statuts `qualified_software`, `clinically_validated` et `authorized_for_use` demandent des preuves supplémentaires et ne sont pas revendiqués. La couverture logicielle ne signifie pas que les connaissances médicales nécessaires sont disponibles.

## Exécution de l’implémentation

Le chemin le plus direct est Docker Compose :

```sh
cp deploy/.env.example deploy/.env
# Remplacer le secret applicatif et le mot de passe PostgreSQL dans deploy/.env
cd deploy
docker compose up --build
```

L’API et l’interface sont exposées sur `http://localhost:8000`. Voir [IMPLEMENTATION.md](IMPLEMENTATION.md) pour le démarrage local, la génération d’un jeton, les invariants de sécurité et les limites des intégrations externes.

## Vérification documentaire

Depuis la racine, avec Python :

```sh
python tools/build_contracts.py
python tools/validate_reference.py
```

Ces commandes ne requièrent aucun service médical ni compte fournisseur. Le validateur vérifie les liens locaux, les exemples et le sous-ensemble de schéma utilisé par le générateur. Il ne remplace ni un validateur standard complet, ni la suite de tests applicative, ni une validation clinique. Voir le [rapport](VALIDATION.md).

Le manifeste est régénéré par `make validate` (ou `make manifest`) après les contrôles documentaires et décrit les fichiers source effectivement livrés.

## Révision 1.1

Voir [les changements](CHANGELOG.md), la [couverture fonctionnelle](docs/26-coverage.md) et les [scénarios d’acceptation](docs/33-acceptance.md). Les contrats étendus contiennent 107 définitions et 80 opérations.
