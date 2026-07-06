# Agentic Development Loop

Guidance for driving this repository's work forward with Claude Code's
`/loop` skill, iteration by iteration. Four loop modes cover the recurring
kinds of work on a docs-and-scaffolding repo like this one: shipping
checklist items, grooming the backlog, managing tech debt, and designing
what comes after v1. Run one mode at a time — each has its own stopping
conditions, and mixing modes in one loop makes it unclear what an iteration
is supposed to finish.

## Why a loop

This repo has no build system or test suite to gate work yet, so the safest
unit of agentic progress is one change per iteration: do it, verify it,
record it, commit. Running that as a `/loop` lets unattended iterations make
steady, reviewable progress instead of one large uncontrolled batch of
changes.

## Implementation loop

Ships items already on the `docs/todo.md` checklist.

1. Read `docs/todo.md` and pick the next unchecked item, in phase order
   (Phase 1 before Phase 2 before Phase 3, then release-readiness items).
2. Implement just that item, consulting `docs/dataset-spec.md` for the
   relevant schema, key, or contract details.
3. Verify the change (run any available lint/test/validation step; for
   docs-only changes, re-read the edited file for consistency).
4. Check the item off in `docs/todo.md` and commit.
5. Stop the iteration there — one checklist item per turn, not a batch.

```
/loop 20m Work the next unchecked item in docs/todo.md: implement it,
verify it, check it off, and commit. Stop after one item.
```

Stop when: every checklist item is checked off, an item needs a decision
only the user can make (surface it instead of guessing), or three
consecutive iterations make no progress on the same item.

## Backlog grooming loop

Turns gaps and open questions into new, well-formed `docs/todo.md` items
instead of leaving them implicit.

1. Scan `docs/dataset-spec.md`, `docs/prd.md`, `docs/data-sources.md`, and
   any validation reports under `reports/validation/` for work that isn't
   yet represented as a `docs/todo.md` checkbox (new entities, unaddressed
   risks, open questions, newly deferred-then-revived sources).
2. Write each gap as one action-sized `docs/todo.md` item under the right
   phase heading, following the existing bullet style (imperative,
   references the concrete file/table/field it touches).
3. Remove or reword stale items that no longer match the current spec.
4. Commit the `docs/todo.md` update alone — this loop only edits the
   backlog, it doesn't implement anything.

```
/loop 30m Groom docs/todo.md: find one gap between docs/dataset-spec.md
and docs/prd.md and the current checklist, add or correct one item for
it, and commit.
```

Stop when: a full pass over the spec docs turns up no new gaps, or an item
would require a scope decision (add vs. defer) that only the user should
make.

## Tech debt loop

Cleans up drift between docs, inconsistent terminology, and scaffolding that
no longer matches how the repo is actually structured — without adding new
scope.

1. Look for one concrete piece of debt: duplicated text between docs,
   filenames or paths that no longer match reality, stale cross-references,
   placeholder READMEs that are out of date, or checklist items whose
   wording drifted from `docs/dataset-spec.md`.
2. Fix only that one thing. Don't bundle an unrelated improvement into the
   same iteration.
3. Verify by re-reading the changed file(s) and grepping for any other
   reference to what you changed (a renamed file, a reworded contract term)
   to make sure nothing was left stale.
4. Commit with a message describing the drift that was fixed, not just the
   diff.

```
/loop 20m Find one piece of doc drift or duplicated text in this repo,
fix just that one thing, verify no stale references remain, and commit.
```

Stop when: a full pass turns up no more drift, or the "fix" would actually
be a scope change (belongs in the backlog-grooming loop instead).

## Future goal design loop

Designs what comes after the current v1 scope, without starting to build it.

1. Re-read `docs/prd.md`'s open questions and non-goals, and
   `docs/dataset-spec.md`'s deferred sources, for one candidate post-v1 goal
   (e.g. a deferred source, a milestone beyond M6, a non-goal worth
   revisiting).
2. Draft the goal as a short design note: problem, why it's out of v1 scope
   today, what would need to be true to bring it in scope, rough shape of
   the entities/contracts it would need.
3. Add it to a `## Future goals` section in `docs/prd.md` (create the
   section if it doesn't exist yet) rather than inventing a new file — keep
   the doc count harmonized.
4. Do not create `docs/todo.md` checklist items from this loop; that's a
   deliberate handoff to backlog grooming once a goal is accepted.
5. Commit the design note alone.

```
/loop 30m Draft one post-v1 future-goal design note in docs/prd.md's
"Future goals" section, based on an open question, non-goal, or deferred
source. Don't add docs/todo.md items. Commit.
```

Stop when: every open question/non-goal/deferred source already has a
design note, or a candidate goal needs a product decision (should we even
pursue this?) that only the user should make.

## Picking an interval

Match the interval to how long one iteration of the chosen mode actually
takes; prefer a longer interval over polling faster than iterations
complete.
