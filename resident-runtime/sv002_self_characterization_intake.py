#!/usr/bin/env python3
"""Master Records intake for the canonical SV002 self-characterization artifact set."""
from __future__ import annotations

import argparse, base64, hashlib, json, os, subprocess, tempfile
from pathlib import Path
from typing import Any

EXPERIMENT_ID="STEGVERSE-002-SELF-CHARACTERIZATION-001"
SERVICE_ID="master-records.sv002-self-characterization-reconstruction"
REQUIRED=(
    "S0.json",
    "EXPERIMENT_EXECUTION_RECEIPT.json",
    "SELF_CHARACTERIZATION.md",
    "SELF_CHARACTERIZATION_FORMAL.json",
    "INTERACTION_RECEIPT_CHAIN.json",
    "TRANSITION_EFFECTS.json",
    "TRANSITION_RECEIPTS.json",
    "TRANSITION_RECEIPTS.live.jsonl",
    "ORG_BOUNDARY_RECEIPTS.json",
    "ORG_BOUNDARY_RECEIPTS.live.jsonl",
    "REPOSITORY_LEDGER_ROOT.json",
    "ORGANIZATION_LEDGER_ROOT.json",
)
MAX_TOTAL_BYTES=16*1024*1024
ORGANIZATION_RECORD_ROOT_ENV="STEGVERSE_MASTER_RECORDS_SV002_ORGANIZATION_RECORD_ROOT"
ORGANIZATION_RECORD_MANIFEST="MASTER_RECORDS_ORGANIZATION_RECORD_MANIFEST.json"
OPERATION="ORGANIZATION_RECORD_SV002_SELF_CHARACTERIZATION"
MANIFEST_SCHEMA="master-records.sv002-organization-record-manifest/v1"
INTAKE_SCHEMA="master-records.sv002-self-characterization-organization-record-intake/v1"
AUTHORITY_EFFECT="NONE_ORGANIZATION_RECORD_ONLY"
# Pre-rename names, still accepted on read; never written.
# MASTER-RECORDS-BULK-SEMANTIC-REMEDIATION-002: identifier values before the
# custody -> organization record rename.
LEGACY_MASTER_RECORDS_CUSTODY={
    "root_env":"STEGVERSE_MASTER_RECORDS_SV002_CUSTODY_ROOT",
    "manifest":"MASTER_RECORDS_CUSTODY_MANIFEST.json",
    "operation":"CUSTODY_SV002_SELF_CHARACTERIZATION",
    "manifest_schema":"master-records.sv002-custody-manifest/v1",
    "authority_effect":"NONE_CUSTODY_ONLY",
}
MANIFEST_BINDING=("experiment_id","run_id","artifact_set_sha256","organization_ledger_root_hash")
RECONSTRUCTION_RECEIPT="STEGVERSE_002_SELF_CHARACTERIZATION_RECONSTRUCTION_RECEIPT.json"

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def sha256_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise RuntimeError(f"expected object:{path}")
    return v

def organization_record_base()->Path:
    override=os.getenv(ORGANIZATION_RECORD_ROOT_ENV) or os.getenv(LEGACY_MASTER_RECORDS_CUSTODY["root_env"])
    if override: return Path(override).expanduser().resolve()
    base=Path(os.getenv("XDG_STATE_HOME",str(Path.home()/".local/state")))
    return (base/"stegverse/master-records/sv002-self-characterization").resolve()

def orchestration_roots()->list[Path]:
    out=[]
    for key in ("MASTER_RECORDS_ORCHESTRATION_ROOT","STEGVERSE_MASTER_RECORDS_ORCHESTRATION_ROOT"):
        if os.getenv(key): out.append(Path(os.environ[key]).expanduser())
    home=Path(os.getenv("HOME",str(Path.home())))
    out.extend([
        home/".stegverse/repos/master-records/orchestration",
        Path("/var/lib/stegverse/source/master-records/orchestration"),
        Path("/srv/stegverse/repos/master-records/orchestration"),
        Path("/opt/stegverse/repos/master-records/orchestration"),
    ])
    return [p.resolve() for p in out]

def resolve_orchestration()->Path:
    for root in orchestration_roots():
        if (root/"scripts/verify_sv002_self_characterization_reconstruction.py").is_file():
            return root
    raise RuntimeError("master-records/orchestration source not materialized")

