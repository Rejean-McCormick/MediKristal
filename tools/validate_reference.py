"""Validation documentaire sans dépendance.

Valide seulement les mots-clés JSON Schema effectivement émis par build_contracts.py.
Ce n'est ni un validateur général Draft 2020-12 ni une preuve OpenAPI/FHIR/Kristal.
L'implémentation applicative devra employer des validateurs standards complets.
"""
import copy
import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
schema=json.loads((ROOT/'contracts/domain.schema.json').read_text())
api=json.loads((ROOT/'contracts/openapi.json').read_text())
checks=[]
def check(name, condition, detail=''):
    checks.append({'name':name,'status':'PASS' if condition else 'FAIL','detail':detail})

def resolve(pointer,root):
    assert pointer.startswith('#/'),pointer
    cur=root
    for part in pointer[2:].split('/'):
        cur=cur[part.replace('~1','/').replace('~0','~')]
    return cur

def validate(value, spec, path='$'):
    errors=[]
    if '$ref' in spec:
        errors.extend(validate(value,resolve(spec['$ref'],schema),path))
    if 'const' in spec and value!=spec['const']:errors.append(path+':const')
    if 'enum' in spec and value not in spec['enum']:errors.append(path+':enum')
    t=spec.get('type')
    kinds={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),'number':lambda x:isinstance(x,(int,float)) and not isinstance(x,bool),'integer':lambda x:isinstance(x,int) and not isinstance(x,bool),'boolean':lambda x:isinstance(x,bool),'null':lambda x:x is None}
    if t and not kinds[t](value):return errors+[path+':type '+t]
    if isinstance(value,dict):
        for k in spec.get('required',[]):
            if k not in value:errors.append(path+':missing '+k)
        props=spec.get('properties',{})
        if spec.get('additionalProperties') is False:
            for k in value.keys()-props.keys():errors.append(path+':unexpected '+k)
        for k,v in value.items():
            if k in props:errors.extend(validate(v,props[k],path+'.'+k))
    if isinstance(value,list) and 'items' in spec:
        for i,v in enumerate(value):errors.extend(validate(v,spec['items'],path+f'[{i}]'))
    if isinstance(value,str):
        if len(value)<spec.get('minLength',0):errors.append(path+':minLength')
        if 'pattern' in spec and re.search(spec['pattern'],value) is None:errors.append(path+':pattern')
        fmt=spec.get('format')
        try:
            if fmt=='uuid':uuid.UUID(value)
            if fmt=='date-time':
                dt=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
                if dt.tzinfo is None or 'T' not in value:raise ValueError()
            if fmt=='uri' and not re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',value):raise ValueError()
        except ValueError:errors.append(path+':format '+fmt)
    if isinstance(value,(float,int)) and not isinstance(value,bool):
        if 'minimum' in spec and value<spec['minimum']:errors.append(path+':minimum')
        if 'maximum' in spec and value>spec['maximum']:errors.append(path+':maximum')
        if 'exclusiveMinimum' in spec and value<=spec['exclusiveMinimum']:errors.append(path+':exclusiveMinimum')
    for branch in spec.get('allOf',[]):errors.extend(validate(value,branch,path))
    for keyword in ['anyOf','oneOf']:
        if keyword in spec:
            count=sum(not validate(value,b,path) for b in spec[keyword])
            if (keyword=='anyOf' and count==0) or (keyword=='oneOf' and count!=1):errors.append(path+':'+keyword)
    if 'if' in spec and not validate(value,spec['if'],path):errors.extend(validate(value,spec.get('then',{}),path))
    return errors

# Inventaire syntaxique et références.
for p in ROOT.rglob('*.json'):
    if p.name not in ['validation-report.json','manifest.json']:
        try:json.loads(p.read_text());check('json:'+str(p.relative_to(ROOT)),True)
        except Exception as e:check('json:'+str(p.relative_to(ROOT)),False,str(e))
def walk(v):
    if isinstance(v,dict):
        yield v
        for child in v.values():yield from walk(child)
    if isinstance(v,list):
        for child in v:yield from walk(child)
