# Télécharger les référentiels médicaux

Le dépôt MediKristal fournit un outil d’acquisition indépendant du serveur. Il télécharge des archives et des fichiers publiés, calcule leur SHA-256 et compare les empreintes disponibles chez l’éditeur. L’acquisition prépare le travail d’import. L’analyse des formats, la revue des droits et l’admission dans un corpus restent des étapes distinctes.

## Emplacement

Dans la disposition de travail Windows, le script résout les chemins à partir du dépôt, quel que soit le répertoire courant.

```text
C:\mycode\Kristal\MediKristal\
  MediKristal\
    Telecharger-bases-medicales.bat
    scripts\download_medical_sources.py
  MediKristal-Donnees\
    dpd\...
    hpo\...
    ...
```

L’outil crée `MediKristal-Donnees` au premier téléchargement. Chaque fichier est conservé sous `source/nom-de-fichier/sha256/` avec un `provenance.json` indiquant l’éditeur de référence, la version ou la mention « courante », la date de récupération, la taille et l’empreinte. Une nouvelle version de contenu conserve l’ancienne copie. Les téléchargements incomplets restent hors de l’arborescence publiée et sont nettoyés en fin de commande. Une relance reprend la source depuis le début et ne duplique pas une copie identique.

## Lancer l’outil

Depuis PowerShell, à la racine du dépôt avec Python 3.12 ou plus récent :

```powershell
.\Telecharger-bases-medicales.bat --list
.\Telecharger-bases-medicales.bat dpd hpo
.\Telecharger-bases-medicales.bat
.\Telecharger-bases-medicales.bat --all
```

Sans argument, la commande télécharge les sources publiques. Indiquer un ou plusieurs identifiants pour choisir les sources. Une source inaccessible est signalée, les autres restent traitées et le code de sortie est 1 si l’un des téléchargements a échoué. `--dest` permet de désigner un autre dossier hors dépôt. Sur les autres systèmes, utiliser `python scripts/download_medical_sources.py` avec les mêmes arguments.

| Identifiant | Contenu | Accès |
| --- | --- | --- |
| `dpd` | Produits pharmaceutiques Santé Canada, quatre archives par statut | [Extraits publics](https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database/what-data-extract-drug-product-database.html) |
| `hpo` | Ontologie OBO et annotations maladie-phénotype, version du 1er septembre 2026 | [Versions HPO](https://github.com/obophenotype/human-phenotype-ontology/releases) |
| `cim-11` | Tableurs MMS 2026-01, français et anglais | [OMS](https://icd.who.int/browse/2026-01/mms/fr) |
| `orphadata` | Associations phénotypiques des maladies rares, XML français et anglais | [Orphadata Science](https://sciences.orphadata.com/phenotypes/) |
| `rxnorm` | Contenu prescriptible, version du 2 novembre 2026 | [NLM](https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html) |
| `loinc` | Archive complète 2.83 | [Compte LOINC](https://loinc.org/kb/api/auth), variables `MEDIKRISTAL_LOINC_USER` et `MEDIKRISTAL_LOINC_PASSWORD` |
| `ccdd`, `pclocd`, `snomed-ct-ca` | CCDD en ZIP CSV, pCLOCD en XLSX et SNOMED CT CA en ZIP RF2. L’outil vérifie le SHA-256 publié. | [Compte système Inforoute](https://accelero.infoway-inforoute.ca/en/syndication-feed), variables `MEDIKRISTAL_INFOWAY_CLIENT_ID` et `MEDIKRISTAL_INFOWAY_CLIENT_SECRET` |
| `rxnorm-complet` | Version intégrale du 2 novembre 2026 | [Clé UMLS](https://documentation.uts.nlm.nih.gov/automating-downloads.html), variable `MEDIKRISTAL_UMLS_API_KEY` |

Configurer les variables dans la session avant de sélectionner une source avec accès contrôlé. L’outil utilise les API des éditeurs et conserve les identifiants hors des reçus. Les URL signalées dans les reçus identifient les données d’origine. Les URL d’authentification et les jetons sont exclus.

Les bases nommées ci-dessus sont des ressources de référence. Les recommandations et guides restent sélectionnés par sujet, juridiction et droits. Une mise à jour d’une version épinglée se fait dans le catalogue du script avec l’empreinte officielle lorsqu’elle est disponible. Les règles de transformation et de revue sont décrites au [chapitre 27](27-connectors.md).
