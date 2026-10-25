"""Organization ledger genesis from the committed epoch packet (resident-runtime/ledger_genesis.py).

Ledgers and the epoch source here are temporary repositories built by the test: receipts written
by these tests are NOT LEDGERED and NOT AUTHENTIC. No network, no clock. The genesis is a
main-merge transfer, never an InTr hop inside this organization.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = json.loads((ROOT / ".stegverse/merge-transfer/genesis-epoch.json").read_text())
SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def seal(body):
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                                 ensure_ascii=False).encode()).hexdigest()


class Genesis(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        w = Path(self.work.name)
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t", "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
               "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z"}
        self.saved = {k: os.environ.get(k) for k in (*env, "STEGVERSE_REPO_LEDGER_ROOT", "STEGVERSE_ORG_LEDGER_ROOT")}
        os.environ.update(env)
        os.environ["STEGVERSE_REPO_LEDGER_ROOT"] = str(w / "repo")
        os.environ["STEGVERSE_ORG_LEDGER_ROOT"] = str(w / "org")
        # A synthetic public source ledger whose head records the packet's epoch.
        src = w / "src"
        src.mkdir()
        git("init", "-q", "-b", "main", cwd=src)
        body = {"schema": "stegverse.organization-transition-receipt/v1", "previous_receipt_sha256": None,
                "hb_reference": {"epoch": PACKET["hb_epoch"], "derived_from_clock": False}}
        self.receipt = {**body, "receipt_sha256": seal(body)}
        (src / "receipts").mkdir()
        (src / "receipts" / (self.receipt["receipt_sha256"][7:] + ".json")).write_text(json.dumps(self.receipt))
        (src / "HEAD.json").write_text(json.dumps({"receipt_sha256": self.receipt["receipt_sha256"]}))
        git("add", "-A", cwd=src)
        git("commit", "-qm", "ledger", cwd=src)
        self.src_git = str(src / ".git")
        self.packet = copy.deepcopy(PACKET)
        self.packet["epoch_source"]["ledger_tip"] = git("rev-parse", "HEAD", cwd=src)
        self.packet["epoch_source"]["head_receipt_sha256"] = self.receipt["receipt_sha256"]
        # A merge on this repository's history to open the ledger with: the checkout's own HEAD.
        self.commit = git("rev-parse", "HEAD", cwd=ROOT)
        self.genesis = load("ledger_genesis_test", "resident-runtime/ledger_genesis.py")

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.work.cleanup()

    def test_the_committed_packet_is_well_formed(self):
        self.assertIsNone(self.genesis.packet_failure(PACKET))
        self.assertEqual(PACKET["repository"], "master-records/.github")
        self.assertNotEqual(PACKET["epoch_source"]["ledger_repository"], PACKET["repository"])

    def test_genesis_opens_the_ledger_with_a_main_merge_transfer_once(self):
        first = self.genesis.open_ledger(self.packet, [self.commit], self.src_git)
        self.assertEqual((first["disposition"], first["genesis"]), ("ALLOW", "OPENED"), first)
        self.assertEqual(first["operation"], "ORGANIZATION_MAIN_MERGE_TRANSFER")
        self.assertIsNone(first["previous_receipt_sha256"])
        self.assertEqual(first["hb_epoch"], PACKET["hb_epoch"])
        verified = self.genesis.mt.verify_merge_transfer(self.genesis.mt.repository(), self.commit)
        self.assertEqual(verified["disposition"], "ALLOW", verified)
        again = self.genesis.open_ledger(self.packet, [self.commit], self.src_git)
        self.assertEqual(again["genesis"], "GENESIS_NOT_NEEDED")
        self.assertEqual(again["head_receipt_sha256"], first["organization_receipt_sha256"])

    def test_the_head_epoch_then_drives_the_ordinary_append(self):
        self.genesis.open_ledger(self.packet, [self.commit], self.src_git)
        epoch, failed = self.genesis.mt.head_epoch(self.genesis.mt.org_store())
        self.assertIsNone(failed)
        self.assertEqual(epoch, PACKET["hb_epoch"])

    def _refused(self, packet, code):
        result = self.genesis.open_ledger(packet, [self.commit], self.src_git)
        self.assertEqual(result["disposition"], "FAIL_CLOSED", result)
        self.assertEqual(result["failure_code"], code)
        self.assertTrue(all(result.get(f) for f in SIX), result)
        self.assertFalse(any(Path(self.work.name).glob("org/**/*.json")))

    def test_an_epoch_that_differs_from_the_source_head_is_refused(self):
        packet = copy.deepcopy(self.packet)
        packet["hb_epoch"] += 1
        self._refused(packet, "GENESIS_EPOCH_SOURCE_UNVERIFIED")

    def test_an_unknown_head_receipt_is_refused(self):
        packet = copy.deepcopy(self.packet)
        packet["epoch_source"]["head_receipt_sha256"] = "sha256:" + "0" * 64
        self._refused(packet, "GENESIS_EPOCH_SOURCE_UNVERIFIED")

    def test_an_absent_tip_is_refused(self):
        packet = copy.deepcopy(self.packet)
        packet["epoch_source"]["ledger_tip"] = "0" * 40
        self._refused(packet, "GENESIS_EPOCH_SOURCE_UNVERIFIED")

    def test_an_epoch_below_the_anchor_or_own_ledger_source_is_refused(self):
        packet = copy.deepcopy(self.packet)
        packet["hb_epoch"] = 31
        self._refused(packet, "GENESIS_EPOCH_PACKET_INVALID")
        packet = copy.deepcopy(self.packet)
        packet["epoch_source"]["ledger_repository"] = "master-records/.github"
        self._refused(packet, "GENESIS_EPOCH_PACKET_INVALID")


if __name__ == "__main__":
    unittest.main()
