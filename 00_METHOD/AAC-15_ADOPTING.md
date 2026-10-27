# AAC-15: Adopting It

This is for the organization that has seen the demonstration and wants its own:
where to start, what the first week and month look like, and where the
repository is ready for that and where it is not, measured by doing it.
[AAC-01](AAC-01_OVERVIEW.md) says where the effort goes;
[AAC-05](AAC-05_CHANGE_FLOW.md) says how change flows once it is running. This
is the part in between.

## Who it needs

- **An owner for the repository.** One architect, or a small team, who reviews
  the pull requests and answers for the warnings.
- **Whoever holds the inventory.** A CMDB, a spreadsheet, an export from an
  application portfolio tool. The first model comes from there.
- **The product teams,** for the five intake answers in AAC-05, once it runs.

Nothing has to be installed for the first two weeks. Python 3.10 or later
runs the engine and the app; the app binds to the machine it runs on.

## The first day: an empty model that passes

There are two ways to start. The one this chapter grew up with is a copy of
this repository with the sample taken out, below. The one that suits an
organization with many people on one estate is a repository of its own --
created in Azure DevOps, GitHub or wherever its code lives, and cloned by
each person -- with terrane installed from pip and nothing of terrane's in
the repository:

```bash
pip install terrane
```

```bash
terrane init --name "Contoso Architecture" --governance https://dev.azure.com/contoso/arch/_git/governance --governance-ref v1.0.0
```

`terrane init` writes `10_MODEL/model.yaml`, a README and a `.gitignore`, and
keeps the README the new repository started with. Credentials never belong
in the repository, and the `.gitignore` says so from the first commit: `.env`
files, keys and certificates are left out, and an ignore file the repository
already had keeps every line of its own and gains the ones it lacked. A
connection names where its secret lives, an environment variable or a
secrets manager, never the secret. The settings it writes
read the shipped library and the shipped views from the installed package
(`shipped_library: package`, `shipped_views: package`), pin the terrane
releases the estate is checked with (`requires_terrane`, this minor
release by default), and name the organization's governance repository and
the revision it is checked against. Everyone on the estate installs a
terrane in range; `terrane validate` says so as an error when someone has not,
since a change checked by another release can pass for one person and fail
for the next. Raising the pin is a change of its own. A shipped view the
estate has no use for -- the sample's harvested estate, its change evidence
chain -- is left out by name, `shipped_views: {from: package, without:
[harvested-estate, change-evidence-chain]}`, and one it wants drawn
differently is written into `30_VIEWS` with `replaces:` and the shipped
view's id. A shipped view that selects nothing in the estate is a warning,
`view.shipped_nothing`, since nobody on the estate can edit it; the
estate's own views are held to the error they always were. The pictures go
under `70_ARTIFACTS/`, which the `.gitignore` keeps out: committed, two
people's renders would conflict on every change.

The app does the same from its estate menu, the estate's name above the
search: **Start a new estate** asks a name and a folder and runs the same
`init_estate` the command does, then opens the new estate in place of the
one that was open, on a first page of three steps (bring in the inventory,
see what the diagrams need, draw). **Join one your team keeps** clones and
fetches the governance as `terrane connect` does, and **Open a folder**
opens an estate already on the machine; the menu lists the ones this
browser has opened. Nothing about the estate that was open changes, and
the sample opens on a line saying it is the sample, with a button to start
your own.

Everyone else on the estate connects to it once:

```bash
terrane connect https://dev.azure.com/contoso/arch/_git/estate
```

That clones the estate, and fetches the governance repository it pins into
`.terrane/governance/` at the pinned revision, read-only and never
committed; in a clone made from Azure DevOps's own page, `terrane connect`
with no address does the second part alone, and a raised pin is one more
`terrane connect` away. Signing in is git's: the credential manager Git
for Windows ships already knows Azure DevOps and GitHub, and terrane holds
no password or token.

The rest of this chapter is written from a copy of the repository, and
holds for either.

```bash
cd 50_ENGINE && python -m terrane clear
```

```bash
python -m terrane clear --yes
```

The first says what would go; the second takes the sample estate out: every
record under `10_MODEL` but the model's own settings, and the two settings
that name its records -- what the card issuer answered the library and how
it holds the patterns (`answers` and `patterns`, below). The library, the
views, the method and the engine stay. `--keep org_units` (or any entity
type) leaves that part in place as a starting shape to correct.

```bash
python -m terrane validate
```

