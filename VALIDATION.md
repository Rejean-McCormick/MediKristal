# Rapport de validation documentaire

Validation documentaire et sous-ensemble de schéma généré ; pas validation complète OpenAPI/JSON Schema externe, pas test applicatif ou clinique.

Résultat : 211 PASS ; 0 FAIL.

| Vérification | Résultat | Détail |
|---|---|---|
| json:sbom.cdx.json | PASS |  |
| json:source-snapshots.json | PASS |  |
| json:contracts/openapi.json | PASS |  |
| json:contracts/domain.schema.json | PASS |  |
| json:contracts/traceability.json | PASS |  |
| json:examples/cost.json | PASS |  |
| json:examples/procedure.json | PASS |  |
| json:examples/workflow.json | PASS |  |
| json:examples/followup.json | PASS |  |
| json:examples/evaluation.json | PASS |  |
| json:examples/capability.json | PASS |  |
| json:examples/booking.json | PASS |  |
| json:examples/case.json | PASS |  |
| json:examples/result-batch.json | PASS |  |
| json:examples/observation.json | PASS |  |
| json:examples/index.json | PASS |  |
| json:examples/contribution.json | PASS |  |
| json:examples/provider-policy.json | PASS |  |
| json:backend/build/lib/medikristal/_assets/contracts/openapi.json | PASS |  |
| json:backend/build/lib/medikristal/_assets/contracts/domain.schema.json | PASS |  |
| json:backend/build/lib/medikristal/_assets/contracts/traceability.json | PASS |  |
| json:backend/medikristal/_assets/contracts/openapi.json | PASS |  |
| json:backend/medikristal/_assets/contracts/domain.schema.json | PASS |  |
| json:backend/medikristal/_assets/contracts/traceability.json | PASS |  |
| schema local references | PASS |  |
| api references | PASS |  |
| path-parameters:getCapabilities | PASS |  |
| path-parameters:createCase | PASS |  |
| idempotency:createCase | PASS |  |
| path-parameters:listCases | PASS |  |
| path-parameters:getCase | PASS |  |
| path-parameters:transitionCase | PASS |  |
| idempotency:transitionCase | PASS |  |
| path-parameters:recordObservation | PASS |  |
| idempotency:recordObservation | PASS |  |
| path-parameters:listObservations | PASS |  |
| path-parameters:amendObservation | PASS |  |
| idempotency:amendObservation | PASS |  |
| path-parameters:evaluateCase | PASS |  |
| idempotency:evaluateCase | PASS |  |
| path-parameters:getEvaluation | PASS |  |
| path-parameters:listProposals | PASS |  |
| path-parameters:decideProposal | PASS |  |
| idempotency:decideProposal | PASS |  |
| path-parameters:comparePlans | PASS |  |
| idempotency:comparePlans | PASS |  |
| path-parameters:getPlan | PASS |  |
| path-parameters:requestOrder | PASS |  |
| idempotency:requestOrder | PASS |  |
| path-parameters:getOrder | PASS |  |
| path-parameters:createResourceCapability | PASS |  |
| idempotency:createResourceCapability | PASS |  |
| path-parameters:listResourceCapabilities | PASS |  |
| path-parameters:getAvailability | PASS |  |
| path-parameters:recordAvailability | PASS |  |
| idempotency:recordAvailability | PASS |  |
| path-parameters:createCostQuote | PASS |  |
| idempotency:createCostQuote | PASS |  |
| path-parameters:listCostQuotes | PASS |  |
| path-parameters:requestBooking | PASS |  |
| idempotency:requestBooking | PASS |  |
| path-parameters:getBooking | PASS |  |
| path-parameters:confirmBooking | PASS |  |
| idempotency:confirmBooking | PASS |  |
| path-parameters:cancelBooking | PASS |  |
| idempotency:cancelBooking | PASS |  |
| path-parameters:registerSource | PASS |  |
| idempotency:registerSource | PASS |  |
| path-parameters:listSources | PASS |  |
| path-parameters:importSource | PASS |  |
| idempotency:importSource | PASS |  |
| path-parameters:searchConcepts | PASS |  |
| path-parameters:searchAssertions | PASS |  |
| path-parameters:listModels | PASS |  |
| path-parameters:buildRelease | PASS |  |
| idempotency:buildRelease | PASS |  |
| path-parameters:getRelease | PASS |  |
| path-parameters:activateRelease | PASS |  |
| idempotency:activateRelease | PASS |  |
| path-parameters:exportKnowledge | PASS |  |
| idempotency:exportKnowledge | PASS |  |
| path-parameters:submitContribution | PASS |  |
| idempotency:submitContribution | PASS |  |
| path-parameters:listContributions | PASS |  |
| path-parameters:getContribution | PASS |  |
| path-parameters:reviewContribution | PASS |  |
| idempotency:reviewContribution | PASS |  |
| path-parameters:setProviderPolicy | PASS |  |
| idempotency:setProviderPolicy | PASS |  |
| path-parameters:getProviderUsage | PASS |  |
| path-parameters:getOperation | PASS |  |
| path-parameters:listProtocols | PASS |  |
| path-parameters:listEvidence | PASS |  |
| path-parameters:decideRelease | PASS |  |
| idempotency:decideRelease | PASS |  |
| path-parameters:evaluateTreatments | PASS |  |
| idempotency:evaluateTreatments | PASS |  |
| path-parameters:listTreatmentOptions | PASS |  |
| path-parameters:getConfiguration | PASS |  |
| path-parameters:changeConfiguration | PASS |  |
| idempotency:changeConfiguration | PASS |  |
| path-parameters:listSite | PASS |  |
| path-parameters:createSite | PASS |  |
| idempotency:createSite | PASS |  |
| path-parameters:getSite | PASS |  |
| path-parameters:reviseSite | PASS |  |
| idempotency:reviseSite | PASS |  |
| path-parameters:listManagedResource | PASS |  |
| path-parameters:createManagedResource | PASS |  |
| idempotency:createManagedResource | PASS |  |
| path-parameters:getManagedResource | PASS |  |
| path-parameters:reviseManagedResource | PASS |  |
| idempotency:reviseManagedResource | PASS |  |
| path-parameters:listProcedureEntry | PASS |  |
| path-parameters:createProcedureEntry | PASS |  |
| idempotency:createProcedureEntry | PASS |  |
| path-parameters:getProcedureEntry | PASS |  |
| path-parameters:reviseProcedureEntry | PASS |  |
| idempotency:reviseProcedureEntry | PASS |  |
| path-parameters:getResourceCapability | PASS |  |
| path-parameters:reviseResourceCapability | PASS |  |
| idempotency:reviseResourceCapability | PASS |  |
| path-parameters:createWorkflow | PASS |  |
| idempotency:createWorkflow | PASS |  |
| path-parameters:getWorkflow | PASS |  |
| path-parameters:transitionWorkflow | PASS |  |
| idempotency:transitionWorkflow | PASS |  |
| path-parameters:listCaseWorkflows | PASS |  |
| path-parameters:receiveResultBatch | PASS |  |
| idempotency:receiveResultBatch | PASS |  |
| path-parameters:createFollowUp | PASS |  |
| idempotency:createFollowUp | PASS |  |
| path-parameters:getFollowUp | PASS |  |
| path-parameters:transitionFollowUp | PASS |  |
| idempotency:transitionFollowUp | PASS |  |
| path-parameters:listCaseFollowUps | PASS |  |
| path-parameters:createCarePlan | PASS |  |
| idempotency:createCarePlan | PASS |  |
| path-parameters:listCaseCarePlans | PASS |  |
| path-parameters:getCarePlan | PASS |  |
| path-parameters:reviseCarePlan | PASS |  |
| idempotency:reviseCarePlan | PASS |  |
| path-parameters:getImportReport | PASS |  |
| path-parameters:getSource | PASS |  |
| path-parameters:listOptimizationPolicies | PASS |  |
| unique operation IDs | PASS |  |
| OpenAPI version | PASS |  |
| example:case.json | PASS |  |
| example:observation.json | PASS |  |
| example:evaluation.json | PASS |  |
| example:capability.json | PASS |  |
| example:cost.json | PASS |  |
| example:booking.json | PASS |  |
| example:provider-policy.json | PASS |  |
| example:contribution.json | PASS |  |
| example:workflow.json | PASS |  |
| example:followup.json | PASS |  |
| example:procedure.json | PASS |  |
| example:result-batch.json | PASS |  |
| negative:probability-range | PASS |  |
| negative:score-not-probability | PASS |  |
| negative:unknown-no-value | PASS |  |
| negative:unexpected-field | PASS |  |
| negative:negative-cost | PASS |  |
| negative:invalid-uuid | PASS |  |
| synthetic posterior positive | PASS |  |
| synthetic posterior negative | PASS |  |
| synthetic namespace | PASS |  |
| local Markdown links | PASS |  |
| requirements test mapping | PASS |  |
| 33 chapters | PASS |  |
| traceability exact requirement coverage | PASS |  |
| traceability:MK-001 | PASS |  |
| traceability:MK-002 | PASS |  |
| traceability:MK-003 | PASS |  |
| traceability:MK-004 | PASS |  |
| traceability:MK-005 | PASS |  |
| traceability:MK-006 | PASS |  |
| traceability:MK-007 | PASS |  |
| traceability:MK-008 | PASS |  |
| traceability:MK-009 | PASS |  |
| traceability:MK-010 | PASS |  |
| traceability:MK-011 | PASS |  |
| traceability:MK-012 | PASS |  |
| traceability:MK-013 | PASS |  |
| traceability:MK-014 | PASS |  |
| traceability:MK-015 | PASS |  |
| traceability:MK-016 | PASS |  |
| traceability:MK-017 | PASS |  |
| traceability:MK-018 | PASS |  |
| traceability:MK-019 | PASS |  |
| traceability:MK-020 | PASS |  |
| traceability:MK-021 | PASS |  |
| traceability:MK-022 | PASS |  |
| traceability:MK-023 | PASS |  |
| traceability:MK-024 | PASS |  |
| traceability:MK-025 | PASS |  |
| traceability:MK-026 | PASS |  |
| traceability:MK-027 | PASS |  |
| traceability:MK-028 | PASS |  |
| traceability:MK-029 | PASS |  |
| traceability:MK-030 | PASS |  |
| traceability:MK-031 | PASS |  |
| traceability:MK-032 | PASS |  |
| API version consistent | PASS |  |
| permissions all operations | PASS |  |
| revision mutation guards | PASS |  |
| negative:assigned-owner-required | PASS |  |
| negative:completed-proof-required | PASS |  |
| negative:unknown-criterion-not-zero | PASS |  |
| synthetic conditional strategy cost | PASS |  |

Ce validateur contrôle la spécification et les contrats ; il n’exécute pas la suite applicative. Les preuves logicielles exécutées sont consignées dans `APP_VALIDATION.md`. Les hashes des exemples sont des placeholders. La qualification native Kristal/FHIR, la compilation CQL et toute validation clinique restent hors de la portée de ce contrôle documentaire.
