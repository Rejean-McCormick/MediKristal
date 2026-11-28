# Importer les référentiels publics

Depuis la racine du dépôt sous Windows, lancer `Importer-bases-medicales.bat`. Le lanceur utilise Python 3.12 ou plus récent avec le module SQLite et FTS5. En ligne de commande, utiliser `python scripts/import_medical_sources.py build`.

Le script lit le dossier frère `MediKristal-Donnees`. Il vérifie les 11 fichiers avec leurs reçus et construit un index SQLite dans `MediKristal-Donnees/index-public/`. Pour utiliser un autre dossier, placer `--data CHEMIN` devant `build`. Prévoir plusieurs Go de marge pour SQLite et les fichiers temporaires. Le chemin complet de l’index est affiché à la fin.

## Consulter l’index

```powershell
.\Importer-bases-medicales.bat search "CHEMIN_VERS_INDEX.sqlite3" "nortriptyline"
.\Importer-bases-medicales.bat search "CHEMIN_VERS_INDEX.sqlite3" "HP:0001250"
```

Chaque résultat indique source, type, code, libellé, fichier et SHA-256. L’index conserve les champs d’origine des tables sélectionnées et les reçus dans `source_file`. La BDPP indexe les produits, ingrédients et historiques de statut. HPO conserve termes, annotations et qualificatifs. La CIM-11 indexe les classeurs MMS français et anglais. Orphadata conserve la fiche de maladie avec ses associations dans le XML. RxNorm conserve les tables RRF de noms, relations et attributs. Les membres non sélectionnés restent disponibles dans les archives originales.

L’index est un catalogue de lecture local. Il n’est pas relié aux résultats cliniques, au serveur PostgreSQL ou à l’interface Web de MediKristal. La promotion d’un corpus et le mapping entre référentiels restent soumis aux décisions du [chapitre 27](27-connectors.md).

Un fichier absent, une empreinte différente, une version locale ambiguë ou un format non reconnu interrompt la construction. Les archives source sont lues sans extraction sur disque. Les imports réussis sont conservés par ensemble d’empreintes. Pour utiliser un autre ensemble lorsque deux copies sont installées, créer un dossier distinct avec une seule copie choisie par fichier et utiliser `--data`.
