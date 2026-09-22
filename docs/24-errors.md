# 24 — Erreurs et invariants

## Codes métier stables

| Code | Effet | Reprise |
|---|---|---|
| insufficient_data | Évaluation incomplète | Obtenir entrées demandées |
| out_of_scope | Modèle non applicable | Modèle/protocole adapté ou révision |
| not_estimable | Pas de probabilité justifiée | Présenter relation/score étiqueté |
| conflicting_observations | Informations contradictoires | Résolution explicite |
| ambiguous_mapping | Correspondance non résolue | Révision du mapping |
| invalid_unit | Conversion/calcul refusé | Corriger unité avec provenance |
| stale_case | Proposition basée sur ancienne version | Réévaluer |
| stale_availability | Capacité non confirmée | Rafraîchir propriétaire |
| unknown_cost | Comparaison économique incomplète | Compléter ou comparer sous incertitude |
| model_failed | Calcul non abouti | Diagnostic technique, pas 0 % |
| release_not_admitted | Corpus non autorisé dans le contexte | Admission appropriée |
| artifact_integrity_failed | Pack bloqué | Nouvelle copie vérifiée |
| artifact_revoked | Usage concerné bloqué | Version admissible et analyse impacts |
| capability_unavailable | Adaptateur absent/panne | Fallback déclaré ou attente |
| budget_exceeded | Appel payant non effectué | Budget/politique explicite |
| provider_outcome_unknown | Appel possiblement exécuté | Réconciliation |
| idempotency_conflict | Clé réutilisée différemment | Nouvelle commande intentionnelle |
| booking_conflict | Slot non attribuable | Nouvelle proposition |
| booking_unconfirmed | Pas de réservation certaine | Attendre reçu/réconcilier |
| permission_denied | Action refusée | Principal/grant approprié |
| license_restricted | Usage/export non permis | Source ou droits appropriés |
| clinical_use_not_admitted | Capacité seulement engineering/research | Preuves et politique adaptées |
| result_quarantined | Résultat stocké non utilisé | Corriger identité/méthode/qualité |

## Invariants de décision

I01. Aucun prix ne modifie les probabilités cliniques. I02. Toute action externe repose sur une version du cas fraîche. I03. Inconnu n'est pas absent. I04. Un score n'est pas une probabilité. I05. Une réservation n'est confirmée que par son propriétaire. I06. Un événement dupliqué ne double aucun effet. I07. Toute correction conserve la trace historique. I08. Une signature ne valide pas la médecine. I09. Une release publiée ne devient pas cliniquement admise par défaut. I10. Le mode payant ne donne pas de permissions supplémentaires. I11. Une source non accessible ne disparaît pas de la provenance. I12. Une sortie LLM ne remplace pas une preuve. I13. Le catalogue d'équipements ne suffit pas à décrire une capacité. I14. Les clés externes sont namespacées. I15. Toute exportation respecte finalité, données et droits. I16. Le système doit s'abstenir honnêtement lorsqu'il ne couvre pas le cas.

## Priorité des erreurs

Autorisation et identité avant accès à des informations ; intégrité et droits avant chargement de corpus ; applicabilité avant calcul ; fraîcheur et autorisation avant action. Une erreur d'infrastructure ne se présente pas comme résultat clinique normal. Plusieurs limitations peuvent coexister ; les retourner sans masquer les causes utiles au destinataire autorisé.
