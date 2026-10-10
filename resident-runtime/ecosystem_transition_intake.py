#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path

OPERATION="ORGANIZATION_RECORD_ORGANIZATION_TRANSITION"
# MASTER-RECORDS-BULK-SEMANTIC-REMEDIATION-002: operation value before the
# custody -> organization record rename; still accepted on read, never written.
LEGACY_CUSTODY_OPERATION="CUSTODY_ORGANIZATION_TRANSITION"
DESTINATION_SERVICE="organization.ecosystem-transition-ledger"
# MASTER-RECORDS-BULK-SEMANTIC-REMEDIATION-002: destination service before the
# Master Records -> Organization rename; still accepted on read, never written.
LEGACY_DESTINATION_SERVICE="master-records.ecosystem-transition-ledger"

ORGANIZATION_RECEIPT_SCHEMA="stegverse.organization-transition-receipt/v1"

def load(p): return json.loads(Path(p).read_text())

def receipt_digest(receipt):
    body=dict(receipt); body.pop("receipt_sha256",None)
    return "sha256:"+hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def verify_release_predecessor(request):
    """The release predecessor is a verified organization receipt-chain segment.

    `organization_receipt` is the segment head; optional `organization_receipt_segment`
    lists the receipts preceding it, oldest first. Master Records only checks the
    segment; it does not create, admit, authorize, infer or repair any transition.
    """
    head=request.get("organization_receipt")
    if not isinstance(head,dict): raise RuntimeError("organization receipt missing")
    prior=request.get("organization_receipt_segment") or []
    if not isinstance(prior,list): raise RuntimeError("organization receipt-chain segment invalid")
    segment=[*prior,head]; organization=None; previous=None
    for index,receipt in enumerate(segment):
        if not isinstance(receipt,dict) or receipt.get("schema")!=ORGANIZATION_RECEIPT_SCHEMA: raise RuntimeError("organization receipt schema mismatch")
        if receipt.get("receipt_sha256")!=receipt_digest(receipt): raise RuntimeError("organization receipt hash mismatch")
        if organization is None: organization=receipt.get("organization")
        if not organization or receipt.get("organization")!=organization: raise RuntimeError("organization receipt-chain segment owner mismatch")
        if index and receipt.get("previous_receipt_sha256")!=previous: raise RuntimeError("organization receipt-chain segment linkage broken")
        previous=receipt["receipt_sha256"]
    return {"organization":organization,"segment_length":len(segment),"segment_head_sha256":previous,
            "segment_base_previous_receipt_sha256":segment[0].get("previous_receipt_sha256")}

def orchestration_roots():
    out=[]
    if os.getenv("MASTER_RECORDS_ORCHESTRATION_ROOT"):
        out.append(Path(os.environ["MASTER_RECORDS_ORCHESTRATION_ROOT"]).expanduser())
    home=Path(os.getenv("HOME",str(Path.home())))
    out.extend([
      home/".stegverse"/"repos"/"master-records"/"orchestration",
      Path("/var/lib/stegverse/source/master-records/orchestration"),
      Path("/srv/stegverse/repos/master-records/orchestration"),
      Path("/opt/stegverse/repos/master-records/orchestration")
    ])
    return [p.resolve() for p in out]

def resolve_orchestration():
    for root in orchestration_roots():
        if (root/"services/ecosystem_transition_ledger.py").is_file() and (root/".stegverse/transition-ledger/ecosystem-contract.json").is_file():
            return root
    raise RuntimeError("master-records/orchestration source not materialized")

def run(ingress:Path):
    env=load(ingress)
    if (env.get("destination") or {}).get("org")!="master-records": raise RuntimeError("wrong destination organization")
    if (env.get("destination") or {}).get("service") not in (DESTINATION_SERVICE,LEGACY_DESTINATION_SERVICE): raise RuntimeError("wrong destination service")
    payload=env.get("payload") or {}
    request=payload.get("request") if isinstance(payload.get("request"),dict) else payload
    if request.get("operation") not in (OPERATION,LEGACY_CUSTODY_OPERATION): raise RuntimeError("operation mismatch")
    if request.get("authority_transfer",False) is not False: raise RuntimeError("authority transfer prohibited")
    release_predecessor=verify_release_predecessor(request)
    org_receipt=request["organization_receipt"]
    pre=request.get("predecessor_ecosystem_state_sha256")
    post=request.get("successor_ecosystem_state_sha256")
    if not pre or not post: raise RuntimeError("ecosystem state hashes required")
    root=resolve_orchestration()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); rp=td/"org-receipt.json"; rp.write_text(json.dumps(org_receipt,indent=2,sort_keys=True)+"\n")
        cmd=["python3",str(root/"services/ecosystem_transition_ledger.py"),"--org-receipt",str(rp),"--predecessor-ecosystem-state-sha256",str(pre),"--successor-ecosystem-state-sha256",str(post),"--relation-evidence-json",json.dumps(request.get("relation_evidence") or {},sort_keys=True)]
        done=subprocess.run(cmd,cwd=root,capture_output=True,text=True,check=False)
        if done.returncode!=0: raise RuntimeError("organization transition ledger recording failed:"+done.stderr[-512:])
        record=None
        for line in reversed(done.stdout.splitlines()):
            try:
                v=json.loads(line)
                if isinstance(v,dict): record=v; break
            except Exception: pass
        if not record: raise RuntimeError("organization transition ledger receipt missing")
    return {"schema":"master-records.ecosystem-transition-intake/v1","state":"RECORDED","record_receipt":record,"release_predecessor":release_predecessor,"authority_effect":"NONE_ORGANIZATION_RECORD_ONLY","authority_transfer":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--ingress",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    try: result=run(a.ingress.resolve()); code=0
    except Exception as exc:
        result={"schema":"master-records.ecosystem-transition-intake/v1","state":"BLOCKED","reason":str(exc),"authority_effect":"NONE_BLOCKED","authority_transfer":False};code=2
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,sort_keys=True));raise SystemExit(code)
if __name__=="__main__":main()
