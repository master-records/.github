# master-records

**master-records is the StegVerse recorder of released organization batch receipts for cross-organization reconstruction.**

An Organization may release a batch receipt whose release predecessor is a verified segment of its own organization receipt chain. Master Records records that released receipt so cross-organization history can be reconstructed. Custody and durable history stay with each Organization.

## What belongs here

The organization includes:

- **orchestration** — recording of released organization batch receipts and the deterministic reconstruction verifiers that read them;
- **monitoring** — observation of Master Records' own recording surfaces (not of any organization's runtime reality);
- **telemetry** — Master Records' own operational telemetry;
- **core-lite** — bounded supporting logic internal to Master Records.

## Role in the ecosystem

Master Records records released organization batch receipts, including those covering end-of-life transitions, for cross-organization reconstruction. Its release predecessor is a verified organization receipt-chain segment. Custody, retention and durable history of the underlying evidence stay with the Organization that produced it.

Master Records cannot create, admit, authorize, infer or repair a transition, and it never held transition authority. It is not the runtime-reality authority and not a gate on any organization's runtime reality; no organization awaits it. Recording a released receipt does not authorize anything. Admission, gates, closure, and prerequisites belong to Interlock/InTr, and ledger roles belong to the organization transition ledger.
