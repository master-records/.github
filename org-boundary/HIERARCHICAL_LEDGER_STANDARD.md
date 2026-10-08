# Hierarchical Ledger and Recursive Reconstruction Standard

Status: CANONICAL DESIGN
Version: stegverse.hierarchical-ledger/v1
Scope: repository -> organization -> ecosystem

## Purpose

StegVerse receipt history is recursively reconstructable at three resolutions without requiring every higher layer to duplicate every lower-layer event.

The governing model is:

```text
repository ledger = granular event history for one repository
organization ledger = authoritative coverage of repositories beneath one organization
organization transition ledger (ecosystem layer) = canonical ecosystem coverage of organization ledgers plus ecosystem-native transitions
Master Records = organization records of the covered roots, used for reconstruction
```

Coverage means ordered, integrity-bound, reconstructable inclusion. Coverage does not require payload duplication.

## Core invariants

1. The repository is the highest-resolution routine ledger boundary.
2. The organization ledger covers every repository beneath that organization by ordered receipt-root reference and may also contain organization-native transitions.
3. The ecosystem layer of the organization transition ledger covers every participating organization by ordered organization-root reference and may also contain ecosystem-native or cross-organization transitions.
4. An upper layer MUST NOT claim coverage of a lower-layer interval unless the exact ordered interval is bound by hash/root and remains resolvable.
5. Aggregation MUST preserve sequence. Set membership alone is insufficient.
6. Missing, unavailable, or unverifiable descendants remain NOT_ESTABLISHED; an upper root MUST NOT fabricate lower evidence.
7. Receipt aggregation grants no execution, admission, credential, release, deployment, or activation authority.
8. Replay and reconstruction use the same canonical receipt history that supported the live view.
9. A live projection may summarize lower layers, but every summary must resolve to its canonical descendant evidence.
10. Historical roots are immutable. A new aggregate state creates a successor root linked to the previous root.

## Repository ledger

The repository ledger records the most granular governed transitions relevant to repository state.

Examples include:

```text
objective_received
uncertainty_registered
discovery_initiated
resource_observed
authority_evaluated
knowledge_state_changed
plan_changed
pre_execution_gate_passed
file_or_state_mutated
validation_started
validation_completed
commit_or_artifact_bound
receipt_emitted
```

Not every read or computation must become a canonical transition. The repository decides event significance according to its governing state-transition schema. Any transition used to support an externally consequential claim MUST be receipt-bound.

A repository checkpoint/root MUST bind:

- repository identity;
- ordered first and last receipt identifiers;
- receipt count;
- ordered root hash;
- predecessor checkpoint/root;
- reconstruction status;
- optional experiment/run identifiers;
- optional semantic summary for live projection.

## Organization ledger

The organization ledger is the canonical organizational aggregation layer.

It contains:

1. ordered references to repository checkpoint/root intervals; and
2. organization-native transitions that cannot be reduced to one repository.

Organization-native examples:

```text
repository admitted to organization capability graph
organization policy changed
cross-repository dependency established
organization capability snapshot changed
org-boundary ingress or egress accepted
organization release state changed
```

An organization root MUST identify every descendant repository root that contributes to that organization state. It SHOULD retain only the aggregation metadata necessary for deterministic resolution rather than duplicating each underlying event.

## Ecosystem layer of the organization transition ledger

The ecosystem layer of the organization transition ledger is the canonical ecosystem coverage layer.

It contains:

1. ordered references to organization roots;
2. ecosystem-native transitions;
3. cross-organization transitions;
4. reconstruction references for the roots it accepts.

Master Records holds the organization records for those roots and uses them for reconstruction; custody of the underlying evidence stays with the Organization.

Ecosystem-layer coverage does not mean central ingestion of every repository event. It means that every accepted ecosystem-level claim has a deterministic evidence path:

```text
ecosystem root
  -> organization root
      -> repository root
          -> individual transition receipts
              -> bound evidence/artifacts
```

## Ordered range semantics

Every aggregate child reference MUST bind the child's ordered interval:

