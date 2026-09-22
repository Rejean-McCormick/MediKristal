"""Génère les contrats documentaires ; ce fichier n'est pas le backend MediKristal."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = {}
def s(desc=None):
    x = {'type':'string','minLength':1}
    if desc: x['description']=desc
    return x
def enum(*values): return {'type':'string','enum':list(values)}
def ref(name): return {'$ref':'#/$defs/'+name}
def arr(item): return {'type':'array','items':item}
def nullable(item): return {'anyOf':[item,{'type':'null'}]}
def obj(props, required=None, desc=None):
    x={'type':'object','additionalProperties':False,'properties':props,'required':list(props) if required is None else required}
    if desc:x['description']=desc
    return x
def define(name,props,required=None,desc=None):
    D[name]=obj(props,required,desc)
def resource(name,props,required=None):
    base={'id':ref('UUID'),'tenant_id':ref('UUID'),'revision':ref('Revision'),'created_at':ref('Timestamp'),'updated_at':ref('Timestamp')}
    define(name,base|props,list(base)+(list(props) if required is None else required))

D['UUID']={'type':'string','format':'uuid'}
D['Timestamp']={'type':'string','format':'date-time'}
D['Revision']={'type':'integer','minimum':1}
D['Digest']={'type':'string','pattern':'^sha256:[a-f0-9]{64}$'}
D['Probability']={'type':'number','minimum':0,'maximum':1}
D['UseLevel']=enum('engineering','research','clinical_advisory','clinical_execution')
D['Mode']=enum('offline_free','online_free','online_extended')
define('Concept',{'system':{'type':'string','format':'uri'},'code':s(),'version':s(),'display':s()},['system','code','version'])
define('ArtifactRef',{'id':s(),'version':s(),'digest':ref('Digest')})
define('ForeignRef',{'owner':s(),'id':s(),'version':s()})
define('Quantity',{'kind':{'const':'quantity'},'value':{'type':'number'},'unit':s(),'comparator':enum('eq','lt','le','gt','ge'),'original':s()},['kind','value','unit','comparator'])
define('CodedValue',{'kind':{'const':'coded'},'value':ref('Concept')})
define('BooleanValue',{'kind':{'const':'boolean'},'value':{'type':'boolean'}})
define('TextValue',{'kind':{'const':'text'},'value':s()})
define('IntervalValue',{'kind':{'const':'interval'},'low':{'type':'number'},'high':{'type':'number'},'unit':s()})
define('RatioValue',{'kind':{'const':'ratio'},'numerator':{'type':'number'},'denominator':{'type':'number','exclusiveMinimum':0},'unit':s()})
D['ObservationValue']={'oneOf':[ref(n) for n in ['Quantity','CodedValue','BooleanValue','TextValue','IntervalValue','RatioValue']]}
define('SourceRef',{'source_id':s(),'source_version':s(),'record_id':s(),'digest':ref('Digest')},['source_id','source_version','record_id'])
define('Scope',{'population_id':s(),'setting':s(),'jurisdiction':s(),'language':s(),'valid_from':ref('Timestamp'),'valid_until':nullable(ref('Timestamp'))})
define('CreateCase',{'subject_ref':ref('UUID'),'intended_use':ref('UseLevel'),'language':s(),'synthetic':{'type':'boolean'},'context_refs':arr(ref('UUID'))})
resource('ClinicalCase',{'subject_ref':ref('UUID'),'intended_use':ref('UseLevel'),'language':s(),'synthetic':{'type':'boolean'},'context_refs':arr(ref('UUID')),'lifecycle':enum('draft','active','waiting','closed','cancelled')})
obs={'concept':ref('Concept'),'kind':enum('symptom','sign','measurement','history','exposure','medication','allergy','test_result','patient_report'),'presence':enum('present','absent','unknown','not_assessed'),'value':nullable(ref('ObservationValue')),'effective_at':ref('Timestamp'),'status':enum('proposed','preliminary','final','amended','entered_in_error'),'source':ref('SourceRef'),'quality':enum('usable','uncertain','quarantined'),'method_ref':nullable(ref('Concept')),'dependency_refs':arr(ref('UUID'))}
define('RecordObservation',obs)
resource('Observation',{'case_id':ref('UUID'),'recorded_at':ref('Timestamp'),'replaces_id':nullable(ref('UUID'))}|obs)
for name in ['RecordObservation','Observation']:
    D[name]['allOf']=[{'if':{'properties':{'presence':{'enum':['unknown','not_assessed','absent']}},'required':['presence']},'then':{'properties':{'value':{'type':'null'}}}}]
define('AmendObservation',{'reason':s(),'replacement':ref('RecordObservation')})
define('CaseTransition',{'target':enum('active','waiting','closed','cancelled'),'reason':s()})
define('EvaluationRequest',{'case_revision':ref('Revision'),'knowledge_release':ref('ArtifactRef'),'model_refs':arr(ref('ArtifactRef')),'evaluation_time':ref('Timestamp'),'intended_use':ref('UseLevel')})
define('MissingInput',{'concept':ref('Concept'),'reason':s(),'required_by':s()})
define('IntervalEstimate',{'low':ref('Probability'),'high':ref('Probability'),'level':ref('Probability'),'method':s()})
define('HypothesisResult',{'concept':ref('Concept'),'kind':enum('probability','score','qualitative'),'probability':nullable(ref('Probability')),'score':nullable({'type':'number'}),'qualitative':nullable(s()),'interval':nullable(ref('IntervalEstimate')),'target_event':s(),'horizon':s(),'model_ref':ref('ArtifactRef'),'scope_status':enum('applicable','out_of_scope','uncertain'),'calibration_ref':nullable(ref('ArtifactRef')),'evidence_refs':arr(ref('ArtifactRef')),'reason_codes':arr(s())})
D['HypothesisResult']['allOf']=[
 {'if':{'properties':{'kind':{'const':'probability'}}},'then':{'properties':{'probability':ref('Probability'),'score':{'type':'null'},'qualitative':{'type':'null'}}}},
 {'if':{'properties':{'kind':{'const':'score'}}},'then':{'properties':{'probability':{'type':'null'},'score':{'type':'number'},'qualitative':{'type':'null'},'interval':{'type':'null'}}}},
 {'if':{'properties':{'kind':{'const':'qualitative'}}},'then':{'properties':{'probability':{'type':'null'},'score':{'type':'null'},'qualitative':s(),'interval':{'type':'null'}}}}]
define('TraceNode',{'node_id':s(),'kind':enum('observation','transformation','model','evidence','decision'),'reference':s(),'parent_ids':arr(s()),'summary':s()})
resource('Evaluation',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'knowledge_release':ref('ArtifactRef'),'evaluation_time':ref('Timestamp'),'intended_use':ref('UseLevel'),'status':enum('complete','partial','insufficient_data','out_of_scope','failed'),'stale':{'type':'boolean'},'synthetic':{'type':'boolean'},'hypotheses':arr(ref('HypothesisResult')),'missing_inputs':arr(ref('MissingInput')),'limitations':arr(s()),'trace':arr(ref('TraceNode')),'engine_version':s(),'replay_digest':ref('Digest')})
resource('ActionProposal',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'evaluation_id':ref('UUID'),'kind':enum('ask','examine','test','observe','refer','treat_option'),'target':ref('Concept'),'protocol_ref':ref('ArtifactRef'),'preconditions':arr(s()),'reason_codes':arr(s()),'evidence_refs':arr(ref('ArtifactRef')),'status':enum('proposed','accepted','rejected','expired','superseded','order_requested'),'expires_at':ref('Timestamp')})
define('ProposalDecision',{'decision':enum('accept','reject'),'reason':s()})
define('OrderRequest',{'proposal_id':ref('UUID'),'case_revision':ref('Revision'),'destination':s(),'authorization_policy_ref':ref('ArtifactRef')})
resource('ServiceOrder',{'proposal_id':ref('UUID'),'case_id':ref('UUID'),'case_revision':ref('Revision'),'destination':s(),'status':enum('requested','accepted','in_progress','completed','rejected','cancel_requested','cancelled','reconciling'),'foreign_ref':nullable(ref('ForeignRef'))})
define('CapabilityInput',{'procedure':ref('Concept'),'site_ref':s(),'resource_refs':arr(s()),'required_skills':arr(s()),'duration_minutes':{'type':'integer','minimum':1},'capacity':{'type':'integer','minimum':1},'constraints':arr(s())})
resource('ResourceCapability',D['CapabilityInput']['properties'])
define('Slot',{'slot_id':s(),'start':ref('Timestamp'),'end':ref('Timestamp'),'state':enum('free','held','booked','unavailable','unknown'),'remaining_capacity':{'type':'integer','minimum':0}})
resource('AvailabilitySnapshot',{'capability_id':ref('UUID'),'owner':s(),'captured_at':ref('Timestamp'),'valid_until':ref('Timestamp'),'mode':enum('confirmed','estimated'),'slots':arr(ref('Slot'))})
define('CostInput',{'capability_id':ref('UUID'),'amount_minor':{'type':'integer','minimum':0},'currency':{'type':'string','pattern':'^[A-Z]{3}$'},'kind':enum('marginal','average','tariff','patient_out_of_pocket'),'perspective':s(),'valid_from':ref('Timestamp'),'valid_until':ref('Timestamp'),'source':ref('SourceRef')})
resource('CostQuote',D['CostInput']['properties'])
define('PlanRequest',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'evaluation_id':ref('UUID'),'proposal_ids':arr(ref('UUID')),'resource_snapshot_ids':arr(ref('UUID')),'policy_ref':ref('ArtifactRef')})
resource('Plan',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'status':enum('optimal','feasible','infeasible','unknown'),'strategy_refs':arr(s()),'selected_strategy_ref':nullable(s()),'limitations':arr(s()),'policy_ref':ref('ArtifactRef'),'resource_snapshot_ids':arr(ref('UUID')),'explanation':s()})
define('BookingRequest',{'order_id':ref('UUID'),'capability_id':ref('UUID'),'slot_id':s(),'availability_snapshot_id':ref('UUID')})
resource('Booking',{'order_id':ref('UUID'),'capability_id':ref('UUID'),'slot_id':s(),'owner':s(),'status':enum('proposed','hold_requested','held','confirm_requested','confirmed','expired','rejected','cancel_requested','cancelled','reconciling'),'hold_expires_at':nullable(ref('Timestamp')),'foreign_ref':nullable(ref('ForeignRef'))})
define('ReasonCommand',{'reason':s()})
define('SourceRegistration',{'name':s(),'publisher':s(),'uri':{'type':'string','format':'uri'},'source_type':enum('terminology','guideline','evidence','dataset','device_catalog','local_catalog'),'access':enum('free','paid','unknown'),'rights':enum('redistributable','local_import_only','restricted','unknown'),'rights_evidence_ref':s()})
resource('Source',D['SourceRegistration']['properties'])
define('ImportRequest',{'source_version':s(),'uploaded_file_ref':s(),'expected_digest':ref('Digest')})
define('ReleaseFile',{'path':{'type':'string','pattern':'^(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))[^\\\\]+$'},'sha256':ref('Digest'),'size_bytes':{'type':'integer','minimum':0}})
define('KnowledgeRelease',{'format':{'const':'medikristal.knowledge-release/1'},'release_id':ref('Digest'),'version':s(),'status':enum('draft','reviewing','candidate','published','deprecated','revoked'),'usage':ref('UseLevel'),'synthetic':{'type':'boolean'},'files':arr(ref('ReleaseFile')),'source_refs':arr(ref('ArtifactRef')),'model_refs':arr(ref('ArtifactRef')),'protocol_refs':arr(ref('ArtifactRef')),'rights_manifest_ref':ref('ArtifactRef'),'qualification_refs':arr(ref('ArtifactRef')),'minimum_runtime':s(),'built_at':ref('Timestamp'),'signatures':arr(s())})
define('ReleaseBuildRequest',{'source_snapshot_refs':arr(ref('ArtifactRef')),'model_refs':arr(ref('ArtifactRef')),'protocol_refs':arr(ref('ArtifactRef')),'intended_use':ref('UseLevel'),'synthetic':{'type':'boolean'}})
define('ReleaseActivation',{'release_ref':ref('ArtifactRef'),'policy_ref':ref('ArtifactRef'),'reason':s()})
define('Assertion',{'id':s(),'subject':ref('Concept'),'predicate':s(),'object':ref('Concept'),'scope':ref('Scope'),'source_refs':arr(ref('SourceRef')),'status':enum('hypothesis','claimed','sourced','disputed','reviewed','validated','rejected','retracted','superseded'),'certainty':enum('unknown','low','medium','high','not_applicable'),'evidence_refs':arr(ref('ArtifactRef'))})
define('EvidenceEstimate',{'id':s(),'measure':enum('prevalence','sensitivity','specificity','likelihood_ratio_positive','likelihood_ratio_negative','conditional_probability','effect_size'),'value':{'type':'number'},'population_ref':s(),'setting':s(),'target':ref('Concept'),'test':nullable(ref('Concept')),'threshold_description':nullable(s()),'sample_size':nullable({'type':'integer','minimum':1}),'interval_description':nullable(s()),'source_refs':arr(ref('SourceRef')),'limitations':arr(s()),'review_status':enum('extracted','reviewed','rejected')})
define('ModelManifest',{'id':s(),'version':s(),'digest':ref('Digest'),'type':enum('bayesian_network','likelihood','regression','prediction_rule','ml','synthetic'),'scope':ref('Scope'),'hypothesis_space':enum('mutually_exclusive','multi_label'),'input_concepts':arr(ref('Concept')),'parameter_ref':ref('ArtifactRef'),'evidence_refs':arr(ref('ArtifactRef')),'qualification_refs':arr(ref('ArtifactRef')),'missingness_policy':s(),'abstention_policy_ref':ref('ArtifactRef'),'engine_version':s(),'intended_use':ref('UseLevel')})
define('ContributionInput',{'kind':enum('mapping','assertion','estimate','model','protocol','translation','correction'),'target_ref':ref('ArtifactRef'),'proposed_artifact_ref':ref('ArtifactRef'),'rationale':s(),'evidence_refs':arr(ref('ArtifactRef')),'scope':ref('Scope')})
resource('Contribution',D['ContributionInput']['properties']|{'status':enum('draft','submitted','screening','under_review','changes_requested','accepted','rejected','withdrawn','published')})
define('ReviewDecision',{'verdict':enum('accept','reject','request_changes'),'rationale':s(),'evidence_refs':arr(ref('ArtifactRef')),'conflict_of_interest':s()})
define('ProviderPolicyInput',{'provider_id':s(),'enabled':{'type':'boolean'},'allowed_modes':arr(ref('Mode')),'allows_patient_data':{'type':'boolean'},'allowed_purposes':arr(s()),'budget_minor':{'type':'integer','minimum':0},'currency':{'type':'string','pattern':'^[A-Z]{3}$'},'period_start':ref('Timestamp'),'period_end':ref('Timestamp'),'fallback_capability':nullable(s())})
resource('ProviderPolicy',D['ProviderPolicyInput']['properties'])
define('ProviderUsage',{'provider_id':s(),'period_start':ref('Timestamp'),'period_end':ref('Timestamp'),'reserved_minor':{'type':'integer','minimum':0},'spent_minor':{'type':'integer','minimum':0},'currency':s()})
define('Capability',{'name':s(),'state':enum('available','degraded','unavailable','not_configured','not_qualified'),'requires_network':{'type':'boolean'},'paid':{'type':'boolean'},'supported_uses':arr(ref('UseLevel')),'limitations':arr(s())})
define('Capabilities',{'api_version':{'const':'0.2.0'},'mode':ref('Mode'),'network_scope':enum('none','lan','internet'),'capabilities':arr(ref('Capability'))})
resource('Operation',{'kind':s(),'status':enum('queued','running','succeeded','failed','cancelled','reconciling'),'result_ref':nullable(s()),'error_code':nullable(s()),'correlation_id':ref('UUID')})
define('FieldError',{'path':s(),'code':s()})
define('Error',{'type':s(),'title':s(),'status':{'type':'integer','minimum':400,'maximum':599},'code':s(),'detail':s(),'correlation_id':ref('UUID'),'field_errors':arr(ref('FieldError')),'retryable':{'type':'boolean'}})
define('Event',{'event_id':ref('UUID'),'event_type':s(),'tenant_id':ref('UUID'),'occurred_at':ref('Timestamp'),'aggregate_type':s(),'aggregate_id':s(),'aggregate_revision':ref('Revision'),'correlation_id':ref('UUID'),'causation_id':nullable(ref('UUID')),'classification':enum('public_knowledge','restricted_knowledge','patient_sensitive','operational'),'payload_ref':s(),'payload_digest':ref('Digest'),'producer':s()})
define('ExportRequest',{'release_ref':ref('ArtifactRef'),'target':enum('kristal_ses','fhir_knowledge'),'policy_ref':ref('ArtifactRef')})
define('ExpressionRef',{'library_ref':ref('ArtifactRef'),'expression_name':s()})
define('ProtocolTransition',{'when':enum('true','false','unknown','error','completed'),'target_step_id':s()})
define('ProtocolStep',{'step_id':s(),'kind':enum('input','evaluate','propose_action','wait_result','review','terminate'),'condition':nullable(ref('ExpressionRef')),'action_target':nullable(ref('Concept')),'transitions':arr(ref('ProtocolTransition')),'max_visits':{'type':'integer','minimum':1}})
define('ProtocolManifest',{'id':s(),'version':s(),'digest':ref('Digest'),'scope':ref('Scope'),'entry_step_id':s(),'steps':arr(ref('ProtocolStep')),'library_refs':arr(ref('ArtifactRef')),'model_refs':arr(ref('ArtifactRef')),'source_refs':arr(ref('SourceRef')),'intended_use':ref('UseLevel'),'qualification_refs':arr(ref('ArtifactRef'))})
define('TreatmentCheck',{'name':s(),'status':enum('pass','fail','unknown','not_applicable'),'reason':s(),'evidence_refs':arr(ref('ArtifactRef'))})
resource('TreatmentOption',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'target':ref('Concept'),'protocol_ref':ref('ArtifactRef'),'goal':s(),'checks':arr(ref('TreatmentCheck')),'status':enum('proposed','needs_information','not_applicable','superseded'),'evidence_refs':arr(ref('ArtifactRef')),'limitations':arr(s())})
define('TreatmentRequest',{'case_revision':ref('Revision'),'evaluation_id':ref('UUID'),'protocol_refs':arr(ref('ArtifactRef'))})
define('ReleaseDecision',{'verdict':enum('publish','revoke'),'reason':s(),'review_refs':arr(ref('ArtifactRef')),'policy_ref':ref('ArtifactRef')})
define('AvailabilityInput',{'owner':s(),'captured_at':ref('Timestamp'),'valid_until':ref('Timestamp'),'mode':enum('confirmed','estimated'),'slots':arr(ref('Slot'))})
define('Configuration',{'mode':ref('Mode'),'network_scope':enum('none','lan','internet'),'intended_use':ref('UseLevel'),'execution_policy':enum('proposal_only','protocol_authorized'),'provider_allowlist':arr(s()),'paid_budget_minor':{'type':'integer','minimum':0},'currency':{'type':'string','pattern':'^[A-Z]{3}$'},'local_release_ref':nullable(ref('ArtifactRef'))})
D['Configuration']['allOf']=[{'if':{'properties':{'mode':{'const':'offline_free'}}},'then':{'properties':{'network_scope':enum('none','lan'),'paid_budget_minor':{'const':0}}}},{'if':{'properties':{'mode':{'const':'online_free'}}},'then':{'properties':{'paid_budget_minor':{'const':0}}}}]
define('Page',{'items':arr(s('URI de ressource ; les endpoints spécialisés ont un type de page propre.')),'next_cursor':nullable(s())})

from contract_extensions import extend_domain, extend_api, extend_examples
extend_domain(globals())

schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:medikristal:contracts:domain:0.2.0','title':'MediKristal domain DTO v0.2.0','$defs':D}
(ROOT/'contracts/domain.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')

# OpenAPI : toutes les opérations ci-dessous sont cibles, aucune n'est implémentée ici.
components={name:{'$ref':'./domain.schema.json#/$defs/'+name} for name in D}
def oref(name):return {'$ref':'#/components/schemas/'+name}
def page(name):
    pn=name+'Page'
    components[pn]=obj({'items':arr(oref(name)),'next_cursor':nullable(s())})
    return pn
paths={}
def endpoint(path,method,oid,summary,response,request=None,permission='read',async_=False,match=False,description=''):
    import re
    parameters=[{'name':p,'in':'path','required':True,'schema':{'type':'string'},'description':'Identifiant opaque autorisé dans le tenant courant.'} for p in re.findall(r'{([^}]+)}',path)]
    if method=='post':parameters.append({'name':'Idempotency-Key','in':'header','required':True,'schema':s()})
    if match:parameters.append({'name':'If-Match','in':'header','required':True,'schema':s(),'description':'ETag de la révision attendue.'})
    if response.endswith('Page'):
        parameters.extend([{'name':'cursor','in':'query','schema':s()},{'name':'limit','in':'query','schema':{'type':'integer','minimum':1,'maximum':100,'default':50}}])
    status='202' if async_ else ('201' if method=='post' and not match else '200')
    responses={status:{'description':'Accepté pour traitement ; suivre Operation.' if async_ else 'Résultat de la commande ou lecture.','content':{'application/json':{'schema':oref(response)}}},'default':{'description':'Erreur typée ; aucun succès fictif.','content':{'application/problem+json':{'schema':oref('Error')}}}}
    if not async_ and not response.endswith('Page'):
        responses[status]['headers']={'ETag':{'description':'Révision opaque de la ressource lorsque mutable.','schema':s()}}
    op={'operationId':oid,'summary':summary,'description':description or 'Appliquer les invariants du chapitre propriétaire et les contrôles serveur.','x-permission':permission,'x-status':'specified','parameters':parameters,'responses':responses,'security':[{'bearerAuth':[]}]}
    if request:op['requestBody']={'required':True,'content':{'application/json':{'schema':oref(request)}}}
    paths.setdefault(path,{})[method]=op
endpoint('/capabilities','get','getCapabilities','Capacités effectivement disponibles','Capabilities',permission='capabilities:read')
endpoint('/cases','post','createCase','Créer un cas','ClinicalCase','CreateCase','cases:create')
endpoint('/cases','get','listCases','Lister les cas autorisés',page('ClinicalCase'),permission='cases:read')
endpoint('/cases/{case_id}','get','getCase','Lire un cas','ClinicalCase',permission='cases:read')
endpoint('/cases/{case_id}/transitions','post','transitionCase','Changer le cycle du cas','ClinicalCase','CaseTransition','cases:update',match=True)
endpoint('/cases/{case_id}/observations','post','recordObservation','Ajouter une observation','Observation','RecordObservation','observations:write',match=True)
endpoint('/cases/{case_id}/observations','get','listObservations','Lire les observations',page('Observation'),permission='cases:read')
endpoint('/observations/{observation_id}/amendments','post','amendObservation','Amender sans effacer la version originale','Observation','AmendObservation','observations:amend',match=True)
endpoint('/cases/{case_id}/evaluations','post','evaluateCase','Évaluer un snapshot','Operation','EvaluationRequest','evaluations:create',async_=True,match=True)
endpoint('/evaluations/{evaluation_id}','get','getEvaluation','Lire résultat, limites et trace','Evaluation',permission='cases:read')
endpoint('/cases/{case_id}/proposals','get','listProposals','Lire propositions',page('ActionProposal'),permission='cases:read')
endpoint('/proposals/{proposal_id}/decisions','post','decideProposal','Accepter ou refuser sans exécution implicite','ActionProposal','ProposalDecision','proposals:decide',match=True)
endpoint('/plans','post','comparePlans','Comparer stratégies admissibles','Operation','PlanRequest','plans:create',async_=True)
endpoint('/plans/{plan_id}','get','getPlan','Lire faisabilité et explication','Plan',permission='cases:read')
endpoint('/orders','post','requestOrder','Demander acte autorisé','Operation','OrderRequest','orders:execute',async_=True)
endpoint('/orders/{order_id}','get','getOrder','Lire état d’ordre','ServiceOrder',permission='orders:read')
endpoint('/resource-capabilities','post','createResourceCapability','Créer capacité locale','ResourceCapability','CapabilityInput','resources:admin')
endpoint('/resource-capabilities','get','listResourceCapabilities','Lister capacités',page('ResourceCapability'),permission='resources:read')
endpoint('/resource-capabilities/{capability_id}/availability','get','getAvailability','Disponibilité datée','AvailabilitySnapshot',permission='resources:read')
endpoint('/cost-quotes','post','createCostQuote','Enregistrer devis contextualisé','CostQuote','CostInput','resources:admin')
endpoint('/bookings','post','requestBooking','Demander réservation','Operation','BookingRequest','bookings:execute',async_=True)
endpoint('/bookings/{booking_id}','get','getBooking','Lire état propriétaire','Booking',permission='bookings:read')
endpoint('/bookings/{booking_id}/confirmations','post','confirmBooking','Confirmer un hold admissible','Operation','ReasonCommand','bookings:execute',async_=True,match=True)
endpoint('/bookings/{booking_id}/cancellations','post','cancelBooking','Demander annulation','Operation','ReasonCommand','bookings:execute',async_=True,match=True)
endpoint('/sources','post','registerSource','Enregistrer source et droits','Source','SourceRegistration','knowledge:author')
endpoint('/sources/{source_id}/imports','post','importSource','Importer fichier déjà téléversé et vérifié','Operation','ImportRequest','knowledge:author',async_=True)
endpoint('/knowledge/concepts','get','searchConcepts','Rechercher concepts versionnés',page('Concept'),permission='knowledge:read')
paths['/knowledge/concepts']['get']['parameters'].append({'name':'q','in':'query','required':True,'schema':s()})
endpoint('/knowledge/assertions','get','searchAssertions','Rechercher assertions',page('Assertion'),permission='knowledge:read')
endpoint('/knowledge/models','get','listModels','Lister manifestes admissibles',page('ModelManifest'),permission='knowledge:read')
endpoint('/knowledge/releases','post','buildRelease','Construire une release candidate','Operation','ReleaseBuildRequest','knowledge:build',async_=True)
endpoint('/knowledge/releases/{release_id}','get','getRelease','Lire manifeste de release','KnowledgeRelease',permission='knowledge:read')
endpoint('/knowledge/activations','post','activateRelease','Vérifier puis activer localement','Operation','ReleaseActivation','knowledge:activate',async_=True)
endpoint('/knowledge/exports','post','exportKnowledge','Exporter uniquement savoir autorisé','Operation','ExportRequest','knowledge:export',async_=True)
endpoint('/contributions','post','submitContribution','Soumettre proposition scientifique','Contribution','ContributionInput','contributions:submit')
endpoint('/contributions/{contribution_id}','get','getContribution','Lire proposition et état','Contribution',permission='contributions:read')
endpoint('/contributions/{contribution_id}/reviews','post','reviewContribution','Décision de révision sans activation','Contribution','ReviewDecision','contributions:review',match=True)
endpoint('/providers/policies','post','setProviderPolicy','Créer politique fournisseur sans secret','ProviderPolicy','ProviderPolicyInput','providers:admin')
endpoint('/providers/{provider_id}/usage','get','getProviderUsage','Consommation réservée et réelle','ProviderUsage',permission='providers:admin')
endpoint('/operations/{operation_id}','get','getOperation','État d’opération asynchrone','Operation',permission='operations:read')
endpoint('/resource-capabilities/{capability_id}/availability','post','recordAvailability','Enregistrer un snapshot sans simuler une réservation','AvailabilitySnapshot','AvailabilityInput','resources:admin')
endpoint('/knowledge/protocols','get','listProtocols','Lister protocoles versionnés',page('ProtocolManifest'),permission='knowledge:read')
endpoint('/knowledge/evidence','get','listEvidence','Lire preuves quantitatives contextualisées',page('EvidenceEstimate'),permission='knowledge:read')
endpoint('/knowledge/releases/{release_id}/decisions','post','decideRelease','Publier ou révoquer selon politique','Operation','ReleaseDecision','knowledge:publish',async_=True)
endpoint('/cases/{case_id}/treatment-evaluations','post','evaluateTreatments','Évaluer options sans prescrire','Operation','TreatmentRequest','evaluations:create',async_=True,match=True)
endpoint('/cases/{case_id}/treatment-options','get','listTreatmentOptions','Lire options et contrôles incomplets',page('TreatmentOption'),permission='cases:read')
endpoint('/configuration','get','getConfiguration','Lire profil sans secrets','Configuration',permission='configuration:read')
endpoint('/configuration/changes','post','changeConfiguration','Changer profil avec contrôle de capacités','Configuration','Configuration','configuration:admin',match=True)
extend_api(globals())
api={'openapi':'3.1.0','info':{'title':'MediKristal API — cible documentaire','version':'0.2.0','description':'Contrat étendu des opérations centrales ; non implémenté dans ce dossier. Les contrôles sémantiques restent obligatoires.'},'servers':[{'url':'http://localhost:8000/api/v1','description':'Développement local uniquement ; déploiement distant sous TLS.'}],'paths':paths,'components':{'schemas':components,'securitySchemes':{'bearerAuth':{'type':'http','scheme':'bearer','description':'Jeton local ou OIDC vérifié côté serveur.'}}}}
(ROOT/'contracts/openapi.json').write_text(json.dumps(api,ensure_ascii=False,indent=2)+'\n')

# Exemples cohérents et explicitement synthétiques.
U=lambda n:f'00000000-0000-4000-8000-{n:012d}'
T='2026-09-22T12:00:00Z'
H='sha256:'+'a'*64
A=lambda id:{'id':id,'version':'0.1.0','digest':H}
C=lambda code:{'system':'urn:medikristal:synthetic','code':code,'version':'1'}
B=lambda n:{'id':U(n),'tenant_id':U(1),'revision':1,'created_at':T,'updated_at':T}
examples={}
case=B(2)|{'subject_ref':U(3),'intended_use':'engineering','language':'fr','synthetic':True,'context_refs':[],'lifecycle':'active'}
examples['case']=('ClinicalCase',case)
observation=B(4)|{'case_id':U(2),'recorded_at':T,'replaces_id':None,'concept':C('SYN-T1'),'kind':'test_result','presence':'present','value':{'kind':'boolean','value':True},'effective_at':T,'status':'final','source':{'source_id':'synthetic-fixture','source_version':'1','record_id':'result-1'},'quality':'usable','method_ref':None,'dependency_refs':[]}
examples['observation']=('Observation',observation)
evaluation=B(5)|{'case_id':U(2),'case_revision':1,'knowledge_release':A('synthetic-release'),'evaluation_time':T,'intended_use':'engineering','status':'complete','stale':False,'synthetic':True,'hypotheses':[{'concept':C('SYN-D1'),'kind':'probability','probability':0.08/0.17,'score':None,'qualitative':None,'interval':None,'target_event':'Maladie fictive SYN-D1 présente','horizon':'instant synthétique','model_ref':A('synthetic-binary'),'scope_status':'applicable','calibration_ref':None,'evidence_refs':[],'reason_codes':['synthetic_only']}],'missing_inputs':[],'limitations':['Aucune calibration clinique ; nombres fictifs.'],'trace':[{'node_id':'n1','kind':'observation','reference':U(4),'parent_ids':[],'summary':'Test fictif positif'},{'node_id':'n2','kind':'model','reference':'synthetic-binary@0.1.0','parent_ids':['n1'],'summary':'Prior 0.10, sensibilité 0.80, spécificité 0.90, données fictives.'}],'engine_version':'synthetic-oracle/1','replay_digest':H}
examples['evaluation']=('Evaluation',evaluation)
cap=B(6)|{'procedure':C('SYN-T1'),'site_ref':'synthetic-site','resource_refs':['synthetic-machine'],'required_skills':['synthetic-operator'],'duration_minutes':15,'capacity':1,'constraints':['engineering_only']}
examples['capability']=('ResourceCapability',cap)
cost=B(7)|{'capability_id':U(6),'amount_minor':25,'currency':'CAD','kind':'marginal','perspective':'synthetic_facility','valid_from':T,'valid_until':'2026-09-23T12:00:00Z','source':{'source_id':'synthetic-fixture','source_version':'1','record_id':'cost-1'}}
examples['cost']=('CostQuote',cost)
booking=B(8)|{'order_id':U(9),'capability_id':U(6),'slot_id':'synthetic-slot','owner':'synthetic-facility','status':'reconciling','hold_expires_at':None,'foreign_ref':None}
examples['booking']=('Booking',booking)
policy=B(10)|{'provider_id':'synthetic-provider','enabled':False,'allowed_modes':['online_extended'],'allows_patient_data':False,'allowed_purposes':['terminology_lookup'],'budget_minor':0,'currency':'CAD','period_start':T,'period_end':'2026-10-22T12:00:00Z','fallback_capability':None}
examples['provider-policy']=('ProviderPolicy',policy)
scope={'population_id':'synthetic-only','setting':'engineering','jurisdiction':'TEST','language':'fr','valid_from':T,'valid_until':None}
contribution=B(11)|{'kind':'estimate','target_ref':A('synthetic-binary'),'proposed_artifact_ref':A('synthetic-candidate'),'rationale':'Correction fictive pour tester le workflow.','evidence_refs':[],'scope':scope,'status':'submitted'}
examples['contribution']=('Contribution',contribution)
extend_examples(globals())
index=[]
for file,(typ,data) in examples.items():
    (ROOT/f'examples/{file}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    index.append({'file':f'{file}.json','schema':typ,'synthetic':True})
(ROOT/'examples/index.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({'schemas':len(D),'operations':sum(len(v) for v in paths.values()),'examples':len(examples)}))
