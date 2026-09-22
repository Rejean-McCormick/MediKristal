# 16 — Sécurité, confidentialité et autorisations

## Modèle de menace

Menaces : accès à un autre patient/tenant, compte compromis, injection dans source/LLM, dépendance malveillante, pack falsifié, export illicite de données, double commande, réidentification via logs, faux contenu fournisseur, désactivation de garde par administrateur, coût payant incontrôlé et données périmées prises pour actuelles. Les protections sont testées, pas déclarées par une case UI.

## Matrice de droits minimale

| Action | Patient | Professionnel habilité | Contributeur | Admin ressources | Responsable publication |
|---|---|---|---|---|---|
| Lire un cas | Ses cas autorisés | Cas sous grant | Non par défaut | Non par défaut | Non par défaut |
| Ajouter déclaration patient | Oui, source déclarée | Oui | Non | Non | Non |
| Valider observation clinique | Non par rôle patient | Selon habilitation | Non | Non | Non |
| Demander évaluation | Selon couverture/politique | Oui selon usage | Cas synthétiques/recherche autorisés | Non | Non |
| Prescrire/ordonner | Non par rôle patient | Selon habilitation et politique | Non | Non | Non |
| Administrer coûts/slots | Non | Selon rôle additionnel | Non | Oui | Non |
| Proposer contenu | Selon canal | Oui | Oui | Selon domaine | Oui |
| Publier connaissance | Non | Pas automatiquement | Non | Non | Avec décision de révision requise |

Les rôles sont combinés avec finalité, relation au cas, tenant, niveau d'usage, scope et politiques. Service accounts ont droits ciblés. L'habilitation clinique réelle n'est pas déduite d'une auto-inscription « médecin ». Le système modélise la preuve et son expiration ; il n'invente pas de mécanisme québécois de vérification.

## Authentification et sessions

Identité locale disponible offline, mot de passe haché par bibliothèque éprouvée, protection brute-force, sessions expirantes et révocables. MFA pour comptes sensibles lorsque le déploiement l'exige ; sa dépendance doit fonctionner dans le profil retenu. OIDC optionnel avec issuer/audience/nonce et validation serveur. Les jetons ne vont pas dans les URL ou logs. Authentification ne vaut pas autorisation.

## Cloisonnement

Toutes les requêtes SQL et stockage fichiers tiennent compte du tenant et de l'objet. Ajouter défense DB (RLS ou équivalent qualifié) et tests de fuite. Corpus global en lecture seule avec ACL explicite ; cas et identités restent séparés. Les exports de connaissances inspectent le contenu, pas seulement son étiquette, pour éviter données individuelles dans qualifiers ou texte libre.

Chiffrement transport et repos selon déploiement ; clé hors image et dépôt, rotation, sauvegarde protégée et procédure de récupération. Sur poste autonome, protéger également sauvegardes et caches ; pas de promesse de confidentialité si disque et clés sont exposés au même attaquant.

## Audit

Journal accès, changements de droits, exports, décisions, publications, appels fournisseurs et break-glass si prévu. Éléments : principal, action, objet opaque, date, motif, corrélation, verdict. Aucune valeur clinique brute dans logs d'infrastructure. Journal d'audit append-only avec droits et rétention ; mécanisme d'intégrité ne remplace pas gestion des accès. La rétention et l'effacement sont configurés selon le cadre applicable avant usage réel, sans inventer ici un nombre d'années universel.

## Exécution et supply chain

Le chargement de modèle interdit pickle/code arbitraire non approuvé. Utiliser formats de données sûrs ou artefacts logiciels signés et isolés. Conteneurs non privilégiés, système de fichiers restreint, egress allowlist et budgets. Empêcher SSRF via URL de sources ou webhooks. Scanner dépendances, générer SBOM, figer hashes, documenter corrections. Aucun envoi de PHI vers télémétrie par défaut.

## Garde d'action

Un ordre exige grant, usage admis, protocole/modèle approprié, cas frais et trace. On ne peut pas supprimer le contrôle en mettant `force=true` non documenté. Les dérogations éventuelles sont une politique précise avec acteurs, raisons, limites et audit ; elles ne créent pas de données manquantes ni de fausse validation.

## Déploiement clinique

Cette spécification ne décide pas du statut réglementaire du futur produit ni de sa conformité québécoise ou internationale. Documenter finalité, utilisateurs, autonomie et périmètre réel ; effectuer l'évaluation applicable avant usage clinique. Le code peut être construit et testé immédiatement ; `clinically_validated` et `authorized_for_use` nécessitent des preuves extérieures au test logiciel.

## Permissions des contrats 0.2

`workflows:create` et `workflows:control` sont accordées au professionnel/service habilité pour le cas et le protocole ; elles ne suffisent jamais à autoriser un ordre. `results:ingest` exige une source authentifiée et un grant du cas ; les documents patient suivent la voie de déclaration/quarantaine appropriée. `careplans:write`, `followups:create` et `followups:manage` exigent une responsabilité sur le cas ; le rôle patient seul n’accorde pas de gestion institutionnelle. Les catalogues réutilisent `resources:admin` ou `knowledge:author` selon leur propriétaire. Aucune nouvelle permission n’est attribuée par défaut aux rôles existants.