```yaml
scope_type: repo
scope_id: StegVerse-002/micro-node-runtime
root_id: repo-root-00042
range:
  first_receipt_id: R000341
  last_receipt_id: R000417
  receipt_count: 77
  ordered_root_hash: sha256:...
```

An ordered root MUST commit to both content and sequence. Reordering identical receipt members MUST produce a different root.

## Root chaining

Every root except genesis MUST identify its predecessor.

```text
repo-root-N      -> repo-root-(N-1)
org-root-N       -> org-root-(N-1)
ecosystem-root-N -> ecosystem-root-(N-1)
```

The successor does not overwrite historical membership.

## Reconstruction modes

### Top-down reconstruction

Used to inspect an ecosystem or organization claim.

```text
ecosystem root
-> selected organization root
-> selected repository root
-> selected transition interval
-> evidence
```

A verifier MAY stop at any valid summary layer unless the requested claim requires deeper resolution.

### Bottom-up inclusion proof

Used to prove that a granular transition contributes to a higher-level canonical state.

```text
transition receipt
-> repository ordered root
-> organization ordered root
-> ecosystem ordered root
```

Each step MUST verify exact inclusion and predecessor continuity.

## Live projection

Live viewers are projections of canonical receipts, not independent event sources.

A live view MAY show:

- ecosystem state;
- organization state;
- repository state;
- transition count;
- latest transition kind;
- reconstruction status;
- drill-down links.

The viewer MUST NOT mint or repair canonical receipts.

Example:

```text
ECOSYSTEM
StegVerse-002  ACTIVE  org-root-91

  micro-node-runtime  61 transitions
  .github             14 transitions

    T34 discovery_initiated
    T35 resource_observed
    T36 authority_evaluated
    T37 knowledge_state_changed
    T38 plan_changed
```

## Replay

Replay re-renders the historical progression from canonical stored roots and receipts.

For a fixed run ID, the live view and replay view MUST resolve to the same ordered transition identities, hashes, and state classifications.

Replay MAY change presentation resolution but MUST NOT change historical ordering or evidence classification.

## Self-characterization experiment requirement

For StegVerse-002 self-characterization and related pre-execution discovery experiments, repository-level recording SHOULD be sufficiently granular to distinguish at least:

```text
objective_received
known_unknown_or_uncertainty_registered
discovery_initiated
resource_observed
authority_resolution
state_or_knowledge_update
plan_delta
pre_execution_gate
mutation_or_external_action
validation
```

The experiment does not require private chain-of-thought. It requires observable, machine-readable state transitions sufficient to reconstruct whether discovery occurred before action and whether discovered evidence changed the externally declared state or action plan.

## Failure semantics

A layer MUST fail closed when:

- a child root cannot be resolved;
- an interval is incomplete;
- ordered hash verification fails;
- predecessor continuity fails;
- scope identity does not match;
- an upper layer claims evidence not present below;
- live and replay roots diverge for the same fixed run;
- reconstruction requires evidence classified UNOBSERVED or NOT_ESTABLISHED.

## Authority boundary

```text
receipt != authority
coverage != custody acceptance
custody != execution
reconstruction != activation
live projection != governance
higher-level inclusion != endorsement of every descendant semantic claim
```

Applicable transition elements and governing policy determine authority effects independently.

## Canonical implementation mapping

```text
repository-level ledgers
  -> repository-local schemas / receipts / experiment records

organization-level ledger/root
  -> <org>/.github organizational boundary and aggregation surfaces

ecosystem-level ledger/root
  -> master-records/orchestration organization record and reconstruction surfaces
```

## Required validation

A conforming implementation must demonstrate:

1. two or more granular repository receipts aggregate into a repository root;
2. that repository root is included in an organization root;
3. that organization root is included in an ecosystem root;
4. top-down reconstruction reaches the exact source receipts;
5. bottom-up inclusion proves the exact ecosystem root;
6. receipt reordering breaks ordered-root verification;
7. missing descendant evidence fails closed;
8. live and replay projections produce the same transition order for a frozen run.

