# 27 — Connecteurs et intégration des sources

## Contrat commun d’import

L’unité d’import est `(source_id, source_version, blob_digest, parser_version, mapping_version)`. Le worker reçoit un fichier déjà stocké en quarantaine ou une référence de téléchargement autorisée, jamais une URL libre utilisée directement par le moteur clinique. Les identifiants sont conservés en chaînes, sans conversion numérique.

États : `received → verified → parsed → normalized → reviewed → published`; branches `quarantined`, `failed`, `cancelled`. Seule une release admissible publiée peut être activée. Un import n’active jamais des connaissances. Stocker `ImportRun`, `RawRecord`, `MappingCandidate`, `ImportIssue`, compteurs et checkpoint dans le module connaissances ; le binaire brut est immuable.

| Étape | Entrée | Sortie | Échec observable |
| --- | --- | --- | --- |
| Vérification | Blob, digest, droits, limites | Fichier admis au parsing | Format, taille, checksum ou droits incompatibles |
| Parsing | Profil de format épinglé | Enregistrements bruts avec position | Colonne requise absente, encodage non admis |
| Normalisation | Enregistrement et mapping versionné | Concepts/assertions candidats | Code ambigu, unité non résolue, référence pendante |
| Révision | Diff et rapport | Acceptation ou retour documenté | Perte de granularité, retrait massif inattendu |
| Publication | Candidat révisé | Release immuable et manifeste | Dépendance/droit non résolu |

Une colonne nouvelle facultative est conservée dans le brut et signalée ; une colonne requise manquante fait échouer le profil. Ne pas déduire une suppression de la seule absence dans un delta. Un remplacement complet doit être déclaré `full_snapshot`; un delta doit préciser sa base. Une reprise réutilise le même checkpoint et ne crée pas une nouvelle version logique des lignes déjà importées.

## Profils initiaux

Les mappings ci-dessous sont des contrats de conception. Les noms de colonnes externes viennent des documentations officielles listées en bas ; chaque implémentation doit épingler la version du fichier et une fixture légale. Aucun téléchargement ni droit de redistribution n’est implicite.

### LOINC : identité des observations

Entrée : table principale `Loinc.csv`, CSV à en-têtes. `LOINC_NUM` donne le code natif ; `COMPONENT`, `PROPERTY`, `TIME_ASPCT`, `SYSTEM`, `SCALE_TYP`, `METHOD_TYP` restent des attributs distincts. Le parser recherche les colonnes par nom, pas par position. Libellés et statut restent liés à la release. Les champs inconnus sont conservés dans le brut.

Sortie : concepts de mesure et références à leur méthode/échantillon, pas une capacité réservée ni une performance diagnostique. Les accessoires relatifs aux panels et remplacements demandent leurs propres profils ; ne pas fabriquer les composants d’un panel à partir de son libellé. Un code local proche crée `MappingCandidate`, jamais une équivalence automatique.

Tests : code conservé avec tiret ; CSV contenant virgules et guillemets ; méthode vide ; code déprécié encore référencé par un ancien résultat ; changement de colonne ; même release réimportée ; collision entre version de terminologie et code local.

### HPO : concepts et annotations de phénotypes

Importer séparément l’ontologie et `phenotype.hpoa`. Le profil d’annotation conserve notamment l’identifiant de maladie, le terme HPO, qualificatif, référence de preuve, fréquence et contexte présents dans la version épinglée. Les lignes provenant de publications différentes restent distinctes. Une annotation négative ne devient pas association positive.

Une fréquence de phénotype chez les sujets atteints n’est pas une probabilité de maladie sachant le phénotype. Conserver le sens conditionnel et le dénominateur lorsqu’il existe. Une fréquence absente reste absente ; une catégorie de fréquence ne devient pas un nombre central inventé. Ces annotations alimentent des candidats et preuves contextualisées, pas un diagnostic général calibré.

