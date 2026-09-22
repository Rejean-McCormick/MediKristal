# 10 — Options thérapeutiques

## Périmètre

Médicaments, mesures non médicamenteuses, procédures, orientation, surveillance et soins de soutien. Le système sépare `TreatmentOption`, décision, prescription, dispensation et administration. Une proposition n'est pas un traitement administré. Les systèmes cliniques ou pharmacies restent propriétaires de leurs actes exécutés.

## Modèle

Une option porte indication, objectif, population, bénéfices/risques sourcés, statut, protocole, alternative, disponibilité pertinente et surveillance. Pour un médicament : substance(s), produit éventuel, forme, voie, concentration, unité et dépendances terminologiques. Les détails de dose et de durée sont fournis uniquement par un module de calcul qualifié avec source et entrées ; ce dossier n'en fixe aucun.

## Contrôles requis

Vérifier identité, allergies documentées et niveau d'incertitude, traitements actifs y compris automédication déclarée, doublons de substance/classe selon règle, interactions, fonctions organiques nécessaires, grossesse/allaitement lorsque pertinents, âge/poids, indication et informations manquantes. Les contrôles sont eux-mêmes versionnés. Une donnée requise inconnue produit `needs_information` et empêche la présentation de compatibilité confirmée.

Une base de produits autorisés n'est pas une base exhaustive d'interactions ; CCDD/RxNorm ne remplacent pas la sélection de preuves thérapeutiques. Les paramètres fournis par un service payant gardent leur provenance et conditions ; une panne ne produit pas « aucune interaction ».

## Probabilité et décision

L'utilité d'un traitement dépend de ses effets attendus selon les états possibles, pas uniquement de la maladie la mieux classée. L'évaluation thérapeutique lit les probabilités applicables mais conserve les limites. Si aucun modèle de décision adéquat n'existe, présenter les options documentées sans classement numérique fallacieux.

## Exécution

La commande de prescription exige politique et acteur habilités, vérifications récentes, confirmation du destinataire et idempotence. Le canal patient affiche informations et propositions dans le périmètre admis ; il ne peut activer une prescription institutionnelle. Les suggestions expérimentales ne sont pas routées comme ordres. Les actions autorisées par protocole doivent déclarer exactement leur périmètre et conditions d'arrêt.

## Suivi

Le plan relie traitement choisi, surveillance, contrôles attendus et réévaluation. Les effets rapportés sont de nouvelles observations ; ils ne deviennent pas automatiquement preuve causale ni données d'apprentissage. Les événements indésirables et décisions d'arrêt sont conservés avec responsabilités de suivi. Une révision de connaissance peut signaler les plans actifs impactés.

## Tests

Concentration vs dose totale ; unité incompatible ; médicament combiné avec doublon d'ingrédient ; allergie inconnue ; interaction non couverte ; modèle hors population ; résultat rénal corrigé ; fournisseur d'interactions indisponible ; changement de traitement entre calcul et validation. Toutes les fixtures emploient des substances fictives ; aucune posologie réelle dans le corpus technique livré.