def verify_artifacts(request:dict[str,Any])->tuple[dict[str,bytes],list[dict[str,Any]],str,str]:
    if request.get("experiment_id")!=EXPERIMENT_ID: raise RuntimeError("experiment_id mismatch")
    run_id=str(request.get("run_id") or "")
    if not run_id.startswith("SV002-RUN-"): raise RuntimeError("run_id invalid")
    rows=request.get("artifacts")
    if not isinstance(rows,list): raise RuntimeError("artifacts list required")
    by_name={row.get("name"):row for row in rows if isinstance(row,dict)}
    if sorted(by_name)!=sorted(REQUIRED): raise RuntimeError("canonical artifact set mismatch")
    meta=[]; decoded={}; total=0
    for name in REQUIRED:
        row=by_name[name]
        try: raw=base64.b64decode(str(row.get("base64") or ""),validate=True)
        except Exception as exc: raise RuntimeError(f"artifact base64 invalid:{name}") from exc
        if len(raw)!=row.get("size") or sha256_bytes(raw)!=row.get("sha256"):
            raise RuntimeError(f"artifact digest mismatch:{name}")
        total+=len(raw)
        if total>MAX_TOTAL_BYTES: raise RuntimeError("artifact set exceeds organization record intake limit")
        decoded[name]=raw
        meta.append({"name":name,"sha256":row["sha256"],"size":row["size"]})
    artifact_set_sha256=sha256_bytes(canon(meta))
    if artifact_set_sha256!=request.get("artifact_set_sha256"):
        raise RuntimeError("artifact_set_sha256 mismatch")
    try:
        s0=json.loads(decoded["S0.json"])
        execution=json.loads(decoded["EXPERIMENT_EXECUTION_RECEIPT.json"])
        org_root=json.loads(decoded["ORGANIZATION_LEDGER_ROOT.json"])
    except Exception as exc:
        raise RuntimeError("canonical JSON artifact parse failed") from exc
    if s0.get("run_id")!=run_id or execution.get("run_id")!=run_id:
        raise RuntimeError("run_id artifact binding mismatch")
    if org_root.get("root_hash")!=request.get("organization_ledger_root_hash"):
        raise RuntimeError("organization ledger root handoff binding mismatch")
    return decoded,meta,artifact_set_sha256,run_id

def build_manifest(request:dict[str,Any],meta:list[dict[str,Any]],artifact_set_sha256:str,run_id:str)->dict[str,Any]:
    return {
        "schema":MANIFEST_SCHEMA,
        "experiment_id":EXPERIMENT_ID,
        "run_id":run_id,
        "artifact_set_sha256":artifact_set_sha256,
        "organization_ledger_root_hash":request.get("organization_ledger_root_hash"),
        "artifact_count":len(meta),
        "artifacts":meta,
        "authority_effect":AUTHORITY_EFFECT,
    }

def materialize_workspace(workspace:Path,decoded:dict[str,bytes],manifest:dict[str,Any])->Path:
    """Write the artifact set into an ephemeral verification workspace.

    The artifact bytes stay in the custody of the Organization that produced them;
    Master Records keeps only the manifest and the reconstruction receipt.
    """
    workspace.mkdir(parents=True,exist_ok=True)
    for name,raw in decoded.items(): (workspace/name).write_bytes(raw)
    (workspace/ORGANIZATION_RECORD_MANIFEST).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return workspace

def record_root(run_id:str)->Path:
    # Directory name kept so records written before artifact bytes stopped being
    # retained stay at the same path; it now holds the manifest and receipt only.
    return organization_record_base()/run_id/"artifact-root"

