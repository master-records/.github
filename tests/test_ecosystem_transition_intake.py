#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
def load_module(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
intake=load_module("mr_ecosystem_transition_intake","resident-runtime/ecosystem_transition_intake.py")
submit=load_module("mr_submit_org_transition","resident-runtime/submit_org_transition_to_master_records.py")

class TestEcosystemTransitionIntake(unittest.TestCase):
    def run_ingress(self,operation):
        request={"operation":operation,"organization_receipt":{"schema":"x"},"predecessor_ecosystem_state_sha256":"a"*64,
                 "successor_ecosystem_state_sha256":"b"*64,"authority_transfer":False}
        with tempfile.TemporaryDirectory() as td:
            ingress=Path(td)/"in.json"
            ingress.write_text(json.dumps({"destination":{"org":"master-records","service":"master-records.ecosystem-transition-ledger"},"payload":{"request":request}}))
            done=subprocess.CompletedProcess([],0,stdout=json.dumps({"receipt":"r"})+"\n",stderr="")
            with mock.patch.object(intake,"resolve_orchestration",return_value=Path(td)), \
                 mock.patch.object(intake.subprocess,"run",return_value=done):
                return intake.run(ingress)

    def test_accepts_new_and_legacy_operation_and_emits_new_fields(self):
        for operation in ("ORGANIZATION_RECORD_ORGANIZATION_TRANSITION","CUSTODY_ORGANIZATION_TRANSITION"):
            with self.subTest(operation=operation):
                result=self.run_ingress(operation)
                self.assertEqual(result["record_receipt"],{"receipt":"r"})
                self.assertNotIn("custody_receipt",result)
                self.assertEqual(result["authority_effect"],"NONE_ORGANIZATION_RECORD_ONLY")
        with self.assertRaisesRegex(RuntimeError,"operation mismatch"):
            self.run_ingress("OTHER")

    def test_publisher_emits_new_values_only(self):
        with tempfile.TemporaryDirectory() as td:
            receipt=Path(td)/"receipt.json"
            receipt.write_text(json.dumps({"schema":"stegverse.organization-transition-receipt/v1","organization":"master-records"}))
            argv=["x","--org-receipt",str(receipt),"--predecessor-ecosystem-state-sha256","a"*64,"--successor-ecosystem-state-sha256","b"*64]
            published={"frame":{"frame_sha256":"f"*64}}
            with mock.patch.object(sys,"argv",argv), mock.patch.object(submit.K,"publish_packet",return_value=published) as pub, \
                 mock.patch("builtins.print") as out:
                submit.main()
        packet=pub.call_args.args[0]
        self.assertEqual(packet["payload"]["operation"],"ORGANIZATION_RECORD_ORGANIZATION_TRANSITION")
        self.assertEqual(packet["transition"]["reference"],"ecosystem.transition.organization-record.v1")
        self.assertEqual(json.loads(out.call_args.args[0])["status"],"PUBLISHED_FOR_ORGANIZATION_RECORD")

if __name__=="__main__": unittest.main()
