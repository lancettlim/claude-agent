# Agentic Development Loop

Guidance for driving this repository's work forward with Claude Code's
`/loop` skill, iteration by iteration, against `todo.md`.

## Why a loop

This repo has no build system or test suite to gate work yet, so the safest
unit of agentic progress is one `todo.md` checklist item per iteration:
implement it, verify it, check it off, commit. Running that as a `/loop`
lets unattended iterations make steady, reviewable progress instead of one
large uncontrolled batch of changes.

## What each iteration does

1. Read `todo.md` and pick the next unchecked item, in phase order (Phase 1
   before Phase 2 before Phase 3, then release-readiness items).
2. Implement just that item, consulting `dataset-spec.md` for the relevant
   schema, key, or contract details.
3. Verify the change (run any available lint/test/validation step; for
   docs-only changes, re-read the edited file for consistency).
4. Check the item off in `todo.md` and commit.
5. Stop the iteration there — one checklist item per turn, not a batch.

## Starting the loop

```
/loop 20m Work the next unchecked item in docs/todo.md: implement it,
verify it, check it off, and commit. Stop after one item.
```

Adjust the interval to match how long a single checklist item realistically
takes; prefer a longer interval over polling faster than iterations
complete.

## Stopping conditions

- All checklist items in `todo.md` are checked off.
- An item can't be completed without a decision only the user can make
  (e.g. an open question from `prd.md`) — stop and surface the question
  instead of guessing.
- Three consecutive iterations make no forward progress on the same item —
  stop and report why, rather than looping indefinitely.
