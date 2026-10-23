# An inventory, as exported

A made-up insurer's application portfolio export and its integration list, in
the columns and the words a portfolio tool uses, and the mapping that brings
them into the model. It is the worked example for `terrane import csv --map`
([AAC-15](../../00_METHOD/AAC-15_ADOPTING.md#as-it-was-exported-with-a-mapping)),
and the engine's tests import it into an empty model on every run, so it
cannot drift from what the importer accepts.

| File | What it is |
|---|---|
| `application_portfolio.csv` | Ten applications: `App ID`, `Lifecycle Status` (`In Production`, `Retired - pending`), `Business Criticality` (`Tier 1`), the owning department by name, hosting as the tool says it (`Data Center`, `Vendor Hosted`), and two columns nothing reads |
| `integrations.csv` | Eight integrations between those applications, each end named as the portfolio names it |
| `mapping.yaml` | Which column is which field, which value is which of the model's, and how a row becomes an id |

Into an empty model (`terrane clear --yes` first, or a sandbox):

```bash
cd 50_ENGINE && python -m terrane import csv --from ../60_SOURCES/inventory --map ../60_SOURCES/inventory/mapping.yaml
```

It makes five org units, one per department the applications name; ten
systems, `SYS-POLICY-ADMINISTRATION` and the like, each keeping its `App ID`
in `cmdb_ci_sys_id`; and eight interfaces whose ends resolve to those systems
by name. Nothing is held back and no column is left out.

Into the shipped model it imports too, beside the sample estate, and holds
one interface back: the sample already has a system called General Ledger
(`SYS-GL`), so `Premium postings`, whose target is named that way, names two
systems and is not guessed at. That is the report working; the result is not
a model anyone should keep. To see a value the mapping does not place, change
a `Tier 2` to `Tier 4` in a copy of the portfolio and import the copy.