for node in walk(schema):
    if '$ref' in node:
        try:resolve(node['$ref'],schema)
        except Exception:check('schema-ref:'+node['$ref'],False)
check('schema local references',not any(c['status']=='FAIL' and c['name'].startswith('schema-ref:') for c in checks))
for node in walk(api):
    if '$ref' in node:
        pointer=node['$ref']
        try:
            if pointer.startswith('#/'):resolve(pointer,api)
            elif pointer.startswith('./domain.schema.json#'):resolve('#'+pointer.split('#',1)[1],schema)
            else:raise ValueError(pointer)
        except Exception:check('api-ref:'+pointer,False)
check('api references',not any(c['status']=='FAIL' and c['name'].startswith('api-ref:') for c in checks))
ids=[]
for path,methods in api['paths'].items():
    for method,operation in methods.items():
        ids.append(operation['operationId'])
        expected=set(re.findall(r'{([^}]+)}',path))
        actual={x['name'] for x in operation['parameters'] if x['in']=='path' and x.get('required')}
        check('path-parameters:'+operation['operationId'],expected==actual)
        if method=='post':check('idempotency:'+operation['operationId'],any(x['name']=='Idempotency-Key' and x['required'] for x in operation['parameters']))
check('unique operation IDs',len(set(ids))==len(ids))
check('OpenAPI version',api['openapi']=='3.1.0')

index=json.loads((ROOT/'examples/index.json').read_text())
loaded={}
for entry in index:
    value=json.loads((ROOT/'examples'/entry['file']).read_text())
    loaded[entry['schema']]=value
    errors=validate(value,schema['$defs'][entry['schema']])
    check('example:'+entry['file'],not errors,'; '.join(errors))

neg=[]
x=copy.deepcopy(loaded['Evaluation']);x['hypotheses'][0]['probability']=1.2;neg.append(('probability-range','Evaluation',x))
x=copy.deepcopy(loaded['Evaluation']);x['hypotheses'][0]['kind']='score';neg.append(('score-not-probability','Evaluation',x))
x=copy.deepcopy(loaded['Observation']);x['presence']='unknown';neg.append(('unknown-no-value','Observation',x))
x=copy.deepcopy(loaded['ClinicalCase']);x['fake_validated']=True;neg.append(('unexpected-field','ClinicalCase',x))
x=copy.deepcopy(loaded['CostQuote']);x['amount_minor']=-1;neg.append(('negative-cost','CostQuote',x))
x=copy.deepcopy(loaded['ClinicalCase']);x['id']='not-a-uuid';neg.append(('invalid-uuid','ClinicalCase',x))
for name,typ,x in neg:check('negative:'+name,bool(validate(x,schema['$defs'][typ])))

# Vérifications sémantiques documentaires choisies, pas moteur clinique.
positive=(0.1*0.8)/(0.1*0.8+0.9*0.1)
negative=(0.1*0.2)/(0.1*0.2+0.9*0.9)
check('synthetic posterior positive',abs(positive-loaded['Evaluation']['hypotheses'][0]['probability'])<1e-12)
check('synthetic posterior negative',abs(negative-0.024096385542168676)<1e-12)
check('synthetic namespace',all(c.get('system')=='urn:medikristal:synthetic' for v in loaded.values() for c in walk(v) if 'system' in c and 'code' in c))

bad_links=[]
for file in ROOT.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
        if '://' in target or target.startswith(('#','mailto:')):continue
        dest=target.split('#')[0]
        if dest and not (file.parent/dest).exists():bad_links.append(str(file.relative_to(ROOT))+':'+target)
check('local Markdown links',not bad_links,'; '.join(bad_links))
vision=(ROOT/'docs/01-vision.md').read_text()
tests=(ROOT/'docs/18-tests.md').read_text()
required=set(re.findall(r'MK-\d{3}',vision))
# Les tables emploient parfois MK-001,002 : développer ce raccourci.
covered=set()
for group in re.findall(r'MK-\d{3}(?:,\d{3})*',tests):
    covered.update('MK-'+part.replace('MK-','') for part in group.split(','))
