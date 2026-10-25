# Organization ledger genesis (master-records/.github)

Authoring-Session: lane-b-91117956 · owning goal StegVerse-org/.github#162

`refs/stegverse/organization-ledger` of this organization is opened by its own push-triggered
writer (`.github/workflows/organization-ledger-writer.yml`, job `merge-transfer`). There is no
dispatch and no hand-written ref.

1. On a push to main, the writer finds the ledger ref absent and sets `LEDGER_GENESIS=1`.
2. It reads the public ledger named by the committed epoch packet
   (`.stegverse/merge-transfer/genesis-epoch.json`: StegVerse-Labs/.github at tip
   `b7917dcadcbf77a6abca1063970baef96d9309ea`, head receipt
   `sha256:f840271ea47e9ff0fc2b81bb0d428dfdadc2cbfb2a4299a727ecf07e2ff32c6f`) anonymously.
3. `resident-runtime/ledger_genesis.py` verifies that tip's `HEAD.json`, the head receipt's seal and
   its epoch (`469411750`, not derived from a clock, equal to the packet). It then appends the first
   pushed merge's `ORGANIZATION_MAIN_MERGE_TRANSFER` at that epoch, with
   `previous_receipt_sha256: null`.
4. The ordinary append replays that merge idempotently and appends the rest at the head's epoch.
   The ref is published fast-forward only and verified from a fresh fetch.

Any refusal fails closed with six fields (`GENESIS_EPOCH_PACKET_INVALID`,
`GENESIS_EPOCH_SOURCE_UNVERIFIED`, `GENESIS_COMMIT_ABSENT`). A second run answers
`GENESIS_NOT_NEEDED`. The genesis is a main-merge transfer, not an InTr hop: nothing is addressed to
this organization's own InTr destination, and the retired self-closure carrier is not installed.

The InTr path declaration (path-transfer/path-ingress jobs, `transfers.json`, `inbound.json`, and the
peers' rows) is not part of this install. It waits on the #162 ruling about the destinations manifest
class.

`data/intr-protocol/v1/protocol.json` is a byte-identical copy of the shared protocol file, because
`org-runtime/intr_protocol.py` reads it. It is not edited.

SKAP Vault inside KV is the only PII and credential store for every user, the ecosystem's own included; the ecosystem holds none (HST citation pending P1 #163).
