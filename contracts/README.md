# Contrats structurés v0.2.0

- `domain.schema.json` : 107 définitions de types, objets et commandes sous `$defs`.
- `openapi.json` : 80 opérations cibles en OpenAPI 3.1.0 ; références relatives vers le schéma de domaine.

Pour valider un objet, sélectionner explicitement sa définition, par exemple `#/$defs/Observation`. La racine du document de domaine est un catalogue de définitions, pas un schéma de ressource qui valide automatiquement tout payload. Les adaptateurs et le backend doivent utiliser un validateur JSON Schema Draft 2020-12 complet et des contrôles applicatifs.

## Garanties structurelles

Les DTO sont fermés (`additionalProperties: false`). Types, champs requis, enums, bornes de probabilité, forme des identifiants, formats de date et branches observation/hypothèse sont décrits. Les dates et identifiants exigent un validateur configuré pour vérifier les formats. Les références de versions/digests doivent ensuite être résolues et vérifiées.

## Contrôles sémantiques obligatoires

Le schéma ne prouve pas : identité du patient, permission, cohérence temporelle, tenant, existence d'une référence, droit d'utilisation d'une source, unité appropriée, applicability du modèle, calibration, ordre des bornes d'un intervalle, compatibilité d'un prélèvement, authenticité d'un reçu, ni validité clinique.

Exemples de contrôles à ajouter : interval.low <= interval.high ; slot.start < slot.end ; dates de validité cohérentes ; mesure sensitivity/specificity/prevalence bornée [0,1] ; rapport de vraisemblance non négatif ; membres et entrée d'un protocole existants ; transitions valides ; présence de références de qualification adéquates selon intended_use ; aucun contenu synthétique admis pour clinical_advisory/clinical_execution.

La commande clinique ne doit pas être autorisée parce que le JSON est valide. Les guards de domaine, de fraîcheur, d'autorisation et d'admission sont cumulatifs.

## Couverture

Ce contrat initial est assez précis pour construire le noyau et ses parcours de référence. Il ne constitue pas une implémentation de toutes les opérations administratives, profils FHIR, endpoints institutionnels ou contrats kOA. Les chapitres 13, 14 et 25 décrivent les extensions et frontières. Toute extension publique doit avoir son contrat et ses tests avant d'être annoncée comme disponible.

## Reproduction

`python tools/build_contracts.py` depuis la racine recrée ces deux fichiers et les exemples à partir du générateur documentaire. `python tools/validate_reference.py` effectue les vérifications locales documentées. Ce validateur limité sans dépendance n'est pas un substitut à un validateur complet OpenAPI, FHIR ou Kristal.

## Extensions 0.2

`tools/contract_extensions.py` est appelé par le générateur principal. Il définit les catalogues, workflows, résultats groupés, plans de soins et tâches de suivi. `traceability.json` relie les 32 exigences à leurs contrats et scénarios. Les objets de politique référencent des artefacts versionnés ; leur corps et leur admission sont vérifiés par les moteurs, pas par le seul DTO.

`Plan.comparisons`, `cost_snapshot_refs`, `computed_at` et `valid_until` sont optionnels pour lecture des anciennes sorties ; ils sont sémantiquement requis pour toute nouvelle comparaison économique calculée. Un résultat sans ces champs n’est pas exploitable comme classement économique complet. Les listes vides d’observations dans un lot, cycles de panels, références intertenant, bornes temporelles invalides et politiques non admises sont rejetés par les guards applicatifs.
