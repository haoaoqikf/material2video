## Context

See [proposal.md](proposal.md) and the four delta specifications. The existing v2 project contract already derives core review from risk, binds evidence to the current cycle, and has G5/G6 as distinct project gates. The current review policy nevertheless assigns G5 a mandatory `rough` independent review, and the diagnosis contract blocks all scene-code exploration until the full storyboard is complete.

## Goals / Non-Goals

**Goals:**

- Keep G5 as an all-film production check while making its review type internal.
- Derive independent calls from triggered core risks plus G6; keep split-final and failure escalation.
- Allow scoped, low-cost prototypes before a complete storyboard without confusing prototype evidence with final approval.
- Remove duplicated procedural requirements from the material2video entry and stage references.
- Capture lightweight, evidence-based process learnings in the normal production notes.

**Non-Goals:**

- Do not change financial-timeseries or housing-timeseries workflows.
- Do not modify any work under `videos/`, render videos, or rewrite example delivery history.
- Do not add a review-plan field or CLI export gate.
- Do not weaken factual, licensing, deterministic QA, core-risk, current-candidate, or issue-closure requirements.

## Decisions

1. **Make G5 internal in the shared gate source.** Set G5's review classification to `internal`, make its policy requirement have zero independent reviewers, and derive default call counts as `core + final`. Keep G5's prerequisites, evidence registration, whole-film internal scope, and ability to reopen G4 issues. This centralizes behavior in the existing policy rather than adding an exception to report import or a second review-plan field.

2. **Keep the risk catalog authoritative.** G2/G3/G4 risk-triggered observations remain independent and occur before expansion of the affected high-investment implementation. G6 remains one fresh reviewer by default; `split-final`, `substantive-dispute`, and `repeated-failure` keep their current escalation behavior.

3. **Use one evolving prototype where it answers the question.** A creator may start an isolated scene prototype once the subject and question are clear. The prototype's declared fidelity limits what it proves. An independently created design frame or animatic remains available when the corresponding risk needs it; neither is a universal prerequisite.

4. **Keep review evidence concise by role.** G5 records the actual whole-film range, findings, issue IDs, and uncovered limits. Independent review coverage records what that reviewer actually observed. Hashes, evidence provenance, current-candidate binding, and valid failure closure remain unchanged.

5. **Add process learning to the existing production notes.** Add an optional concise retrospective template to the shared review guidance; do not add a runtime field, new ledger event, or CLI gate. Require evidence or mark estimates, and treat a single production as preliminary.

6. **Do not rewrite historic works.** New behavior applies to cycles started after the shared workflow update. Existing records remain historical evidence and no work folder is migrated as part of this change.

## Risks / Trade-offs

- [Less independent scrutiny before final delivery] → Keep all risk-triggered core reviews, require full current-candidate G6 coverage, and preserve escalation paths.
- [Internal G5 could become a cursory checkbox] → Require actual scope, findings, uncovered limits, and issue references; do not accept an empty pass statement.
- [Early low-fidelity prototypes could be over-interpreted] → Record the question and fidelity, and restrict each conclusion to what its evidence can show.
- [Policy change affects status calculations for in-progress cycles] → Do not edit their work materials; preserve event history and make the new status derive from the revised shared policy. Verify current-policy behavior on isolated synthetic test fixtures.
- [Design mechanisms may not transfer across subjects] → Record conditions and limitations, and label one-work observations preliminary until a second distinct production confirms transfer.
