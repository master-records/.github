# Organization Transition Ledger Mirror Handoff

Organization: `master-records`

Repository-level transitions remain owned and replayable in their originating repositories. This `.github` layer verifies a repo receipt, records only the organization-level state consequence, and links the exact repo receipt hash.

Contract: `.stegverse/transition-ledger/org-contract.json`  
Rollup: `resident-runtime/aggregate_repo_transition.py`

Organization replay must terminate using verified repo receipts plus this org chain; it terminates at the organization layer of the organization transition ledger, before any ecosystem-layer replay.

The organization may release an organization batch receipt, whose release predecessor is a verified segment of this org chain, to Master Records for cross-organization reconstruction. Evidence and durable history stay with this organization; nothing here awaits Master Records. Recording creates no authority.