Tests : qualificatif négatif ; fraction de fréquence ; référence manquante ; plusieurs publications pour la même paire ; terme obsolète ; maladie hors domaine du modèle ; identifiant inconnu en quarantaine.

### RxNorm : noms, attributs et relations de médicaments

Entrée RRF : `RXNCONSO.RRF` pour noms/codes, `RXNREL.RRF` pour relations et `RXNSAT.RRF` pour attributs lorsqu’inclus dans le paquet. Lire UTF-8 avec séparateur `|` et conserver les champs vides. Le profil doit connaître le nombre et le sens des champs de la version ; ne pas traiter tous les fichiers RRF comme une table commune.

Conserver identifiants de concepts, types de termes et provenance native. Relier ingrédient, forme et produit sans les fusionner. Les attributs de sources tierces conservent leurs restrictions. Sortie : terminologie de médicaments ; aucune posologie ou interaction clinique n’est créée par ce connecteur.

Tests : plusieurs noms pour un concept ; relation entre concepts absents ; produit combiné ; identifiant retiré ; champ vide terminal ; source tierce non redistribuable.

### FHIR R4 : échange de cas et résultats

Importer les ressources autorisées selon le profil du partenaire : identité, `ServiceRequest`, `Observation`, `DiagnosticReport` et références utiles. Ce n’est pas un import de connaissances publiques. Le mapper doit résoudre le sujet, l’identifiant/version externes, le temps clinique, le statut, l’unité, le lien à la demande et la provenance. Un rapport avec plusieurs observations garde son groupement. Un résultat corrigé passe par le mécanisme d’amendement ; les valeurs absentes et les valeurs négatives sont distinctes.

Le destinataire d’un ordre confirme la réception puis son état d’exécution. Une réponse HTTP réussie ne signifie pas que l’acte a été réalisé. Les profils locaux non reconnus retournent `unsupported_profile`; les ressources portant des extensions cliniques inconnues requises sont mises en quarantaine. Le round trip doit mesurer et déclarer toute perte d’information.

### Catalogue local : capacités et prix

Premier profil détenu par MediKristal : CSV UTF-8 avec en-têtes `site_external_id,procedure_system,procedure_code,procedure_version,resource_external_id,duration_minutes,capacity`. Prix et calendriers utilisent des fichiers séparés pour éviter de les confondre avec l’acte. Le fichier de prix contient `capability_external_id,amount_minor,currency,kind,perspective,valid_from,valid_until`. Le profil exige une table de correspondance des identifiants externes vers les UUID locaux.

Import en deux phases : prévisualiser les créations/modifications/rejets, puis confirmer avec le digest de ce diff. Une ligne ambiguë ne modifie rien. Une ressource absente d’un fichier n’est pas supprimée. Une fermeture de capacité est une opération explicite ; les réservations existantes sont analysées avant application. Les prix sont de nouvelles versions, jamais une réécriture des coûts historiques.

### Autres sources

SNOMED CT/CA, pCLOCD, CCDD, DPD, Orphadata, classifications, recommandations et bases d’études passent par le même pipeline. Avant de coder chaque parser : consigner version, format, droits, échantillon légal, mapping et tests. Ces connecteurs restent `not_qualified` tant que cette fiche n’existe pas. Le registre affiche ce statut ; il ne les annonce pas comme déjà supportés.

## Sources techniques consultées pour cette révision

- [Structure de la table LOINC](https://loinc.org/kb/users-guide/loinc-database-structure/loinc-table-structure).
- [Annotations phenotype.hpoa](https://obophenotype.github.io/human-phenotype-ontology/annotations/phenotype_hpoa/).
- [Fichiers RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html) et [contenu prescriptible](https://www.nlm.nih.gov/research/umls/rxnorm/docs/prescribe.html).
- [FHIR R4 ServiceRequest](https://hl7.org/fhir/R4/servicerequest.html).

Ces références justifient les formats externes ; les états, profils CSV locaux et choix d’orchestration ci-dessus sont des décisions MediKristal. Les conditions d’accès doivent être vérifiées pour la version réellement installée.
