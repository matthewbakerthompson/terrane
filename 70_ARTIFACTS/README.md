# Generated output

Everything in this folder is produced by `terrane render`, `terrane export` and `terrane cmdb`.

**Do not edit anything here.** The next render overwrites it. If a diagram is wrong,
the model is wrong, or the view filter is wrong. Fix that.

**Do not resolve a merge conflict here by hand.** Take either side, re-run
`terrane render`, and commit the result. A hand-merged generated file no longer matches the
model, which is the exact failure this repository exists to prevent.

It is committed so that diagrams are reviewable in a pull request and readable without
running anything. That convenience is the only reason it is in version control.

| Path | Produced by |
|---|---|
| `INDEX.md` | `terrane render` — start here |
| `mermaid/*.mmd` | `terrane render` — raw diagram source |
| `svg/*.svg` | `terrane render` — the view drawn as the app draws it, for every diagram and map the engine can lay out; `INDEX.md` says which it cannot, and each `docs/` page carries its own under the Mermaid |
| `docs/*.md` | `terrane render` — diagram plus legend, for embedding |
| `structurizr/workspace.dsl` | `terrane render` — for the large landscape views |
| `export/csv/` | `terrane export csv` — metamodel v2 layout |
| `export/backstage/` | `terrane export backstage` — catalog entities |
| `export/model.json` | `terrane export json` — the whole resolved model |
| `cmdb/` | `terrane cmdb drift` — reconciliation report |
