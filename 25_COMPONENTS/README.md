# The component type library

A vocabulary of the things an estate is actually made of — load balancers,
object stores, message brokers, identity providers — so that "what is this box"
has an answer the model can use rather than one the reader has to infer from
the name.

## Why a library and not just a name

A `tech_service` called *Application Load Balancer* and one called *Application
Gateway* are the same kind of thing on two clouds. Without something saying so,
nothing can group them, count them, draw them alike, or tell you that a product
you are onboarding is missing one. A component type is what says so.

It carries four things a bare name cannot:

- **A category** — Compute, Network, Data, Security and the rest — which is
  what a technology stack view groups by and what a reviewer scans for gaps.
- **A shape**, so an infrastructure diagram reads like one. A queue is a queue
  on every diagram it appears on, whatever the cloud calls it that week.
- **What each provider calls it.** `alb` is Application Load Balancer on AWS,
  Application Gateway on Azure, Cloud Load Balancing on GCP. Naming the type
  rather than the product is what makes a cloud migration a re-parameterization
  instead of a re-drawing.
  The canvas's Add finds a type by any of these, and a part dropped into an
  account of a provider is recorded as that provider's `product`: the first
  product an answer offers, "Amazon EKS or ECS" offering two, unless the
  person picks the other.
- **Defaults** worth pre-filling: a load balancer lives at the edge, a database
  lives in the data tier, and having to remember that every time is how those
  fields end up empty.

## What it is not

It is not an icon set and it is not exhaustive. A hundred and nine types cover what
turns up in most estates, the AI services, the security tooling and the
enterprise applications included; the moment you need one that is not here, add it —
the file is the interface. A library that tries to name every managed service
of every cloud goes stale in a quarter and nobody maintains it.

Nor is it a constraint. `component_type` on a system or a tech service is
optional, and something with no type still draws. It buys grouping, shape and
defaults, and costs nothing when absent.

## The files

One file per category, so a diff is readable and two people adding types in
different areas do not collide. `40_SCHEMAS/component_type.schema.json`
describes the shape.

```yaml
- component_type_id: object-store
  name: Object store
  category: Storage
  applies_to: tech_services
  shape: cylinder
  description: >
    Durable blob storage, addressed by key rather than by path or query.
  providers:
    AWS: Amazon S3
    Azure: Azure Blob Storage
    GCP: Cloud Storage
    On-prem: MinIO or a NAS
  defaults:
    service_category: Storage
    network_zone: Private-Data
```
