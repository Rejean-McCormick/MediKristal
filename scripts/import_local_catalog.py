#!/usr/bin/env python3
"""Two-phase validator for the MediKristal-owned local catalog CSV profile.

This script intentionally does not mutate the database. `preview` emits a canonical diff
and digest. `confirm` checks that the same file still yields the supplied digest. A future
transport/API can persist the confirmed diff without changing the parsing contract.
"""
from __future__ import annotations

import argparse, csv, hashlib, json
from pathlib import Path

CAPABILITY_COLUMNS = ["site_external_id","procedure_system","procedure_code","procedure_version","resource_external_id","duration_minutes","capacity"]
PRICE_COLUMNS = ["capability_external_id","amount_minor","currency","kind","perspective","valid_from","valid_until"]


def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def digest(value): return "sha256:"+hashlib.sha256(canonical(value)).hexdigest()

def read_csv(path: Path, required: list[str]) -> dict:
    with path.open(encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        missing=[c for c in required if c not in (reader.fieldnames or [])]
        if missing: return {"status":"quarantined","rows":[],"issues":[{"code":"import_schema_mismatch","missing":missing}]}
        rows=[]; issues=[]
        for i,row in enumerate(reader,start=2):
            try:
                normalized={k:row.get(k,"") for k in required}
                if "duration_minutes" in normalized:
                    normalized["duration_minutes"]=int(normalized["duration_minutes"]); normalized["capacity"]=int(normalized["capacity"])
                    if normalized["duration_minutes"]<=0 or normalized["capacity"]<=0: raise ValueError("invalid capacity")
                if "amount_minor" in normalized:
                    normalized["amount_minor"]=int(normalized["amount_minor"])
                    if normalized["amount_minor"]<0 or len(normalized["currency"])!=3: raise ValueError("invalid money")
                rows.append(normalized)
            except Exception as e:
                issues.append({"record_ref":str(i),"code":"invalid_record","detail":str(e)})
        return {"status":"preview","rows":rows,"issues":issues,"extra_columns":[c for c in (reader.fieldnames or []) if c not in required]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("kind",choices=["capabilities","prices"]); p.add_argument("file",type=Path); p.add_argument("--confirm-digest"); args=p.parse_args()
    required=CAPABILITY_COLUMNS if args.kind=="capabilities" else PRICE_COLUMNS
    result=read_csv(args.file,required); result["profile"]="medikristal-local-catalog/1"; result["kind"]=args.kind
    result["diff_digest"]=digest({"profile":result["profile"],"kind":args.kind,"rows":result["rows"],"issues":result["issues"]})
    if args.confirm_digest:
        result["confirmed"] = result["status"]=="preview" and result["diff_digest"]==args.confirm_digest and not result["issues"]
        if not result["confirmed"]: result["status"]="quarantined"
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
