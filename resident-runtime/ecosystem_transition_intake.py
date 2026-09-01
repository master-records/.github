#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess,tempfile
from pathlib import Path

def load(p): return json.loads(Path(p).read_text())

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
    if (env.get("destination") or {}).get("service")!="master-records.ecosystem-transition-ledger": raise RuntimeError("wrong destination service")
    payload=env.get("payload") or {}
    request=payload.get("request") if isinstance(payload.get("request"),dict) else payload
    if request.get("operation")!="CUSTODY_ORGANIZATION_TRANSITION": raise RuntimeError("operation mismatch")
    if request.get("authority_transfer",False) is not False: raise RuntimeError("authority transfer prohibited")
    org_receipt=request.get("organization_receipt")
    if not isinstance(org_receipt,dict): raise RuntimeError("organization receipt missing")
    pre=request.get("predecessor_ecosystem_state_sha256")
    post=request.get("successor_ecosystem_state_sha256")
    if not pre or not post: raise RuntimeError("ecosystem state hashes required")
    root=resolve_orchestration()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); rp=td/"org-receipt.json"; rp.write_text(json.dumps(org_receipt,indent=2,sort_keys=True)+"\n")
        cmd=["python3",str(root/"services/ecosystem_transition_ledger.py"),"--org-receipt",str(rp),"--predecessor-ecosystem-state-sha256",str(pre),"--successor-ecosystem-state-sha256",str(post),"--relation-evidence-json",json.dumps(request.get("relation_evidence") or {},sort_keys=True)]
        done=subprocess.run(cmd,cwd=root,capture_output=True,text=True,check=False)
        if done.returncode!=0: raise RuntimeError("ecosystem custody failed:"+done.stderr[-512:])
        record=None
        for line in reversed(done.stdout.splitlines()):
            try:
                v=json.loads(line)
                if isinstance(v,dict): record=v; break
            except Exception: pass
        if not record: raise RuntimeError("ecosystem custody receipt missing")
    return {"schema":"master-records.ecosystem-transition-intake/v1","state":"RECORDED","custody_receipt":record,"authority_effect":"NONE_CUSTODY_ONLY","authority_transfer":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--ingress",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    try: result=run(a.ingress.resolve()); code=0
    except Exception as exc:
        result={"schema":"master-records.ecosystem-transition-intake/v1","state":"BLOCKED","reason":str(exc),"authority_effect":"NONE_BLOCKED","authority_transfer":False};code=2
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,sort_keys=True));raise SystemExit(code)
if __name__=="__main__":main()
