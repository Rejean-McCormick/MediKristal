# Vérification des intégrations satellites — 27 octobre 2026

**Portée :** vérification statique des instantanés de code et de documentation datés du 27 octobre 2026. **Aucune qualification runtime, CI distante, publication ni autorisation de production n’est déduite de cet audit.**

## Référence Kristal et preuve d'intégration

- MediKristal reste un logiciel indépendant avec ses propres contrats de domaine, OpenAPI et traçabilité; sa baseline actuelle est **API 0.2.0 / spécification 1.1** dans les documents du dépôt.
- Le `Kristal-Framework` fourni est en **v11 draft.4** et distingue les identités de graphe v11 du format portable `kristal_state` 6.0. Cette distinction ne transforme pas automatiquement les interfaces MediKristal en profils v11 conformes.
- Les adaptateurs MediKristal prévus pour des systèmes externes doivent être validés avec leurs contrats et des essais d'intégration spécifiques. Aucun test de bout en bout MediKristal → Framework v11 n'a été exécuté dans cet audit.
- Éléments examinés : `MediKristal/README.md`, `MediKristal/contracts/openapi.json`, `MediKristal/docs/14-integrations.md`, `MediKristal/backend/medikristal/adapters.py`, `Kristal-Framework/contracts/release.json`.

**Qualification restante :** fixer les versions de schéma, les mappings de provenance et lancer des tests d'intégration avec données synthétiques; ne pas présenter la compatibilité sémantique comme acquise.

## Mise à jour et preuve

Cette page décrit un état vérifié **sur fichiers**. Si le code, les contrats ou les captures de tests ont évolué depuis le snapshot, réexécuter les tests et réviser cette page avant publication.