No errors. On the shipped repository this said twenty-five before this was
written down: every product shape wanted a landing-zone service the empty model
did not have, and each part of each shape said so as an error of its own. Now
each shape says once that it is waiting for a landing zone, and what it will
need from one (`library.no_landing_zone`), and that is a warning.

On an empty model the warnings list what the estate has not yet written
down: each product shape names the landing-zone services it needs and that
the model does not hold yet, and each view says it has nothing of its kind to
draw. They do not fail the gate.

Two things the sample estate did that an organization's model does not:
`terrane refresh` copies the export into `90_EXAMPLE/csv`, which is what the
engine's own tests are seeded from, and the spelling test reads the model's
prose. Both happen only while `model.yaml` says `sample_estate: true`, and
`terrane clear` takes that line out, so the tests keep testing the engine against
the sample whatever your model holds, and a model written in British English
is not failed for it.

Then name it: `name` and `description` in `10_MODEL/model.yaml` are what the
app's sidebar and every exported diagram say.

## The first week: the inventory

An inventory comes in one of two ways: as it was exported, with a mapping that
says what each of its columns, values and codes is in the model's words; or
shaped by hand into metamodel v2 CSVs. The mapping is the shorter road for
anything exported from somewhere else, and it stays beside the export for the
next one. Org units come first either way, because every system names the org
unit that owns it.

A system needs five things, and an import without them loads but fails the
gate:

| Field | What it takes |
|---|---|
| `system_id` | An upper-case id in parts, `SYS-POLICY-ADMIN`. An inventory's own codes (`APP001`, a ServiceNow sys_id) go in `cmdb_ci_sys_id`, not here. |
| `name` | What people call it. |
| `status` | Proposed, Planned, Active, Deprecated or Retired. |
| `owner_org_id` | An org unit in the model. |
| `criticality` | High, Medium or Low. |

### As it was exported, with a mapping

```bash
python -m terrane import csv --from path/to/the/export --map path/to/mapping.yaml
```

[`60_SOURCES/inventory/`](../60_SOURCES/inventory/README.md) is a worked one: a
made-up insurer's portfolio export -- ten applications, each naming the
department that owns it -- and its integration list, in the columns and words a
portfolio tool uses, with the mapping that brings them in. It makes five org
units, ten systems and eight interfaces, and the gate finds nothing wrong with
any of them.

A mapping names each kind of record it makes, and under each:

| Key | What it says |
|---|---|
| `file` | The inventory file, in the `--from` folder: a `.csv`, or an `.xlsx` workbook. Two kinds may read one file: the sample's departments come from the column each application names its owner in, and rows naming the same department are one org unit. |
| `sheet` | The sheet of a workbook the rows are on. Left out, the first sheet with a header row; a title or a note above the header is passed over. |
| `columns` | Which column is which field: `Business Criticality: criticality`. A column can fill two: `Hosting: [hosting, cloud_provider]`. |
| `ignore` | Columns read by nothing, on purpose. Any other column the mapping does not read is listed as left out. |
| `values` | Per field, which of the inventory's values is which of the model's: `Tier 1: High`, `Retired - pending: Deprecated`. Case and spacing are set aside, a value that is already the model's needs no line, and a value mapped to `""` leaves the field empty. |
| `defaults` | Per field, the value when the inventory's is empty or there is no column: `status: Active` for departments, which no export gives a status. |
| `id` | How a row becomes an id: `{prefix: SYS-, from: name}` makes `SYS-POLICY-ADMINISTRATION` of `Policy Administration`, and `from: code` slugs the code instead. Or map a column to `system_id` when the inventory already holds ids in the model's form. |
| `code` | The column holding the inventory's own id (`APP001`, a sys_id). Kept in `cmdb_ci_sys_id` on a system, where the drift report looks first; on any kind, matched when another row names this one. |

A field that points at another record -- `owner_org_id`, an interface's two
ends -- takes the record's id, its name or its inventory code, as an export
names it: `Underwriting Technology` in the owner column finds the org unit of
that name, in the model or in the same import. Only case and spacing are set
aside, and a name two records share finds neither.

Nothing is guessed. A value the mapping does not place and the metamodel does
not list, a reference to nothing, a required field left empty: each holds its
row back, and the report names the field, the value and the rows.

```
Held back; nothing of these rows is written:
  system criticality: 'Tier 4' is not High, Medium or Low, and the mapping does not say which it is (APP002)
  system owner_org_id: 'Marketing' is no org unit in the model or in this import (APP003)
```

