# Organization to Master Records Transition Handoff

Organization: `master-records`

After a repository transition is verified and rolled into the organization ledger, the exact `stegverse.organization-transition-receipt/v1` may be submitted to Master Records as an organization record through the existing organization federation.

Publisher: `resident-runtime/submit_org_transition_to_master_records.py`

Route:

`master-records/.github -> InTr -> master-records/.github -> master-records.ecosystem-transition-ledger -> master-records/orchestration`

The packet carries operation `ORGANIZATION_RECORD_ORGANIZATION_TRANSITION` and transition reference `ecosystem.transition.organization-record.v1`; the publisher reports `PUBLISHED_FOR_ORGANIZATION_RECORD`. The intake returns the ledger receipt as `record_receipt` with authority effect `NONE_ORGANIZATION_RECORD_ONLY`. The pre-rename operation `CUSTODY_ORGANIZATION_TRANSITION` is still accepted on read (MASTER-RECORDS-BULK-SEMANTIC-REMEDIATION-002).

The packet carries the already-hash-bound organization receipt. Transport and recording do not create source authority. Replay stays with the repo/org layers of the organization transition ledger; Master Records uses the record for reconstruction.


## SV002 self-characterization organization record endpoint — 2026-09-01

A dedicated organization record/reconstruction endpoint now exists for the canonical StegVerse-002 self-characterization artifact set:

`master-records.sv002-self-characterization-reconstruction`

Adapter:
`resident-runtime/sv002_self_characterization_intake.py`

Route:

```text
StegVerse-002/.github
-> InTr/federation
-> master-records/.github boundary
-> master-records.sv002-self-characterization-reconstruction
-> write-once Master Records organization record root
-> master-records/orchestration deterministic verifier
-> reconstruction receipt
```

The intake validates the exact bounded artifact list, per-artifact SHA-256/size, aggregate artifact-set hash, experiment ID, RunID, and organization-ledger-root binding before materialization. The organization record is written under the Master Records state domain (`STEGVERSE_MASTER_RECORDS_SV002_ORGANIZATION_RECORD_ROOT`, manifest `MASTER_RECORDS_ORGANIZATION_RECORD_MANIFEST.json`), not the source execution root. Requests carry operation `ORGANIZATION_RECORD_SV002_SELF_CHARACTERIZATION`; the manifest schema is `master-records.sv002-organization-record-manifest/v1`, and the intake result schema is `master-records.sv002-self-characterization-organization-record-intake/v1` with `record_root` and authority effect `NONE_ORGANIZATION_RECORD_ONLY`. The pre-rename root variable, manifest name, operation `CUSTODY_SV002_SELF_CHARACTERIZATION`, and a manifest written under `master-records.sv002-custody-manifest/v1` / `NONE_CUSTODY_ONLY` are still read (MASTER-RECORDS-BULK-SEMANTIC-REMEDIATION-002).

A successful response requires deterministic reconstruction PASS. Receipt ingestion, organization recording, reconstruction, release, activation, and authority remain distinct states; evidence custody stays with the Organization.
