"""Extensions documentaires v0.2 ; aucun service applicatif n'est implémenté ici."""
def extend_domain(g):
    define,resource,ref,arr,s,enum,nullable=[g[n] for n in ['define','resource','ref','arr','s','enum','nullable']]
    catalog={
      'Site':{'owner':s(),'external_id':s(),'name':s(),'timezone':s(),'status':enum('active','retired')},
      'ManagedResource':{'site_id':ref('UUID'),'external_id':s(),'kind':enum('equipment','staff_pool','room','consumable_pool'),'name':s(),'status':enum('active','unavailable','retired')},
      'ProcedureEntry':{'concept':ref('Concept'),'family':s(),'specimen_refs':arr(ref('Concept')),'component_refs':arr(ref('Concept')),'detail_refs':arr(ref('ArtifactRef')),'status':enum('draft','active','retired')}
    }
    for name,props in catalog.items():
        define(name+'Input',props)
        define(name+'Revision',{'replacement':ref(name+'Input'),'reason':s()})
        resource(name,props)
    define('CapabilityRevision',{'replacement':ref('CapabilityInput'),'reason':s()})
    define('WorkflowInput',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'protocol_ref':ref('ArtifactRef'),'authorization_policy_ref':ref('ArtifactRef'),'intended_use':ref('UseLevel')})
    resource('WorkflowRun',g['D']['WorkflowInput']['properties']|{'status':enum('ready','running','waiting_input','waiting_review','waiting_external','reconciling','paused','completed','cancelled','failed'),'current_step_ids':arr(s()),'reason_codes':arr(s())})
    define('WorkflowTransition',{'action':enum('start','pause','resume','cancel'),'reason':s(),'case_revision':ref('Revision')})
    define('FollowUpInput',{'case_id':ref('UUID'),'origin_ref':s(),'owner_ref':nullable(s()),'due_at':ref('Timestamp'),'reason':s()})
    resource('FollowUpTask',g['D']['FollowUpInput']['properties']|{'status':enum('open','assigned','completed','cancelled'),'completion_ref':nullable(s())})
    define('FollowUpTransition',{'target':enum('open','assigned','completed','cancelled'),'owner_ref':nullable(s()),'completion_ref':nullable(s()),'reason':s()})
    g['D']['FollowUpTransition']['allOf']=[{'if':{'properties':{'target':{'const':'assigned'}}},'then':{'properties':{'owner_ref':s()}}},{'if':{'properties':{'target':{'const':'completed'}}},'then':{'properties':{'completion_ref':s()}}}]
    define('CarePlanInput',{'case_revision':ref('Revision'),'treatment_option_ids':arr(ref('UUID')),'followup_task_ids':arr(ref('UUID')),'reason':s()})
    resource('CarePlan',g['D']['CarePlanInput']['properties']|{'case_id':ref('UUID'),'status':enum('active','superseded','closed')})
    define('CarePlanRevision',{'replacement':ref('CarePlanInput'),'status':enum('active','superseded','closed'),'reason':s()})
    define('ResultItem',{'external_item_id':s(),'replaces_id':nullable(ref('UUID')),'observation':ref('RecordObservation')})
    define('ResultBatchInput',{'case_revision':ref('Revision'),'owner':s(),'report_id':s(),'report_version':s(),'digest':ref('Digest'),'items':arr(ref('ResultItem'))})
    resource('ResultReceipt',{'case_id':ref('UUID'),'case_revision':ref('Revision'),'owner':s(),'report_id':s(),'report_version':s(),'digest':ref('Digest'),'status':enum('accepted','quarantined'),'observation_ids':arr(ref('UUID')),'reason_codes':arr(s())})
    define('ImportIssue',{'record_ref':s(),'code':s(),'severity':enum('warning','error'),'detail':s()})
    resource('ImportReport',{'source_id':ref('UUID'),'operation_id':ref('UUID'),'status':enum('completed','quarantined','failed','cancelled'),'read_count':{'type':'integer','minimum':0},'normalized_count':{'type':'integer','minimum':0},'rejected_count':{'type':'integer','minimum':0},'issues':arr(ref('ImportIssue')),'artifact_ref':nullable(ref('ArtifactRef'))})
    define('OptimizationPolicy',{'id':s(),'version':s(),'digest':ref('Digest'),'scope':ref('Scope'),'method':enum('expected_utility','pareto','lexicographic'),'utility_model_ref':nullable(ref('ArtifactRef')),'constraint_set_ref':ref('ArtifactRef'),'objective_refs':arr(ref('ArtifactRef')),'tie_break':enum('eligible_at_then_id'),'qualification_refs':arr(ref('ArtifactRef'))})
    define('CriterionEstimate',{'criterion_ref':ref('ArtifactRef'),'state':enum('known','unknown','not_applicable'),'value':nullable({'type':'number'}),'unit':s(),'source_refs':arr(ref('ArtifactRef'))})
    g['D']['CriterionEstimate']['allOf']=[{'if':{'properties':{'state':{'const':'known'}}},'then':{'properties':{'value':{'type':'number'}}}},{'if':{'properties':{'state':{'enum':['unknown','not_applicable']}}},'then':{'properties':{'value':{'type':'null'}}}}]
    define('StrategyEstimate',{'strategy_ref':ref('ArtifactRef'),'admissible':{'type':'boolean'},'reason_codes':arr(s()),'criteria':arr(ref('CriterionEstimate')),'dominated_by':arr(ref('ArtifactRef'))})
    g['D']['Plan']['properties'].update({'comparisons':arr(ref('StrategyEstimate')),'cost_snapshot_refs':arr(ref('ArtifactRef')),'computed_at':ref('Timestamp'),'valid_until':ref('Timestamp')})
    # Champs optionnels pour compatibilité avec le noyau ; requis sémantiquement
    # lorsqu'une comparaison économique est effectivement calculée.
    g['D']['OptimizationPolicy']['allOf']=[{'if':{'properties':{'method':{'const':'expected_utility'}}},'then':{'properties':{'utility_model_ref':ref('ArtifactRef')}}}]

