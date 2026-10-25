#!/usr/bin/env python3
"""Organization ledger genesis: the first main-merge transfer opens the ledger at a committed epoch.

This organization's ledger ref (refs/stegverse/organization-ledger) is opened by
.github/workflows/organization-ledger-writer.yml on a push to main, by the same
append the writer makes for every merge (resident-runtime/merge_transfer.py,
operation ORGANIZATION_MAIN_MERGE_TRANSFER, through
resident-runtime/intr_destination_ingress.py::_append). It is not an InTr hop:
nothing is addressed to this organization's own InTr destination (Rigel's rule,
2026-10-25: InTr paths exist only between distinct organizations).

merge_transfer.py takes its epoch from the ledger head receipt; a ledger with no
head has none (HB_EPOCH_SOURCE_UNOBSERVED). For the genesis receipt only, the
epoch comes from the committed epoch packet
(.stegverse/merge-transfer/genesis-epoch.json): an hb_epoch together with the
public organization ledger head it was read from (repository, ref, tip commit,
head receipt seal). The workflow reads that ledger anonymously (E0, no credential)
into a local bare repository; this module verifies, from the local objects only,
that the tip's HEAD.json names the head receipt, that the receipt's seal
re-digests, and that its hb_reference.epoch equals the packet's hb_epoch, is an
int >= 32 and is not derived from a clock. No clock is read, nothing is
dispatched, no ref is hand-written, and the network is touched only by the
workflow's anonymous fetch.

When the ledger already has a HEAD this module writes nothing (GENESIS_NOT_NEEDED):
a genesis happens once. Every refusal carries six fields and writes nothing.

SKAP Vault inside KV is the only PII and credential store for every user, the
ecosystem's own included; the ecosystem holds none (HST citation pending P1 #163).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mt = _module("merge_transfer_for_ledger_genesis", "resident-runtime/merge_transfer.py")

PACKET = ROOT / ".stegverse" / "merge-transfer" / "genesis-epoch.json"
PACKET_SCHEMA = "stegverse.organization-ledger-genesis-epoch/v1"
RESULT_SCHEMA = "stegverse.organization-ledger-genesis-result/v1"
LEDGER_REF = "refs/stegverse/organization-ledger"
ENTRYPOINT = ".github/workflows/organization-ledger-writer.yml (push to main; job merge-transfer, genesis step)"
GOAL = "StegVerse-org/.github#162"
SHA40 = re.compile(r"[0-9a-f]{40}")
SEAL = re.compile(r"sha256:[0-9a-f]{64}")
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/\.github")
ALLOW, FAIL_CLOSED = "ALLOW", "FAIL_CLOSED"

PACKET_INVALID = "GENESIS_EPOCH_PACKET_INVALID"
SOURCE_UNVERIFIED = "GENESIS_EPOCH_SOURCE_UNVERIFIED"
NO_COMMIT = "GENESIS_COMMIT_ABSENT"


def refusal(code: str, predicate: str, repair: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"schema": RESULT_SCHEMA, "disposition": FAIL_CLOSED, "failure_code": code,
            "failed_predicate": predicate, "required_evidence_or_repair": repair,
            "retry_entrypoint": ENTRYPOINT, "owning_existing_goal": GOAL,
            "next_attempt": "commit a corrected .stegverse/merge-transfer/genesis-epoch.json to main; nothing was written",
            "detail": detail, **extra}


def packet_failure(packet: Any) -> str | None:
    if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
        return "packet schema is not " + PACKET_SCHEMA
    if packet.get("repository") != mt.repository():
        return "packet repository " + repr(packet.get("repository")) + " is not " + mt.repository()
    epoch = packet.get("hb_epoch")
    if type(epoch) is not int or epoch < 32:
        return "hb_epoch is not an int >= 32"
    source = packet.get("epoch_source")
    if not isinstance(source, Mapping):
        return "epoch_source is absent"
    if not isinstance(source.get("ledger_repository"), str) or not REPOSITORY.fullmatch(source["ledger_repository"]):
        return "epoch_source.ledger_repository is not <Organization>/.github"
    if source["ledger_repository"] == mt.repository():
        return "epoch_source names this organization's own ledger, which has no head yet"
    if source.get("ledger_ref") != LEDGER_REF:
        return "epoch_source.ledger_ref is not " + LEDGER_REF
    if not isinstance(source.get("ledger_tip"), str) or not SHA40.fullmatch(source["ledger_tip"]):
        return "epoch_source.ledger_tip is not 40 lowercase hex"
    if not isinstance(source.get("head_receipt_sha256"), str) or not SEAL.fullmatch(source["head_receipt_sha256"]):
        return "epoch_source.head_receipt_sha256 is not sha256:<64 hex>"
    return None


def _show(git_dir: Path | str, commit: str, path: str) -> Any:
    done = subprocess.run(["git", "--git-dir", str(git_dir), "show", commit + ":" + path],
                          capture_output=True, text=True)
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def verify_epoch_source(packet: Mapping[str, Any], source_git_dir: Path | str) -> tuple[int | None, dict[str, Any] | None]:
    """(epoch, None) when the packet's epoch is the verified head epoch of the named public ledger."""
    bad = packet_failure(packet)
    if bad is not None:
        return None, refusal(PACKET_INVALID, "GENESIS_EPOCH_PACKET_IS_WELL_FORMED",
                             "a packet of schema " + PACKET_SCHEMA + " naming this repository, an int hb_epoch >= 32 "
                             "and another organization's public ledger head", bad)
    source = packet["epoch_source"]

    def unverified(detail: str) -> tuple[None, dict[str, Any]]:
        return None, refusal(SOURCE_UNVERIFIED, "GENESIS_EPOCH_IS_THE_VERIFIED_HEAD_EPOCH_OF_THE_NAMED_LEDGER",
                             "the named ledger tip, read anonymously, must hold HEAD.json naming the head receipt, whose "
                             "seal re-digests and whose hb_reference.epoch equals hb_epoch with derived_from_clock false",
                             detail, epoch_source=dict(source))

    tip = source["ledger_tip"]
    head = _show(source_git_dir, tip, "HEAD.json")
    if not isinstance(head, Mapping) or head.get("receipt_sha256") != source["head_receipt_sha256"]:
        return unverified("HEAD.json at " + tip + " is absent or names " + repr((head or {}).get("receipt_sha256")
                                                                               if isinstance(head, Mapping) else None))
    receipt = _show(source_git_dir, tip, "receipts/" + source["head_receipt_sha256"][len("sha256:"):] + ".json")
    if not mt.sealed(receipt) or receipt["receipt_sha256"] != source["head_receipt_sha256"]:
        return unverified("head receipt " + source["head_receipt_sha256"] + " is absent or its seal does not verify")
    reference = receipt.get("hb_reference")
    epoch = reference.get("epoch") if isinstance(reference, Mapping) else None
    if type(epoch) is not int or epoch < 32 or reference.get("derived_from_clock") is not False:
        return unverified("head hb_reference " + repr(reference) + " is not a supplied epoch")
    if epoch != packet["hb_epoch"]:
        return unverified("head epoch " + str(epoch) + " differs from packet hb_epoch " + str(packet["hb_epoch"]))
    return epoch, None


