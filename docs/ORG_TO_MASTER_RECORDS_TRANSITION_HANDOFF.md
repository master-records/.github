# Organization to Master Records Transition Handoff

Organization: `master-records`

After a repository transition is verified and rolled into the organization ledger, the exact `stegverse.organization-transition-receipt/v1` may be submitted to Master Records through the existing organization federation.

Publisher: `resident-runtime/submit_org_transition_to_master_records.py`

Route:

`master-records/.github -> InTr -> master-records/.github -> master-records.ecosystem-transition-ledger -> master-records/orchestration`

The packet carries the already-hash-bound organization receipt. Transport and custody do not create source authority and do not replace repo/org replay.


## SV002 self-characterization custody endpoint — 2026-09-01

A dedicated custody/reconstruction endpoint now exists for the canonical StegVerse-002 self-characterization artifact set:

`master-records.sv002-self-characterization-reconstruction`

Adapter:
`resident-runtime/sv002_self_characterization_intake.py`

Route:

```text
StegVerse-002/.github
-> InTr/federation
-> master-records/.github boundary
-> master-records.sv002-self-characterization-reconstruction
-> write-once Master Records custody root
-> master-records/orchestration deterministic verifier
-> reconstruction receipt
```

The intake validates the exact bounded artifact list, per-artifact SHA-256/size, aggregate artifact-set hash, experiment ID, RunID, and organization-ledger-root binding before materialization. Custody is written under the Master Records state domain, not the source execution root.

A successful response requires deterministic reconstruction PASS. Receipt ingestion, custody, reconstruction, release, activation, and authority remain distinct states.