def write_record(manifest:dict[str,Any],reconstruction:dict[str,Any]|None=None)->Path:
    root=record_root(manifest["run_id"])
    root.mkdir(parents=True,exist_ok=True)
    legacy_path=root/LEGACY_MASTER_RECORDS_CUSTODY["manifest"]
    if legacy_path.exists():
        legacy=load(legacy_path)
        if any(legacy.get(k)!=manifest[k] for k in MANIFEST_BINDING):
            raise RuntimeError("organization record manifest write-once collision")
    manifest_path=root/ORGANIZATION_RECORD_MANIFEST
    raw_manifest=json.dumps(manifest,indent=2,sort_keys=True)+"\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8")!=raw_manifest \
            and load(manifest_path)!=legacy_manifest(manifest):
        raise RuntimeError("organization record manifest write-once collision")
    if not manifest_path.exists(): manifest_path.write_text(raw_manifest,encoding="utf-8")
    if reconstruction is not None:
        (root/RECONSTRUCTION_RECEIPT).write_text(json.dumps(reconstruction,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return root

def legacy_manifest(manifest:dict[str,Any])->dict[str,Any]:
    """The same manifest as written under the pre-rename schema and authority effect."""
    return dict(manifest,schema=LEGACY_MASTER_RECORDS_CUSTODY["manifest_schema"],
                authority_effect=LEGACY_MASTER_RECORDS_CUSTODY["authority_effect"])

def read_manifest(root:Path)->dict[str,Any]:
    for name in (ORGANIZATION_RECORD_MANIFEST,LEGACY_MASTER_RECORDS_CUSTODY["manifest"]):
        if (root/name).is_file(): return load(root/name)
    raise RuntimeError("organization record manifest missing")

def reconstruct(root:Path)->dict[str,Any]:
    orchestration=resolve_orchestration()
    verifier=orchestration/"scripts/verify_sv002_self_characterization_reconstruction.py"
    output=root/RECONSTRUCTION_RECEIPT
    env={"PATH":os.environ.get("PATH",""),"HOME":os.environ.get("HOME",str(Path.home()))}
    done=subprocess.run(
        ["python3",str(verifier),str(root),"--output",str(output)],
        cwd=orchestration,env=env,capture_output=True,text=True,check=False,timeout=120,
    )
    if done.returncode!=0 or not output.is_file():
        raise RuntimeError("deterministic reconstruction failed:"+done.stderr[-512:])
    result=load(output)
    if result.get("status")!="PASS" or result.get("reconstruction")!="PASS" or result.get("experiment_id")!=EXPERIMENT_ID:
        raise RuntimeError("reconstruction result not PASS")
    return result

def run(ingress:Path)->dict[str,Any]:
    env=load(ingress)
    if (env.get("destination") or {}).get("org")!="master-records": raise RuntimeError("wrong destination org")
    if (env.get("destination") or {}).get("service")!=SERVICE_ID: raise RuntimeError("wrong destination service")
    payload=env.get("payload") or {}
    request=payload.get("request") if isinstance(payload.get("request"),dict) else payload
    if request.get("operation") not in (OPERATION,LEGACY_MASTER_RECORDS_CUSTODY["operation"]): raise RuntimeError("operation mismatch")
    if request.get("authority_transfer") is not False: raise RuntimeError("authority transfer prohibited")
    decoded,meta,artifact_set_sha256,run_id=verify_artifacts(request)
    manifest=build_manifest(request,meta,artifact_set_sha256,run_id)
    with tempfile.TemporaryDirectory() as td:
        reconstruction=reconstruct(materialize_workspace(Path(td)/"artifact-root",decoded,manifest))
    root=write_record(manifest,reconstruction)
    return {
        "schema":INTAKE_SCHEMA,
        "state":"RECORDED_AND_RECONSTRUCTED",
        "experiment_id":EXPERIMENT_ID,
        "run_id":run_id,
        "artifact_set_sha256":artifact_set_sha256,
        "record_root":str(root),
        "reconstruction_receipt_path":str(root/RECONSTRUCTION_RECEIPT),
        "reconstruction_receipt":reconstruction,
        "master_records_organization_record_established":True,
        "artifact_bytes_retained":False,
        "evidence_custody":"ORIGINATING_ORGANIZATION",
        "authority_transfer":False,
        "authority_effect":AUTHORITY_EFFECT,
    }

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--ingress",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    try: result=run(a.ingress.resolve());code=0
    except Exception as exc:
        result={"schema":INTAKE_SCHEMA,"state":"BLOCKED","reason":str(exc),"master_records_organization_record_established":False,"authority_transfer":False,"authority_effect":"NONE_BLOCKED"};code=2
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
    return code

if __name__=="__main__": raise SystemExit(main())
