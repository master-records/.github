# Organization Transition Ledger Mirror Handoff

Organization: `master-records`

Repository-level transitions remain owned and replayable in their originating repositories. This `.github` layer verifies a repo receipt, records only the organization-level state consequence, and links the exact repo receipt hash.

Contract: `.stegverse/transition-ledger/org-contract.json`  
Rollup: `resident-runtime/aggregate_repo_transition.py`

Organization replay must terminate using verified repo receipts plus this org chain; it terminates at the organization layer of the organization transition ledger, before any ecosystem-layer replay.

Only the organization receipt and evidence required for ecosystem reconstruction propagate to `master-records/.github`. Recording creates no authority.