def open_ledger(packet: Mapping[str, Any], commits: list[str], source_git_dir: Path | str) -> dict[str, Any]:
    """Open the ledger with the first pushed merge's main-merge transfer, or write nothing."""
    store = mt.org_store()
    head = mt._get(store, mt.store_module().HEAD_KEY)
    if isinstance(head, Mapping) and head.get("receipt_sha256"):
        return {"schema": RESULT_SCHEMA, "disposition": ALLOW, "genesis": "GENESIS_NOT_NEEDED",
                "head_receipt_sha256": head["receipt_sha256"]}
    if not commits:
        return refusal(NO_COMMIT, "GENESIS_OPENS_ON_A_PUSHED_MERGE", "the push must name at least one commit",
                       "no commit was selected for this push")
    epoch, failed = verify_epoch_source(packet, source_git_dir)
    if failed is not None:
        return failed
    facts = mt.commit_facts(commits[0])
    bad = mt.facts_failure(facts)
    if bad is not None:
        return refusal(mt.FACTS_INVALID, "MERGE_COMMIT_FACTS_ARE_READ_FROM_THE_COMMIT_OBJECT",
                       "pass the commit's tree, parents and subject as git cat-file reads them", bad)
    repo = mt.repository()
    evidence = mt.merge_evidence(repo, facts)
    appended, replayed = mt.ingress._append(
        mt.TRANSITION_CLASS, facts["merge_commit"], evidence, epoch, operation=mt.OPERATION,
        profile_id=mt.PROFILE_ID, boundary_extra={"repository": repo, "merge_commit": facts["merge_commit"]})
    organization_receipt = appended["organization_receipt"]
    return {"schema": RESULT_SCHEMA, "disposition": ALLOW, "genesis": "OPENED", "operation": mt.OPERATION,
            "repository": repo, "merge_commit": facts["merge_commit"], "hb_epoch": epoch, "replayed": replayed,
            "epoch_source": dict(packet["epoch_source"]),
            "previous_receipt_sha256": organization_receipt.get("previous_receipt_sha256"),
            "repository_receipt_sha256": appended["repository_receipt"]["receipt_sha256"],
            "organization_receipt_sha256": organization_receipt["receipt_sha256"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", default=str(PACKET))
    parser.add_argument("--commits-file", required=True)
    parser.add_argument("--source-git-dir", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        packet = {"unreadable": str(exc)}
    commits = Path(args.commits_file).read_text(encoding="utf-8").split()
    result = open_ledger(packet, commits, args.source_git_dir)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["disposition"] == ALLOW else 1


if __name__ == "__main__":
    raise SystemExit(main())
