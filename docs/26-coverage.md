# 26 — Couverture fonctionnelle et règles de complétude

## Ce que signifie « couvert »

Cette version 1.1 décrit une cible, pas des capacités déployées. Une fonctionnalité peut être spécifiée sans disposer du contenu clinique, du connecteur réel ou du code. Ne pas présenter ces états comme équivalents. Les chapitres 27–33 complètent les chapitres 01–25 ; une décision nouvelle est consignée au chapitre 20. Les contrats de transport ne remplacent pas les invariants du domaine.

La [matrice structurée](../contracts/traceability.json) relie chaque exigence MK aux chapitres, opérations OpenAPI, objets, interface, événement, tests d’acceptation et lot. Elle est l’inventaire de couverture à maintenir. Une référence de test est un scénario spécifié, jamais une preuve de son exécution.

## Fonctionnalités de la conversation

| Demande | Exigences | Référence propriétaire | Condition restant extérieure au code |
| --- | --- | --- | --- |
| Aligné sur kOA sans dépendance | MK-001, MK-014 | 02, 14 | Schémas externes épinglés et compatibilité testée |
| Relier les bases médicales | MK-004, MK-005 | 05, 06, 27 | Versions, droits et corpus réellement disponibles |
| Ingestion à tous les niveaux par d’autres logiciels | MK-013, MK-025 | 13, 30 | Adaptateur consommateur pour chaque format externe |
| Symptômes, hypothèses et probabilités | MK-006, MK-007 | 04, 07 | Modèles et population admissibles |
| Tests en fonction coût/disponibilité/utilité | MK-008, MK-009, MK-026 | 08, 09, 28 | Utilités, fenêtres cliniques, catalogues locaux |
| Résultats successifs puis traitements | MK-007, MK-011, MK-028 | 04, 10, 30 | Protocoles, règles thérapeutiques et destinataires |
| Automatisation à l’accueil | MK-027 | 29 | Politique d’actes autorisés et intégration réelle |
| Inventaire IRM/laboratoires et priorités | MK-010, MK-022, MK-029 | 09, 28, 30 | Inventaire local, capacité, personnel et créneaux |
| Coûts saisis par administration | MK-009, MK-029 | 09, 30, 31 | Perspective comptable et devis datés |
| Catalogue des méthodes diagnostiques | MK-021 | 21, 27 | Enrichissement des actes et révision des mappings |
| Contributions d’universités/chercheurs | MK-012, MK-024 | 11, 30 | Révision scientifique indépendante |
| Patient, clinicien, infirmier, administrateur, API | MK-003, MK-015 | 15, 16, 31 | Habilitations et contexte d’usage |
| Hors ligne, gratuit connecté, payant optionnel | MK-002, MK-017, MK-023 | 12, 17 | Paquets locaux et connecteurs disponibles |
| Réutiliser l’open source | MK-020 | 02, 19, 32 | Compatibilité et licences vérifiées par version |

## Une tranche est complète lorsque

Elle possède une commande ou requête typée, une autorisation serveur, un propriétaire transactionnel, ses invariants, ses erreurs, son événement durable si elle mute l’état, un parcours utilisable, des tests métier et un statut annoncé honnêtement dans `/capabilities`. Les mutations administratives doivent être aussi traçables que les commandes cliniques.

Les scénarios techniques doivent tester les erreurs et les reprises, pas seulement un parcours heureux. Les interfaces peuvent arriver progressivement, mais une action API non exposée dans l’interface appropriée demeure une limite fonctionnelle déclarée.

## Limites explicites de la livraison

Le corpus universel des maladies, procédures, performances et traitements n’est pas livré. Les formats des partenaires hospitaliers ne sont pas connus. Les profils FHIR complets et leurs paquets de conformance, les écrans codés, les migrations SQL et les modèles cliniques restent des livrables d’implémentation. Les contrats initiaux étendus couvrent les commandes centrales ; la matrice n’est pas une preuve que toutes les variantes locales possibles sont connues.

Toute nouvelle fonction doit entrer dans la matrice avant de recevoir le statut `implemented`. L’absence de contenu médical bloque sa capacité clinique, pas la construction et les essais synthétiques du mécanisme.
