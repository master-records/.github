#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

KINDS=["INGRESS_ACCEPTED","DISPATCHED","CONSUMED","RESULT_BOUND","EGRESS_EMITTED"]

def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",",":")).encode()

def hid(prefix, v):
    return prefix+"-"+hashlib.sha256(canon(v)).hexdigest()[:24]

def load(path):
    return json.loads(Path(path).read_text())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--envelope",required=True)
    ap.add_argument("--registry",default="org-boundary/registry/services.json")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    env=load(args.envelope); reg=load(args.registry)
    required=["schema_version","packet_id","direction","origin","destination","carrier","intr_profile","transition","payload","evidence"]
    missing=[k for k in required if k not in env]
    if missing: raise SystemExit("missing:"+",".join(missing))
    if env["destination"]["org"]!=reg["organization"]: raise SystemExit("wrong-destination-org")
    svc=next((s for s in reg["services"] if s["service_id"]==env["destination"]["service"]),None)
    if not svc: raise SystemExit("unknown-service")
    if svc["boundary_role"]!="BOUNDARY_LOCAL_DIAGNOSTIC": raise SystemExit("endpoint-adapter-not-installed")
    if env["transition"]["authority_effect"] not in ["NONE","ADMIT","DENY","DEFER","CONDITIONAL"]: raise SystemExit("bad-authority-effect")
    base={"packet_id":env["packet_id"],"service_id":svc["service_id"],"payload_hash":hashlib.sha256(canon(env["payload"])).hexdigest()}
    receipts=[]; prev=None
    for kind in KINDS:
        subject={**base,"kind":kind,"previous_receipt_id":prev}
        rid=hid(kind.lower(),subject)
        receipts.append({"kind":kind,"receipt_id":rid,"subject":svc["service_id"],"evidence_hash":hashlib.sha256(canon(subject)).hexdigest(),"previous_receipt_id":prev})
        prev=rid
    result={
      "schema_version":reg["organization"].lower().replace(" ","-")+".boundary-execution.v1",
      "packet_id":env["packet_id"],
      "organization":reg["organization"],
      "service_id":svc["service_id"],
      "consumed":True,
      "application_result":{"echo":env["payload"]},
      "authority_effect":env["transition"]["authority_effect"],
      "receipts":receipts,
      "reconstruction":{"same_execution_required":True,"status":"RECONSTRUCTED","terminal_receipt_id":prev}
    }
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PASS","out":args.out,"terminal_receipt_id":prev}))

if __name__=="__main__": main()
