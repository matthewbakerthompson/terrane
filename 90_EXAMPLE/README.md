# Example estate

The placeholder estate as metamodel v2 CSVs. `10_MODEL/` was seeded from exactly this,
so the two agree; keeping the CSVs alongside means you can rebuild the model from
scratch, or exercise the import path without inventing a fixture.

```bash
cd 50_ENGINE && python -m terrane import csv --from ../90_EXAMPLE/csv
```

Or **Import CSVs** in the app. Importing over a populated model reports every record
that already exists and changes nothing, so it is safe to re-run.

## What it is

A card-servicing estate: a mainframe ledger, an authorization switch, a couple of
in-house digital products, a bought disputes platform, a warehouse and a data product,
and three products mid-onboarding so the change and governance views have something
to show. Around forty systems once the onboarding shapes are flattened, the business
layer's capability map, value streams and org units, the governance register of forty
controls and ten policies with where the estate enforces them, and the patterns each
product applies.

The CSVs are a flattened export of the model, so archetype-generated entities appear
here as plain rows and the derived governance links carry their `basis`. That is what
a real inventory looks like on arrival, which is the point of exercising this path.

It is **not** a real organization and not a recommendation. Every owner, criticality
rating and capability mapping in it was drafted to exercise the mechanism. Nothing here
should be quoted.

## A second estate

[`thurman-health/`](thurman-health/README.md) is a made-up regional health system,
kept whole rather than as CSVs: a model and views of its own, read with the
repository's library through `shipped_library` in its `model.yaml`, and opened with
`--root` on any command or on the app. It is not the engine's test seed and nothing
copies it anywhere; `test_second_estate.py` reads it where it lies. It is here to show
the metamodel, the shapes and the views working for an industry the sample was not
written for.

## Why CSV as well as the model

Because the import path is the one that matters for adoption. Almost nobody starts from
nothing: you start from a spreadsheet, a Collibra extract or a CMDB dump, and the only
question that matters is whether the tool can take it. Keeping the seed in the format
real inventories arrive in means that path is exercised on every test run rather than
being a feature nobody tries until the day it matters.

## Replacing it

Take the sample out of the model and import your own:

```bash
cd 50_ENGINE && python -m terrane clear --yes
```

```bash
python -m terrane import csv --from /path/to/your/csvs
```

Keep this folder. It is the engine's test seed, not your model: the tests build their
sandbox from it whatever `10_MODEL` holds, and once `terrane clear` has taken the
`sample_estate` line out of `model.yaml`, `terrane refresh` stops copying the model's
export over it. Deleting it, or seeding it with your own estate, fails every test that
names a sample id. [AAC-15](../00_METHOD/AAC-15_ADOPTING.md) is the rest.

## Note on round-tripping

A CSV export is a flattened snapshot of the resolved model, so importing it produces
plain entities. Archetype linkage does not survive the trip — a system that came from an
archetype imports as an ordinary system. That is deliberate: an imported row carrying
`archetype` would be expanded a second time on load. Re-establish the linkage by hand if
you want it, or keep archetypes for what you create from here on.