def extend_api(g):
    ep,page,paths=g['endpoint'],g['page'],g['paths']
    for route,name,perm in [('sites','Site','resources:admin'),('managed-resources','ManagedResource','resources:admin'),('procedure-catalog','ProcedureEntry','knowledge:author')]:
        readperm='resources:read' if name!='ProcedureEntry' else 'knowledge:read'
        ep('/'+route,'get','list'+name,'Lister le catalogue versionné',page(name),permission=readperm)
        ep('/'+route,'post','create'+name,'Créer entrée de catalogue',name,name+'Input',perm)
        ep('/'+route+'/{item_id}','get','get'+name,'Lire entrée de catalogue',name,permission=readperm)
        ep('/'+route+'/{item_id}/revisions','post','revise'+name,'Réviser avec analyse d’impact',name,name+'Revision',perm,match=True)
    ep('/resource-capabilities/{capability_id}','get','getResourceCapability','Lire une capacité','ResourceCapability',permission='resources:read')
    ep('/resource-capabilities/{capability_id}/revisions','post','reviseResourceCapability','Réviser sans effacer les réservations','ResourceCapability','CapabilityRevision','resources:admin',match=True)
    ep('/cost-quotes','get','listCostQuotes','Lister prix contextualisés',page('CostQuote'),permission='resources:read')
    ep('/workflows','post','createWorkflow','Créer parcours durable','WorkflowRun','WorkflowInput','workflows:create')
    ep('/workflows/{workflow_id}','get','getWorkflow','Lire progression et blocages','WorkflowRun',permission='cases:read')
    ep('/workflows/{workflow_id}/transitions','post','transitionWorkflow','Commander une transition gardée','WorkflowRun','WorkflowTransition','workflows:control',match=True)
    ep('/cases/{case_id}/workflows','get','listCaseWorkflows','Lister parcours du cas',page('WorkflowRun'),permission='cases:read')
    ep('/cases/{case_id}/result-batches','post','receiveResultBatch','Recevoir atomiquement un rapport','ResultReceipt','ResultBatchInput','results:ingest',match=True)
    ep('/followups','post','createFollowUp','Créer tâche de suivi','FollowUpTask','FollowUpInput','followups:create')
    ep('/followups/{task_id}','get','getFollowUp','Lire tâche et propriétaire','FollowUpTask',permission='cases:read')
    ep('/followups/{task_id}/transitions','post','transitionFollowUp','Attribuer ou clôturer suivi','FollowUpTask','FollowUpTransition','followups:manage',match=True)
    ep('/cases/{case_id}/followups','get','listCaseFollowUps','Lister tâches du cas',page('FollowUpTask'),permission='cases:read')
    ep('/cases/{case_id}/care-plans','post','createCarePlan','Créer plan sans prescrire','CarePlan','CarePlanInput','careplans:write',match=True)
    ep('/cases/{case_id}/care-plans','get','listCaseCarePlans','Lister plans de soins',page('CarePlan'),permission='cases:read')
    ep('/care-plans/{plan_id}','get','getCarePlan','Lire plan de soins','CarePlan',permission='cases:read')
    ep('/care-plans/{plan_id}/revisions','post','reviseCarePlan','Réviser plan et suivi','CarePlan','CarePlanRevision','careplans:write',match=True)
    ep('/imports/{operation_id}/report','get','getImportReport','Lire rapport de normalisation','ImportReport',permission='knowledge:author')
    ep('/sources','get','listSources','Lister sources et droits',page('Source'),permission='knowledge:read')
    ep('/sources/{source_id}','get','getSource','Lire source et droits','Source',permission='knowledge:read')
    ep('/contributions','get','listContributions','Lister propositions accessibles',page('Contribution'),permission='contributions:read')
    ep('/knowledge/optimization-policies','get','listOptimizationPolicies','Lister politiques admissibles',page('OptimizationPolicy'),permission='knowledge:read')
    # Les filtres ont une sémantique de conjonction, incluse dans le curseur signé.
    for route,method,filters in [('/cost-quotes','get',['capability_id']),('/managed-resources','get',['site_id']),('/procedure-catalog','get',['q','family']),('/knowledge/assertions','get',['subject_code','predicate','object_code','release_id']),('/knowledge/models','get',['release_id','population_id']),('/knowledge/protocols','get',['release_id']),('/knowledge/evidence','get',['subject_code','release_id'])]:
        for name in filters:
            paths[route][method]['parameters'].append({'name':name,'in':'query','schema':g['s'](),'description':'Filtre exact sauf q (recherche textuelle) ; codes qualifiés system|code.'})

