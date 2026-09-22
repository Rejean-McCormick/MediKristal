# 01 — Vision et exigences

## Définition

MediKristal transforme des sources médicales hétérogènes en connaissances reliées et traçables, utilisables pour évaluer un cas, choisir les informations supplémentaires utiles, proposer des options de prise en charge et coordonner leur réalisation. Il expose chaque niveau utile à des applications externes. Il est indépendant de kOA tout en étant compatible avec ses frontières d'autorité.

Le produit cible la pratique concrète : accueil d'urgence, clinique, établissement, contexte à ressources limitées et accès patient. Recherche et simulation sont des outils de contribution et de qualification, non une limitation de la vocation du produit. L'absence actuelle de partenaire ou données autorisées est un état du projet ; elle empêche d'affirmer une validation clinique, pas d'implémenter les contrats.

## Besoins normatifs

Les mots DOIT, NE DOIT PAS et DEVRAIT expriment une obligation, une interdiction et une recommandation dérogeable par ADR.

| ID | Exigence | Critère observable |
|---|---|---|
| MK-001 | Autonomie complète du cœur | Le parcours synthétique complet fonctionne sans kOA ni sortie réseau |
| MK-002 | Trois profils de fonctionnement | Offline gratuit, online gratuit et online avec fournisseurs payants sont testés |
| MK-003 | Utilisateurs multiples | Interfaces patient, professionnel, administration, contributeur et API |
| MK-004 | Sources préservées | Toute normalisation conserve l'original, la version et la transformation |
| MK-005 | Sémantique explicite | Une correspondance partielle ne devient pas équivalence |
| MK-006 | Probabilités justifiées | Chaque probabilité référence modèle, population et version |
| MK-007 | Réévaluation longitudinale | Un résultat corrigé invalide les propositions dépendantes |
| MK-008 | Acquisition d'information | Questions, examens cliniques, tests et surveillance sont comparables |
| MK-009 | Coûts contextualisés | Perspective, devise, nature du coût et date sont obligatoires |
| MK-010 | Ressources réelles | Une réservation exige confirmation du propriétaire |
| MK-011 | Traitements couverts architecturalement | Options et contrôles séparés de la prescription et administration |
| MK-012 | Contributions scientifiques | Révision, comparaison, publication et retrait sont traçables |
| MK-013 | Interopérabilité | API MediKristal et adaptateurs standards documentés |
| MK-014 | Compatibilité Kristal | Export de connaissance conforme au schéma externe épinglé |
| MK-015 | Confidentialité | Cloisonnement tenant/cas, permissions et minimisation |
| MK-016 | Reproductibilité | Entrées, versions, contexte de temps et moteur permettent le rejeu |
| MK-017 | Aucun paiement implicite | Fournisseur et enveloppe budgétaire explicitement autorisés |
| MK-018 | Pas de faux succès | Insuffisant, non couvert, expiré et indisponible sont des sorties natives |
| MK-019 | Déploiement graduel | Qualification logicielle distincte de validation clinique |
| MK-020 | Réutilisation libre | Composants évalués derrière des contrats remplaçables |
| MK-021 | Catalogue diagnostique extensible | Acte, méthode, équipement, prélèvement et résultat distincts |
| MK-022 | Équité et gouvernance | Le prix ne modifie pas le diagnostic ni l'urgence clinique |
| MK-023 | Modes équivalents en droits | Le mode payant ne confère aucun droit clinique supérieur |
| MK-024 | Pas de régression silencieuse | Une mise à jour ne remplace pas un modèle actif sans admission |

## Périmètre fonctionnel complet

Le parcours comprend identité/pseudonyme, consentements et droits, collecte des symptômes, contexte, observations, hypothèses, urgences reconnues par protocoles admis, probabilités lorsque justifiables, actions possibles, comparaison de stratégies, disponibilité, demandes, réservations, prélèvements, résultats, réévaluation, options thérapeutiques, suivi et clôture. L'explication et la provenance traversent toute la chaîne.

Il ne faut pas coder un dossier hospitalier universel, un PACS, un laboratoire complet, une facturation nationale ou une ontologie médicale nouvelle avant ce parcours. Ces systèmes sont des propriétaires externes auxquels MediKristal peut se connecter.

## Niveaux d'usage

`engineering` autorise fixtures et validation du logiciel ; `research` permet modèles candidats avec accès approprié ; `clinical_advisory` exige modèles/protocoles admis pour un contexte et fournit des propositions ; `clinical_execution` exige en plus des règles d'exécution et intégrations qualifiées. Ces niveaux sont indépendants du mode réseau. Les labels sont définis par MediKristal ; ils ne constituent pas une qualification réglementaire.

Un établissement à faibles ressources n'est pas un environnement de validation allégé. Le système décrit des capacités et limites réelles et ne transforme pas l'indisponibilité en indication d'un acte inadapté.

## Hors périmètre des contenus livrés ici

Ce dossier ne fournit aucun modèle diagnostique général calibré, référentiel de doses, seuil de triage ni preuve d'autorisation d'usage clinique. Il définit les mécanismes pour les intégrer et gérer. La couverture clinique complète est une succession de contenus qualifiés, jamais un booléen global `medical_system_ready`.

## Exigences complémentaires v1.1

| ID | Exigence | Critère observable |
| --- | --- | --- |
| MK-025 | Contrats consommables à chaque niveau | Requêtes de connaissances, cas, propositions, plans et suivi sans passage par une interface humaine |
| MK-026 | Optimisation explicite et reproductible | Politique versionnée, branches de stratégie et limites documentées |
| MK-027 | Automatisation sous autorisation | Workflow durable, guards réévalués et reprise après panne |
| MK-028 | Suivi avec responsabilité | Tâches attribuables, résultats tardifs et clôture justifiée |
| MK-029 | Catalogues administrables | Sites, ressources et actes révisables sans perdre réservations ni historique |
| MK-030 | Imports qualifiables par source | Profil versionné, rapport de quarantaine et tests de changements de format |
| MK-031 | Interfaces reflétant les états réels | Inconnu, périmé, en attente et confirmé restent distincts |
| MK-032 | Traçabilité livrable par livrable | Chaque exigence pointe vers contrats, interface, scénario et lot |
