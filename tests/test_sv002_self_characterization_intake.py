#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock

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

    def env(self,**values):
        clean={k:v for k,v in os.environ.items() if k not in (mod.ORGANIZATION_RECORD_ROOT_ENV,mod.LEGACY_MASTER_RECORDS_CUSTODY["root_env"])}
        clean.update(values)
        return mock.patch.dict(os.environ,clean,clear=True)

    def test_materializes_exact_bundle_to_master_records_organization_record(self):
        with tempfile.TemporaryDirectory() as td, self.env(**{mod.ORGANIZATION_RECORD_ROOT_ENV:td}):
            run_id="SV002-RUN-"+"c"*32
            root,digest,observed=mod.materialize_artifacts(self.request(run_id))
            self.assertEqual(observed,run_id)
            self.assertEqual(root,Path(td).resolve()/run_id/"artifact-root")
            self.assertTrue((root/"MASTER_RECORDS_ORGANIZATION_RECORD_MANIFEST.json").is_file())
            self.assertFalse((root/mod.LEGACY_MASTER_RECORDS_CUSTODY["manifest"]).exists())
            for name in mod.REQUIRED:self.assertTrue((root/name).is_file())
            manifest=mod.read_manifest(root)
            self.assertEqual(manifest["artifact_set_sha256"],digest)
            self.assertEqual(manifest["schema"],"master-records.sv002-organization-record-manifest/v1")
            self.assertEqual(manifest["authority_effect"],"NONE_ORGANIZATION_RECORD_ONLY")

    def test_accepts_pre_rename_manifest_values_under_new_name(self):
        run_id="SV002-RUN-"+"e"*32
        request=self.request(run_id)
        with tempfile.TemporaryDirectory() as td, self.env(**{mod.ORGANIZATION_RECORD_ROOT_ENV:td}):
            root,_,_=mod.materialize_artifacts(request)
            path=root/mod.ORGANIZATION_RECORD_MANIFEST
            old=dict(json.loads(path.read_text()),schema="master-records.sv002-custody-manifest/v1",authority_effect="NONE_CUSTODY_ONLY")
            path.write_text(json.dumps(old))
            mod.materialize_artifacts(request)
            path.write_text(json.dumps(dict(old,artifact_count=0)))
            with self.assertRaisesRegex(RuntimeError,"organization record manifest write-once collision"):
                mod.materialize_artifacts(request)

    def run_ingress(self,operation):
        run_id="SV002-RUN-"+"f"*32
        request=dict(self.request(run_id),operation=operation,authority_transfer=False)
        with tempfile.TemporaryDirectory() as td, self.env(**{mod.ORGANIZATION_RECORD_ROOT_ENV:td}):
            ingress=Path(td)/"in.json"
            ingress.write_text(json.dumps({"destination":{"org":"master-records","service":mod.SERVICE_ID},"payload":{"request":request}}))
            with mock.patch.object(mod,"reconstruct",return_value={"status":"PASS"}):
                return mod.run(ingress)

    def test_run_accepts_new_and_legacy_operation_and_emits_new_fields(self):
        for operation in ("ORGANIZATION_RECORD_SV002_SELF_CHARACTERIZATION","CUSTODY_SV002_SELF_CHARACTERIZATION"):
            with self.subTest(operation=operation):
                result=self.run_ingress(operation)
                self.assertEqual(result["schema"],"master-records.sv002-self-characterization-organization-record-intake/v1")
                self.assertEqual(result["authority_effect"],"NONE_ORGANIZATION_RECORD_ONLY")
                self.assertIn("record_root",result)
                self.assertNotIn("custody_root",result)
        with self.assertRaisesRegex(RuntimeError,"operation mismatch"):
            self.run_ingress("OTHER")

    def test_accepts_legacy_root_env(self):
        with tempfile.TemporaryDirectory() as td, self.env(**{mod.LEGACY_MASTER_RECORDS_CUSTODY["root_env"]:td}):
            self.assertEqual(mod.organization_record_base(),Path(td).resolve())

    def test_new_root_env_wins_over_legacy(self):
        with tempfile.TemporaryDirectory() as new, tempfile.TemporaryDirectory() as old, \
             self.env(**{mod.ORGANIZATION_RECORD_ROOT_ENV:new,mod.LEGACY_MASTER_RECORDS_CUSTODY["root_env"]:old}):
            self.assertEqual(mod.organization_record_base(),Path(new).resolve())

    def test_reads_legacy_manifest_and_rejects_conflicting_one(self):
        run_id="SV002-RUN-"+"d"*32
        request=self.request(run_id)
        with tempfile.TemporaryDirectory() as td, self.env(**{mod.ORGANIZATION_RECORD_ROOT_ENV:td}):
            root=Path(td).resolve()/run_id/"artifact-root"; root.mkdir(parents=True)
            legacy={"schema":"master-records.sv002-custody-manifest/v1","experiment_id":mod.EXPERIMENT_ID,"run_id":run_id,
                    "artifact_set_sha256":request["artifact_set_sha256"],"organization_ledger_root_hash":request["organization_ledger_root_hash"]}
            (root/mod.LEGACY_MASTER_RECORDS_CUSTODY["manifest"]).write_text(json.dumps(legacy))
            self.assertEqual(mod.read_manifest(root)["run_id"],run_id)
            mod.materialize_artifacts(request)
            self.assertTrue((root/mod.ORGANIZATION_RECORD_MANIFEST).is_file())
            (root/mod.ORGANIZATION_RECORD_MANIFEST).unlink()
            (root/mod.LEGACY_MASTER_RECORDS_CUSTODY["manifest"]).write_text(json.dumps(dict(legacy,artifact_set_sha256="0"*64)))
            with self.assertRaisesRegex(RuntimeError,"organization record manifest write-once collision"):
                mod.materialize_artifacts(request)

    def test_blocked_result_emits_new_field_only(self):
        with tempfile.TemporaryDirectory() as td:
            ingress=Path(td)/"in.json"; out=Path(td)/"out.json"
            ingress.write_text(json.dumps({"destination":{"org":"other"}}))
            with mock.patch.object(sys,"argv",["x","--ingress",str(ingress),"--out",str(out)]), mock.patch("builtins.print"):
                self.assertEqual(mod.main(),2)
            result=json.loads(out.read_text())
            self.assertIs(result["master_records_organization_record_established"],False)
            self.assertNotIn("master_records_custody_established",result)
            self.assertEqual(result["schema"],"master-records.sv002-self-characterization-organization-record-intake/v1")

if __name__=="__main__": unittest.main()