The answer is a line in the mapping and a second run, which writes the held
rows and leaves alone everything the first one wrote. A row that names a held
row is held with it. Two rows that make the same id and say different things
are a conflict and neither is written: which is the real one is for the
inventory to settle, or for the mapping, by making ids from the code. A later
export in which an application was renamed makes a new id of the new name; its
code is already on the model's record, so it is reported and not made a second
time, and a row naming it by the new name finds that record. A mapping that is
wrong in itself -- a field a system does not have, a value mapped to one the
metamodel does not list, a column the file does not have -- is refused before
anything is written, every problem in one message;
`40_SCHEMAS/import_mapping.schema.json` flags the first two while it is typed.

An inventory's own values are often words YAML reads as something else:
`Yes`, `Off`, `01`, `1.50`. Quote them (`"Yes": Active`). Left bare, one YAML
reader takes `Yes` for true and another for the text, so a mapping with one is
refused under either, naming the line.

Relation tables are not mapped: a `relations/` folder of v2 CSVs comes in on a
run without `--map`.

### From the app: Settings, Sources

The same mapping, made by choosing rather than typing. Drop the export on
**Settings > Sources**, a CSV or a workbook, and three steps follow, none of
which writes anything:

1. **Columns.** Each column with what it holds and the field it goes to,
   filled in from the column names for you to check: `Application Name` is
   the name, `App ID` the export's own id kept for matching, `Annual Run
   Cost` left out. A column can fill two fields. Beside it, what a record of
   that kind needs and where each comes from; one the file does not have is
   chosen once for every row. A column of owners can make the org units it
   names, as the sample's mapping does; when none of its names is an org
   unit the estate holds yet -- every new estate's first import -- that box
   starts ticked, since left off it held back every row, and an untick is
   kept.
2. **Words.** Each of the export's words for a field with a fixed list, with
   how many rows say it: `In Production` is Active. A word that is already
   the model's needs nothing, and one left unmatched holds its rows back.
3. **Review.** Every record it would add, what is already in the model and
   left alone, the rows that wait and why, and what the checks would newly
   say once it is in, worked out on a copy of the model held in memory.

**Bring in** writes the records as the command line would, and **Keep this
as a source** puts the export and its mapping in a folder of `60_SOURCES`
with a note of when it last came in, so the next export comes in with one
click and `terrane import csv --map` reads the same file. A CMDB export is
listed there too, as a source that compares rather than brings in: what
differs is counted and opened in Checks, and nothing is written either way
(AAC-06).

### Shaped by hand, as metamodel v2 CSVs

One file per entity type, named for the type: `org_units.csv`, `systems.csv`,
`interfaces.csv`. The columns are the field names; `90_EXAMPLE/csv` has one of
each to copy the header from.

```bash
python -m terrane import csv --from path/to/your/csvs
```

A column that is not a field is listed as left out -- an inventory always has
some -- and a record already in the model is reported and left alone. Run it
again after fixing the CSVs; nothing is written twice.

### Then the gate

```bash
python -m terrane validate
```

Measured with three systems and an org unit, five errors are left, and they
are of two kinds. Two views are about named systems in the sample estate
(`harvested-estate`, `change-evidence-chain`). Three wait on something the
inventory did not fill: `tiered-architecture` draws systems with a
`network_zone`, `vendor-exposure` systems tagged `vendor` or `third-party`,
and `parts-in-use` systems a part of the library made. A business domain's
landscape is not among them: `domain-landscape` is drawn for each domain your
own systems name. Every view of
a layer not brought in yet -- capabilities, processes, people, data -- says
`view.nothing_yet` and waits; on the shipped repository those were thirty-five
more errors.

Two of those are views written about the sample estate: a drawing of the
systems it harvested from its business layer, and of the evidence behind one of
its changes. Open each in the app and press **Edit view**: the composer shows
what it filters on. Or delete the ones you will not use. Every other view
follows your data as it arrives.

Connections come next. An `interfaces.csv` imports like the rest; on the
drawing, dropping one system on another offers every way the two can be
connected, an interface among them, and the form arrives filled in.

### What the diagrams need

A portfolio export has names, owners, a lifecycle and where each system is
hosted, and very little a diagram is drawn by: Tiered Architecture draws the
systems with a `network_zone`, the Application Landscape boxes them by
`company_domain`, Integration Architecture by `system_category`. Each view
says what it reads, worked out from its own query (`terrane/needs.py`), so a
view the estate writes says it as the shipped ones do:

```bash
python -m terrane needs
python -m terrane needs tiered-architecture
```

The first is every diagram's state -- full, thin, nothing to draw yet, or
drawn for one thing at a time -- then the fields to fill with how many
records lack each and which diagrams read them, the kinds of record the
estate has none of, and the lines. The second is one view. A blank counts
where it is a gap: the field the clause asks to be filled, or one every
record of the type must have; a technology service with no cloud account
may be SaaS, a capability at the top of the map has no parent, and neither
is counted.

In the app the same list is **Checks > What the diagrams need**; a diagram
that draws nothing says, in place of the drawing, what it draws and what
the records lack, and a thin one says it in a line over the drawing and in
**What it needs** beside it. **Set on many** lists the records lacking a
field, with what a person decides by beside each name (hosting, owner,
category), narrows them by any of those, and sets one value on the ticked
ones in one save, each record changed where it lives as a save of one
would change it; **Undo** puts every file back, line endings and all.
Measured on 2026-10-20 with a 320-application export: Tiered Architecture
drew nothing until network zone was set on the 82 on-premise systems in one
save, and the landscape gained its first boxes four business domains later.

## The first month: making it yours

- **Landing zones.** Record each cloud's shared services as technology
  services tagged `landing-zone`, with the `component_type` that says what
  each is, under whatever ids you use. The shapes name kinds -- a block bound
  `api-gateway: landing-zone`, a system that `uses: [secrets-manager]` -- so
  the shapes for that provider then land on your services, and their
  warnings go. A cloud you have no landing zone on is waited for once per
  shape and asks nothing else; a shape for a cloud you do not use can be
  deleted.
- **What the library asks of you.** Some parts need a record of yours that
  is not a kind of service: who owns the shared network path and identity
  federation, where a vendor's audit trail goes, which system takes landed
  files, which controls and policies govern a vendor tenancy and what it
  lands. Each is a parameter marked `estate: true`, answered once under
  `answers` in `10_MODEL/model.yaml`; the catalogs under
  `70_ARTIFACTS/library/` mark them "the estate's answer". A product on a
  part you have not answered is refused with the name of the answer to
  write, and the sample's `model.yaml` is a worked set.
- **The capability map.** Import it, or write it, and say which systems realize
  which capability; the Coverage report then lists the capabilities nothing
  realizes.
- **The kinds of thing you build.** `29_TYPES` names five kinds and the parts
  each always has. They are a starting vocabulary, not a standard; change them
  to how the organization builds.
- **The patterns.** Who owns each one, the decision that approved it and
  which of your controls it is designed to meet are yours, under `patterns`
  in `10_MODEL/model.yaml`; the shipped patterns say none of the three. Say
  them for the patterns you adopt, and delete the ones you would not
  approve. A control or an owner you name that the model does not hold is a
  warning (`pattern.unknown_control`, `pattern.unknown_owner`).
- **A library of your own.** To leave the shipped library as it came, so the
  method's next release is not a merge, name a folder of your own in
  `model.yaml` (`library_paths: [our-library]`) and write your patterns,
  parts and shapes there, in the same layer folders. One of yours replaces a
  shipped one only when it says `replaces:` with its id; anything else that
  reuses an id is an error naming both files. The app writes new parts and
  shapes there once it exists ([AAC-16](AAC-16_EXTENDING_THE_LIBRARY.md)).
- **The review.** `.github/workflows/validate.yml` runs the gate, the tests and
  the freshness check on every pull request, where GitHub Actions runs; the
  same commands run by hand or in another pipeline where it does not
  ([AAC-05](AAC-05_CHANGE_FLOW.md#ci)). A `CODEOWNERS` file over
  `10_MODEL/` folders is how an org unit reviews what it owns.
- **The CMDB.** `terrane cmdb drift` reads a ServiceNow CI export and lists what
  each side has that the other lacks ([AAC-06](AAC-06_CMDB_RECONCILIATION.md)).
  Quarterly is enough.

## Ready, and not yet

Measured on 2026-10-16 by doing it: an empty model from the shipped repository,
then three systems and an org unit of a made-up insurer's, imported as CSVs,
and the same insurer's portfolio export and integration list through a mapping.

| | State | What it rests on |
|---|---|---|
| Starting empty | Ready | `terrane clear`; the gate passes on an empty model (twenty-five errors before; none now) |
| Starting from the app | Ready | The estate menu starts an estate (`terrane init`), joins one (`terrane connect`) or opens one, and the app switches to it without a restart; an empty estate opens on its first three steps. Taking the sample out stays `terrane clear`, from a terminal. |
| Knowing what a diagram needs | Ready | `terrane needs`, and Checks > What the diagrams need; each diagram says it beside its drawing, and a field is set on many records in one save. |
| A repository of its own, terrane from pip | Ready | `terrane init`; the library and the views from the installed package, the release pinned and checked by validate, a governance repository pinned by revision. Measured on 2026-10-19 from a fresh install of the wheel: an estate started in a repository that already had a README, records written, adopted and drawn, and `terrane diff HEAD` read back. Before it, such an estate saw no views and no library. |
| Bringing an inventory | Ready for metamodel v2 CSVs | Reports columns it leaves out and records it leaves alone. Re-importing used to write reference-set files and the relations file whole; it adds to them now. |
| A drawing of what is there | Ready, with a look first | `terrane adopt FILE --dry-run --picture change.svg` draws what a drawing adds against the estate before anything is written. A thing the drawing calls by an id the estate does not use is added as new; the dry run lists the estate's records it probably is, by name, and `--same NEW=OLD` takes one, so the drawing's ledger joins the estate's and no second ledger is written. Nothing is joined by name unless a person says so. [AAC-17](AAC-17_DRAWING_FROM_PYTHON.md). |
| A raw CMDB or portfolio export | Ready, with a mapping | `terrane import csv --map`: which column is which field, which value is which of ours, how a code becomes an id, said once in a file beside the export. What it does not place is held back and named, never guessed; two rows making one id are a conflict. Relation tables still come as v2 CSVs. |
| Views | Ready, with a list | Views of a layer not brought in yet wait as `view.nothing_yet`. Five name the sample or a field an inventory rarely has; the composer retargets each in a few choices, or they are deleted. |
| Editing in the app | Ready for one person | Saves where each record lives; pins, hides and connections from the drawing; the composer for a view. |
| Editing by many people | Partly | Everyone works in a clone of one estate repository on a pinned terrane, records one to a file, and changes go up as pull requests, which is the review. The app writes to the working tree and knows nothing of branches, and the relations it draws all go into one file, where two branches meet. |
| Sharing read-only | Ready, with a caution | The Pages build publishes every view and record to anyone with the link, private repository or not. An organization's estate wants that behind its single sign-on. |
| The engine's tests and CI | Ready | Seeded from the sample whatever the model holds, once `sample_estate` is gone. |
| The library | Ready | No shipped shape, part, pattern, block, build type or connection kind names a record of the sample's, and a test holds it. A shape or part names a kind, which your landing zone answers, or asks you, under `answers`; who owns a pattern and what it meets is yours, under `patterns`. Measured on 2026-10-18 on the health system in `90_EXAMPLE/thurman-health`: the eighteen records it held under the sample's ids are its own choices -- eleven kept as they were, seven renamed to what a hospital calls them, and its private egress given to a different team than the card issuer's -- and its warnings fell from 112 to 38. |
| A library of your own beside the shipped one | Ready | `library_paths` in `model.yaml`; a record replaces a shipped one only by saying `replaces:`, the catalogs and the Library say what came from where, and the app saves into it. [AAC-16](AAC-16_EXTENDING_THE_LIBRARY.md). |
| The business layer import | Not yet, for anyone else | `import_business_layer.py` reads one sibling repository's layout. |
| The license | Ready | `LICENSE` is PolyForm Shield 1.0.0. An organization uses it, changes it and shares it for its own work without asking anyone; what no one may do is offer it, or something built from it, as a product or hosted service that competes with Terrane. |

## What would close the rest, in order

1. **terrane working the estate's repository.** `terrane connect` clones it
   and fetches the governance at the pinned revision, and is in; left are a
   sync that pulls
   what others merged and draws it as a change; every save a commit on the
   person's own branch; and a propose that validates, pushes and opens the
   pull request in Azure DevOps or GitHub. Every write the app makes is
   already a file change with a reason, which is what each commit says.

The three that stood first on this list are in, all above: the mapping
(`terrane import csv --map`), a library of your own beside the shipped one
(`library_paths`, [AAC-16](AAC-16_EXTENDING_THE_LIBRARY.md)), and the sample
out of the library (`answers` and `patterns` in `model.yaml`, kinds the
landing zone answers). The last was measured the way the rest were, by
doing it: the health system was built on the shipped shapes first, and every
sample record those shapes made it hold was then taken out of the library.