check('requirements test mapping',required<=covered,','.join(sorted(required-covered)))
check('33 chapters',len(list((ROOT/'docs').glob('[0-9][0-9]-*.md')))==33)
# Couverture documentaire : références vérifiables, pas exécution de l'application.
trace=json.loads((ROOT/'contracts/traceability.json').read_text())['entries']
trace_ids=[r['requirement'] for r in trace]
check('traceability exact requirement coverage',set(trace_ids)==required and len(trace_ids)==len(set(trace_ids)))
acceptance=(ROOT/'docs/33-acceptance.md').read_text()
for row in trace:
    problems=[]
    if any(not (ROOT/p).exists() for p in row['chapters']):problems.append('chapter')
    if any(t not in schema['$defs'] for t in row['schemas']):problems.append('schema')
    if any(o not in ids for o in row['operations']):problems.append('operation')
    if any(t not in acceptance for t in row['acceptance_tests']):problems.append('test')
    if not row['interface'] or not row['event']:problems.append('interface/event')
    if not re.fullmatch(r'L(?:[0-9]|1[0-3])',row['delivery_lot']):problems.append('lot')
    if row['status']!='specified':problems.append('unsupported maturity claim')
    check('traceability:'+row['requirement'],not problems,','.join(problems))
check('API version consistent',api['info']['version']==schema['$defs']['Capabilities']['properties']['api_version']['const'])
check('permissions all operations',all(op.get('x-permission') and op.get('security') for methods in api['paths'].values() for op in methods.values()))
check('revision mutation guards',all(any(p['name']=='If-Match' and p.get('required') for p in op['parameters']) for path,methods in api['paths'].items() for method,op in methods.items() if method=='post' and (path.endswith('/revisions') or path.endswith('/transitions'))))
extra_neg=[
 ('assigned-owner-required','FollowUpTransition',{'target':'assigned','owner_ref':None,'completion_ref':None,'reason':'synthetic'}),
 ('completed-proof-required','FollowUpTransition',{'target':'completed','owner_ref':None,'completion_ref':None,'reason':'synthetic'}),
 ('unknown-criterion-not-zero','CriterionEstimate',{'criterion_ref':{'id':'synthetic','version':'1','digest':'sha256:'+'a'*64},'state':'unknown','value':0,'unit':'synthetic','source_refs':[]})
]
for name,typ,value in extra_neg:check('negative:'+name,bool(validate(value,schema['$defs'][typ])))
check('synthetic conditional strategy cost',20+0.30*500==170)

report={'scope':'Validation documentaire et sous-ensemble de schéma généré ; pas validation complète OpenAPI/JSON Schema externe, pas test applicatif ou clinique.','checks':checks,'counts':{'pass':sum(c['status']=='PASS' for c in checks),'fail':sum(c['status']=='FAIL' for c in checks),'schemas':len(schema['$defs']),'operations':len(ids),'examples':len(index),'chapters':len(list((ROOT/'docs').glob('[0-9][0-9]-*.md')))}}
(ROOT/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
md=['# Rapport de validation documentaire','',report['scope'],'',f"Résultat : {report['counts']['pass']} PASS ; {report['counts']['fail']} FAIL.",'','| Vérification | Résultat | Détail |','|---|---|---|']
md.extend(f"| {c['name']} | {c['status']} | {c['detail'].replace('|','/')} |" for c in checks)
md.extend(['','Ce validateur contrôle la spécification et les contrats ; il n’exécute pas la suite applicative. Les preuves logicielles exécutées sont consignées dans `APP_VALIDATION.md`. Les hashes des exemples sont des placeholders. La qualification native Kristal/FHIR, la compilation CQL et toute validation clinique restent hors de la portée de ce contrôle documentaire.'])
(ROOT/'VALIDATION.md').write_text('\n'.join(md)+'\n')
print(json.dumps(report['counts']))
raise SystemExit(bool(report['counts']['fail']))
