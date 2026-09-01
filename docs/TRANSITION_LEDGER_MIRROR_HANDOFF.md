# Transition Ledger Mirror Handoff

Repository: `master-records/.github`

Every durable transition owned here is recorded first in this repository ledger. Repo replay/reconstruction must terminate without org/ecosystem replay.

Contract: `.stegverse/transition-ledger/contract.json`  
Emitter: `.stegverse/transition-ledger/emit.py`  
Durable root: `$XDG_STATE_HOME/stegverse/repo-ledgers/master-records/.github`

Receipts are append-only/hash-linked. Only evidence needed for organization reconstruction propagates to `master-records/.github`. Recording grants no authority.
