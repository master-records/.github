#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("sv002_mr_intake",ROOT/"resident-runtime/sv002_self_characterization_intake.py")
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)

class TestSV002MasterRecordsIntake(unittest.TestCase):
    def request(self,run_id):
        rows=[]; meta=[]
        org_hash="a"*64
        for name in mod.REQUIRED:
            if name=="S0.json":
                raw=json.dumps({"experiment_id":mod.EXPERIMENT_ID,"run_id":run_id}).encode()
            elif name=="EXPERIMENT_EXECUTION_RECEIPT.json":
                raw=json.dumps({"experiment_id":mod.EXPERIMENT_ID,"run_id":run_id}).encode()
            elif name=="ORGANIZATION_LEDGER_ROOT.json":
                raw=json.dumps({"root_hash":org_hash}).encode()
            else:
                raw=(name+"\n").encode()
            rows.append({"name":name,"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw),"base64":base64.b64encode(raw).decode()})
            meta.append({"name":name,"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw)})
        artifact_set=hashlib.sha256(mod.canon(meta)).hexdigest()
        return {"experiment_id":mod.EXPERIMENT_ID,"run_id":run_id,"artifact_set_sha256":artifact_set,"organization_ledger_root_hash":org_hash,"artifacts":rows}
    def test_materializes_exact_bundle_to_master_records_custody(self):
        with tempfile.TemporaryDirectory() as td:
            prior=os.environ.get("STEGVERSE_MASTER_RECORDS_SV002_CUSTODY_ROOT")
            os.environ["STEGVERSE_MASTER_RECORDS_SV002_CUSTODY_ROOT"]=td
            try:
                run_id="SV002-RUN-"+"c"*32
                root,digest,observed=mod.materialize_artifacts(self.request(run_id))
                self.assertEqual(observed,run_id)
                self.assertTrue((root/"MASTER_RECORDS_CUSTODY_MANIFEST.json").is_file())
                for name in mod.REQUIRED:self.assertTrue((root/name).is_file())
                manifest=json.loads((root/"MASTER_RECORDS_CUSTODY_MANIFEST.json").read_text())
                self.assertEqual(manifest["artifact_set_sha256"],digest)
                self.assertEqual(manifest["authority_effect"],"NONE_CUSTODY_ONLY")
            finally:
                if prior is None: os.environ.pop("STEGVERSE_MASTER_RECORDS_SV002_CUSTODY_ROOT",None)
                else: os.environ["STEGVERSE_MASTER_RECORDS_SV002_CUSTODY_ROOT"]=prior

if __name__=="__main__": unittest.main()