def extend_examples(g):
    E,B,U,T,A,C=g['examples'],g['B'],g['U'],g['T'],g['A'],g['C']
    E['workflow']=('WorkflowRun',B(30)|{'case_id':U(2),'case_revision':1,'protocol_ref':A('synthetic-protocol'),'authorization_policy_ref':A('engineering-only'),'intended_use':'engineering','status':'waiting_input','current_step_ids':['ask-1'],'reason_codes':['missing_input']})
    E['followup']=('FollowUpTask',B(31)|{'case_id':U(2),'origin_ref':'synthetic:plan/1','owner_ref':None,'due_at':'2026-09-23T12:00:00Z','reason':'Suivi fictif non attribué','status':'open','completion_ref':None})
    E['procedure']=('ProcedureEntry',B(32)|{'concept':C('SYN-T1'),'family':'synthetic','specimen_refs':[],'component_refs':[],'detail_refs':[A('synthetic-procedure')],'status':'draft'})
    E['result-batch']=('ResultBatchInput',{'case_revision':1,'owner':'synthetic-lab','report_id':'synthetic-report','report_version':'1','digest':g['H'],'items':[{'external_item_id':'result-1','replaces_id':None,'observation':{k:v for k,v in g['observation'].items() if k in g['D']['RecordObservation']['properties']}}]})
