# Thurman Health

A second example estate: a made-up regional health system, two hospitals, a
cancer center and thirty clinics, modeled with the same metamodel, engine,
library and views as the card issuer in `10_MODEL/`. It is here to show that
none of those was written for a card issuer only.

## What is in it

- **The clinical core.** One EHR for the hospitals and the clinics, the
  departmental systems that take its orders and send results back (laboratory,
  radiology, PACS and the image archive, pharmacy, oncology, the cancer
  registry), bedside device integration and the bed board.
- **Interoperability.** An HL7 interface engine every feed goes through, an
  enterprise master patient index, a FHIR API for the portal and for the apps
  patients authorize, and the regional exchange and reference lab outside the
  walls.
- **Four products on shipped shapes, unchanged.** The patient portal on the
  Azure digital product shape, video visits and the claims clearinghouse on the
  vendor SaaS shape, the clinical warehouse on the batch data product shape.
- **Data with HIPAA in mind.** Twenty-three data assets, each tagged with the
  standard it travels in (`fhir`, `hl7v2`, `dicom`, `ccda`, `x12`); nearly all
  of it protected health information, so nearly all of it Restricted.
- **A governance register.** Eight policies and eighteen controls: the HIPAA
  Privacy, Security and Breach Notification rules, business associates, records
  retention, Joint Commission patient safety goals, patient access, and state
  cancer reporting, with where the estate enforces each.
- **A business layer.** A two-level capability map of thirty-three
  capabilities, three value streams (emergency care, order to result, cancer
  care) with their stages, nine processes, ten actors and three flows (a lab
  result, an admission, a charge to its remittance).

Thirty-one systems, fifty interfaces, 249 entities and 458 relationships in
all, and thirty-three views.

## How it is held

The estate is a root of its own, beside the repository's:

| | |
|---|---|
| `10_MODEL/` | The model, laid out as the sample's is |
| `30_VIEWS/` | Thirty-three views. Thirty-two are shipped views copied unchanged, and a test holds them byte for byte to the originals; `cancer-care-capabilities` is the shipped value-stream view pointed at cancer care |
| `library/` | A library of its own, named in `library_paths`: the two connection kinds a hospital has and a card issuer does not, an HL7 v2 feed and a DICOM transfer. With them, every interface in the estate is of a kind |

It holds no copy of the shipped library. `shipped_library: ../..` in
`10_MODEL/model.yaml` says the shapes, parts, blocks, patterns and connection
kinds are read from the repository two folders up, so the products here are
built from exactly what the sample's are, and a change to the library is a
change to both.

Nothing generated is committed for it. The gate, `test_second_estate.py` and
CI's Mermaid parse hold it instead, and `70_ARTIFACTS/` here is ignored.

## Running it

```bash
cd 50_ENGINE && python -m terrane --root ../90_EXAMPLE/thurman-health validate
```

```bash
python -m terrane --root ../90_EXAMPLE/thurman-health impact SYS-INTERFACE-ENGINE
```

```bash
python 80_APP/app/server.py --root 90_EXAMPLE/thurman-health --port 8021
```

Every command takes `--root`; the app takes it too, and then opens on this
estate at http://127.0.0.1:8021 with its own name in the sidebar.

## What it answers the library

The shipped shapes and parts name no estate's records. Where they need one
of Thurman's they name a kind, which its landing zone answers, or ask, and
`10_MODEL/model.yaml` answers once for every product:

| Asked | Thurman's answer | The card issuer's |
|---|---|---|
| `platform_org`, who owns the private path to a vendor and identity federation | `ORG-INFRA`, Infrastructure and Cloud | its whole technology org |
| `data_org`, who stewards landed and curated data | `ORG-DATAENG` | the same id |
| `security_org` and `siem_system`, where a vendor's audit trail goes | `ORG-INFOSEC`, `SYS-SIEM` | the same ids |
| `ingest_system`, where landed files arrive | `SYS-CLINICAL-INGEST` | `SYS-DATA-INGEST` |
| `vendor_controls`, `vendor_policies` | `CTL-BA-DUE-DILIGENCE`, `POL-BUSINESS-ASSOCIATES` | third-party risk |
| `landed_data_controls`, `landed_data_policies` | `CTL-RETENTION`; `POL-RECORDS`, `POL-PRIVACY` | the same ids |

The Azure digital product shape binds the landing zone's API gateway,
cluster, database, monitoring and vault, and Thurman's are the services
tagged `landing-zone` in `tech_services.yaml`; its web channel signs in
through the landing zone's identity provider, `TS-IDENTITY`; the clinical
warehouse runs on the landing zone's warehouse and catalog. `patterns` in the
same file says who owns each pattern its products apply and which of its own
controls each meets.

Until the library asked, this estate held eighteen records under the card
issuer's ids so it could build on it -- three org units, two systems, eight
technology services, three policies and two controls -- and heard fifty-one
warnings about patterns owned by org units it does not have. Eleven of the
eighteen it kept as they were, because they read as well in a hospital;
seven it renamed to what a hospital calls them: Information Services
(`ORG-IS`, was `ORG-TECH`), the clinical ingestion (`SYS-CLINICAL-INGEST`),
the warehouse, catalog and identity platform by role, and business
associates rather than a bank's third-party risk (`POL-BUSINESS-ASSOCIATES`,
`CTL-BA-DUE-DILIGENCE`).

## What the gate still says

No errors, and thirty-eight warnings of three kinds:

- **The AWS and Google shapes wait for landing zones** this all-Azure estate
  will never have, once per shape (`library.no_landing_zone`), and the one AI
  part asks the Azure landing zone for a foundation model service it does
  not run (`library.landing_zone_gap`).
- **No CMDB was made up for it** (`cmdb.unlinked`).
- **Two gaps left on purpose** (`governance.no_control`): the clinical
  warehouse holds a copy of nearly everything and its pipeline and semantic
  layer record no control. The bed board, which holds names and locations,
  records none either; it is Confidential, so the gate does not ask, and the
  restricted data view does not show it.

## It is not real

Thurman Health is a made-up name for a made-up organization. The content was
drafted from the synthetic data of an earlier project by the same author. The
regulations the controls cite are real; what Thurman's policies say about them,
every owner, rating, volume, mapping and enforcement point, is invented to
exercise the mechanism, and none of it should be quoted. Vendors are named by
role ("Licensed EHR suite", "Clearinghouse vendor"); the cloud and data
platforms are named as the sample names them.
