# Building blocks

The unit architecture is actually done at.

Below this sits `25_COMPONENTS/`: a load balancer, a queue, a key vault. Too
small to design with — nobody assembles a workload by picking forty individual
services. Above it sits `20_ARCHETYPES/`: a whole product, fourteen entities
from six answers. Too big to reuse in a design conversation.

A **building block** is the handful of components that always arrive together,
with the relations between them and the constraint that holds them in place.
A public web tier is a CDN, a WAF and a load balancer — and a load balancer
with no WAF in front of it is a different risk posture, which is exactly the
sort of thing that should be visible rather than remembered.

## Why this is the modular unit

Five or six blocks compose a workload. The same block appears in the AWS
archetype, the Azure one, and freehand in a design review — so when the WAF
requirement changes it changes in one place, and every design that used the
block inherits it.

This is TOGAF's **Architecture Building Block**, and the useful half of TOGAF's
distinction is what makes it work here:

| | | |
|---|---|---|
| **ABB** | *a public web tier* | The block. What the design needs. |
| **SBB** | *CloudFront, AWS WAF, an ALB* | The `providers` map on each component type. |

The block never mentions a vendor. Resolving it against AWS gives one answer
and against Azure another, from the same block — which is what makes a cloud
migration a re-parameterization rather than a redrawing.

## What a block is not

**Not a pattern.** A pattern is a block plus the decision: what it is for, what
it costs, when not to use it. `private-egress-to-saas` is three components and
one paragraph, and the paragraph is the valuable part. Patterns live in
[`27_PATTERNS/`](../27_PATTERNS/README.md), and a block can be in several.

**Not an application.** A block is what a product runs on: technology
services. The applications a product is made of are parts in
[`28_MODULES/`](../28_MODULES/README.md). A document platform or a risk
register is an application, so the block for communications holds the
rendering, the store and the archive the platform sits on, not the platform;
the loader refuses a block that provides an application type, and says so.

**Not mandatory.** Nothing has to be built from blocks. They are a shortcut and
a shared vocabulary, not a gate.

**Not exhaustive.** A dozen blocks cover most of what turns up. When one is
missing, add it — the file is the interface.

## The shape

```yaml
- building_block_id: public-web-tier
  name: Public web tier
  category: Network
  description: >
    Everything between the internet and an application.
  provides:
    - component: cdn
    - component: waf
    - component: load-balancer
  relations:
    - from: cdn
      to: waf
    - from: waf
      to: load-balancer
  defaults:
    network_zone: Edge
```

`provides` names component types, never products. `relations` are between
components inside the block. `defaults` apply to everything the block creates,
and anything a component type already declares wins where they overlap — the
component knows more about itself than the block does.

Expanding a block needs one answer: what the thing being built is called.
Everything else is derived, which is the whole point.
