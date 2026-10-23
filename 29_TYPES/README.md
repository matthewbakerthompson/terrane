# Build types

The kinds of thing the organization builds, and the standard build of each.

The library below this folder answers "what is this made of" at three sizes:
a component type (`25_COMPONENTS/`) is one service, a block (`26_BLOCKS/`) is
the handful that arrive together, a part (`28_MODULES/`) is a piece of a
product. A shape (`20_ARCHETYPES/`) is a whole product on one provider. What
none of them says is which parts a *kind* of product has, whoever hosts it,
and which of those are negotiable. That is what a build type says.

```yaml
- build_type_id: digital-product
  name: Customer-facing digital product
  description: >
    A web or mobile front end, the API behind it, its own datastore, and an
    event publisher onto the enterprise bus.
  requires: [api-service]                                  # every one has these
  includes: [web-channel, relational-datastore, event-publisher]   # unless there is a reason
  offers: [public-web-entry, async-worker, object-store]   # additions, when needed
  shapes:                                                  # the type on each provider
    AWS: aws-product-onboarding
    Azure: azure-digital-product
    GCP: gcp-digital-product
```

Two files: `build-types.yaml` for the kinds of product (a digital product,
a platform service, a bought SaaS capability, a data product, a shared hub)
and `application-types.yaml` for the kinds of application (an internal tool,
a mobile application, an event-driven service, a batch application, an
integration adapter, an AI inference service, a reporting application). An
application type requires the standard application kit from
`28_MODULES/applications.yaml` and offers the components an application of
that kind may add; it has no shape of its own and is assembled from its parts
against the landing zone.

## What it does

**In the Assemble panel** the first question is what kind of thing is being
built. Choosing a type picks the shape for the chosen provider where there is
one, or the type's parts where there is not; the required parts are locked,
the included ones are ticked, the offered ones are listed as additions, and
every other part is folded away. What the parts run on is answered by the
provider's landing zone, so a product on AWS gets the load balancer, the
container platform and the secrets manager the organization already runs
there without anyone choosing them. The panel lists every departure from the
standard build as it is made.

**In the model** a product records its type as `build_type`. `terrane validate`
reports where a product departs from its standard, as warnings:

| Code | Meaning |
|---|---|
| `types.missing_required` | A part every build of this kind has is not in the product |
| `types.deviation` | A part the type includes by default was dropped |
| `types.unlisted_part` | The product has a part the type neither includes nor offers |

A deviation is not an error. It is the thing a design review should see
without having to ask, written where the review will find it.

**In the catalog** `terrane render` writes `70_ARTIFACTS/library/build-types.md`:
each type, its parts, its shapes, and the products on it with their
deviations.

## Rules

- `requires`, `includes` and `offers` name parts from `28_MODULES/`, and a
  part appears in at most one of them.
- `shapes` maps a provider to a shape of that provider, or `any` to a shape
  that lands on no cloud. Every shape mapped must compose every required part.
- A product on a type with no shape for its provider is assembled from the
  type's parts; `terrane validate` holds it to the same standard.
