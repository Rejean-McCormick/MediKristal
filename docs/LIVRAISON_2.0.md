# Livraison MediKristal 2.0

## Démarrer sur Windows

Extraire le dossier `MediKristal/` dans le dossier parent qui contient `MediKristal-Donnees`. Le chemin de l’index peut aussi être fourni explicitement. Avec PowerShell 7 et Docker Desktop démarré, exécuter depuis le dépôt.

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\Start-MediKristal.ps1
```

Le lanceur ouvre `http://127.0.0.1:8001/episodes`. Il utilise un projet Docker dédié `medikristal-v2`. L’atelier local est accessible sans jeton et conserve ses données dans son volume PostgreSQL. La version précédente peut continuer à utiliser son projet et son port. Pour imposer un autre port ou un index, passer `-Port 8010 -PublicIndex C:\chemin\index.sqlite3`. Le service reste joignable sur l’adresse de boucle locale. Le premier build peut télécharger les images et dépendances.

Le téléchargeur et l’importateur se lancent depuis la racine du dépôt avec `Telecharger-bases-medicales.bat` et `Importer-bases-medicales.bat`. Les données et la provenance sont conservées dans le dossier frère. Une interruption du téléchargement public BDPP peut déclencher une nouvelle tentative avec curl. L’importateur vérifie les artefacts avant de créer l’index de recherche. Si plusieurs index existent, préciser lequel monter. Le service les lit en lecture seule.

## Parcours de démonstration

1. Ouvrir un épisode et renseigner les observations sur sa fiche. Le scénario propose une question si les informations sont insuffisantes, une orientation urgente quand le signal synthétique est coché, ou une comparaison d’examens.
2. Choisir une option faisable et transmettre la demande au laboratoire simulé. Le moteur compare l’examen direct et le parcours conditionnel selon le délai de rendu, le coût attendu et la capacité courante.
3. Déplier **Laboratoire simulé** et transmettre un résultat. La fiche se réévalue automatiquement. Un résultat positif ou indéterminé du test rapide ouvre une comparaison de confirmation. Les résultats corrigés gardent leur historique et rouvrent une décision si nécessaire.
4. Examiner, signer et clôturer dans la même fiche. Le compte rendu est imprimable. Le consentement à la contribution est une action séparée. Les statistiques de la simulation se consultent dans l’espace correspondant.

## Frontières logicielles

| Domaine | Fonction livrée |
| --- | --- |
| Épisode | État durable, observations et auteurs, historique par révision, transfert de lecture par droit explicite et distinction entre recueil, commande, laboratoire, décision et revue. |
| Hospital Ops | Une procédure de démonstration versionnée, appliquée dans le parcours et épinglée à l’épisode. Sa fiche expose étapes et provenance. Les configurations et corpus de vrais sites demandent leur propre contrat. |
| Ressources | Capacité simulée, coût et délai courants. Transaction et contrainte de base préservent la dernière place même si deux demandes arrivent ensemble. |
| Laboratoire | Demande acceptée et résultat simulés. Identifiant, version, déduplication, correction, annulation et recalcul transactionnel. L’atelier n’émet aucun ordre réel. |
| Statistiques | Prévision synthétique figée avant résultat. Issue vérifiée par un rôle distinct. Seuls les épisodes clôturés dont le créateur a accepté la contribution sont projetés vers la table analytique minimale. Un retrait supprime la projection. Les métriques restent des résultats d’ingénierie. |
| Référentiels | Consultation publique locale en lecture seule, sans injection des libellés ou associations dans le modèle diagnostique. |

## API et persistance

La v2 s’exécute à côté de l’[API v1](../contracts/README.md). Son schéma OpenAPI est servi par `/api/v2/openapi.json`. Une clé d’idempotence accompagne chaque écriture et `If-Match` identifie la révision attendue. Le mode normal exige un Bearer avec droit d’action et accès à l’épisode. Les capacités sont `episode:read`, `collect`, `order`, `lab`, `sign`, `share`, `resources`, `statistics`, `verify` et `export`, toutes préfixées par `episode:`. Les profils hors atelier doivent attribuer les droits aux acteurs réels. La projection confidentielle sous `/api/v2/episodes/{id}/projection` expose le profil MediKristal 1 et la recette candidate `dossier-medical`. Elle porte une empreinte et exige le droit d’export. La migration `0003_episode_analysis` ajoute la table analytique et réutilise le journal, les révisions et les claims existants.

Le modèle, les seuils, les délais et les décisions de la démo sont fictifs. La signature est une attribution de la décision dans l’application. Les modèles calibrés sur une population réelle, le paquet Hospital Ops natif qualifié, les ordres vers un laboratoire réel et les adaptateurs Interaction Kernel ou FHIR sont des intégrations à établir et valider avec leurs autorités.

Voir [architecture et backlog](SYSTEME_FINAL.md), [preuves historiques](ETAT_2026-11-27.md) et [profil de qualification](PROFIL_QUALIFICATION.md).

## Vérifications de cette livraison

- Suite applicative complète sur SQLite avec Python 3.12. 84 tests réussis.
- PostgreSQL 16.2. Descente et remontée Alembic de la base jetable, puis six tests du parcours. Le dernier créneau ne peut être réclamé deux fois.
- Playwright et Chromium. Deux fenêtres, dix captures après action et aucune erreur JavaScript observée. La seconde fenêtre transmet le résultat et la première se met à jour sans action de recalcul. La recherche de référentiels a utilisé un index synthétique conforme au schéma de l’importateur.
- La validation documentaire de référence couvre 208 contrôles. Le lanceur Windows et le déploiement Docker Desktop restent à vérifier sur le poste cible.
