# AAC-05 — Change flow

This document covers how changes reach the model. The model goes out of date when it
sits somewhere the change does not, so an architect updates it second-hand, weeks late,
from memory. Within two quarters it is stale.

So the design constraint is: **the model has to be edited by the people making the
change, at the time they make it.** Everything below follows from that.

## The flow

```
  design review / intake
          |
          v
  branch + edit 10_MODEL
          |
          v
  terrane validate  ---- fails ----> fix
          |
          v
  terrane render + export
          |
          v
  pull request  ---- architecture review
          |
          v
  merge -> publish
```

## Two doors

A delivery engineer editing YAML in a pull request and a product owner clicking through
the app are doing the same thing to the same files. The app (`python 80_APP/app/server.py`)
exists because the second group is larger than the first, and so that keeping the model
current does not fall to one person.

Whichever door a change comes through, it lands as a file change in the working tree,
goes through `terrane validate`, and arrives as a reviewable diff. The app does not
bypass the gate.

## Who edits what

| Change | Who | Typically |
|---|---|---|
| New product or service | The delivery team, at design review | **New** in the app, or one instance file naming an archetype |
| New system inside an existing product | The delivery team | **New** in the app, an `extra` block, or a new system file |
| New integration between products | Either side, one of them | A row in `10_MODEL/interfaces/` |
| Retirement | Whoever runs the decommission | `status: Retired` on the entity. Not deletion — retired systems belong in the record |
| Ownership change | The receiving org | `owner_org_id` |
| New archetype, or a change to one | Architecture | Reviewed change, effect on instances checked |
| New view | Architecture | Rare |

The bulk of it is delivery teams making small edits. That is the intended distribution.
If architecture is making most of the edits, the model has drifted out of the path of
change and the flow above is not running.

## The gate

`terrane validate` on every change before it is merged, in CI or by hand
([CI](#ci) below):

```bash
cd 50_ENGINE && python -m terrane validate
```

Exit 1 on any error. Warnings are printed and do not block. `--strict` promotes
warnings to failures, which suits a mature model but not a new one, where importing a
hundred systems produces many warnings.

Warnings are the governance backlog. Track the counts rather than the individual lines:
unowned systems, orphaned systems, systems with no CMDB link. Those three numbers should
go down over quarters as the estate matures.

## Rendering and generated output

`70_ARTIFACTS/` is committed. That is a trade-off:

- **For:** diagrams are reviewable in the pull request. A reviewer sees that adding a
  system changed the landscape view, in the same diff. Reading the current state needs
  no tooling, for people who do not clone the repository.
- **Against:** merge conflicts in generated files.

The conflict rule: **never resolve a conflict in `70_ARTIFACTS/` by hand.**
Take either side, then re-run `terrane refresh` and commit the result. A hand-merged
generated file no longer matches the model.

If the conflicts become frequent, the alternative is to stop committing artifacts and
publish them from CI instead. Make that a recorded decision rather than hand-editing
generated files.

## Publishing

Generated output feeds the existing paths rather than a new one:

| Target | Command | Notes |
|---|---|---|
| Docs / TechDocs / SharePoint | `terrane render` | `70_ARTIFACTS/docs/*.md` embed Mermaid, which renders natively in all three |
| A picture to paste, with no browser | `terrane render` | `70_ARTIFACTS/svg/*.svg`, the view as the app draws it; `--png` rasterizes through resvg-py where it is installed |
| Backstage catalog | `terrane export backstage` | A projection of the model, not a second source |
| Collibra / CSV pipeline | `terrane export csv` | metamodel v2 layout, as the existing validation expects |
| Structurizr | `terrane render` | `70_ARTIFACTS/structurizr/workspace.dsl` |
| Downstream tooling | `terrane export json` | The whole resolved model in one document |

## CI

`.github/workflows/validate.yml` runs on every pull request and every push to `main`:
the gates, the test suite, and a render and the exports, failing if any of the
generated output differs from what is committed — which is what catches the pull
request that edits the model and forgets to re-render. A separate job parses every
generated diagram with the real Mermaid parser, and another runs the suite with
PyYAML installed so the parity test executes.

The workflow needs GitHub Actions, and in this repository Actions has been off
since 2026-10-18. The same checks are run by hand before `main` is pushed:

```bash
cd 50_ENGINE
python -m terrane validate
python -m terrane --root ../90_EXAMPLE/thurman-health validate
python -m terrane refresh            # then git status: nothing left to commit
python -m unittest discover -s tests
```

None of them needs GitHub.

## The intake question

For a new product or service, the intake conversation needs five answers. Ask them at
design review, before anything is built, because they are all decisions somebody is
making anyway:

1. **What archetype is it?** If none fits, that is worth knowing early — either it is
   novel, or it is about to be built non-standard by accident.
2. **Who owns it?** An org unit that exists, not a person and not a project.
3. **What capabilities does it realize?** If the answer is none, ask again.
4. **What does it integrate with?** The cross-product interfaces, which are the
   expensive part and the part most often discovered late.
5. **What data does it hold, and is any of it personal?** Drives classification and the
   privacy view.

That is the intake form. It fits on one screen, and the answers are the model entry.

## When the model drifts

The model drifts in patches. The recovery is a reconciliation pass rather than a rewrite:

1. Run `terrane cmdb drift` — the `CMDB_ONLY` list is a candidate list of things the model
   has missed (see [AAC-06](AAC-06_CMDB_RECONCILIATION.md)).
2. Re-import from whatever inventory you have. `terrane import csv --from <dir>` adds what
   is missing and reports what already exists rather than overwriting it, so it is safe
   to re-run against a model people have been hand-editing.
3. Check the `graph.orphan` warnings — an orphaned system is usually one that was added
   and never connected.
4. Check `MODEL_ONLY` entries with old `last_reviewed` dates — these are candidates for
   retirement that were not reported.

Run the pass quarterly; without it, the model drifts until it has to be rebuilt from
scratch.
