# Patterns

A building block plus the decision.

`26_BLOCKS/` says what arrives together: a CDN, a WAF and a load balancer make
a public web tier. It does not say when to use one, what it costs, or when
reaching for it is the wrong call. That paragraph is the valuable part, and
it is what an architecture review board actually governs. A pattern is where
it lives.

## Why this is a separate thing

A block is a fact about composition. A pattern is a judgment about fit, and
judgments have a lifecycle that facts do not: a pattern is a candidate, then
approved, then deprecated in favor of another one. Mixing the two would mean
either deprecating a block that is still perfectly good composition, or
carrying a decision on a thing that has no owner to make it.

Keeping them apart is also what makes "did this design use the approved
pattern" a query rather than a memory test. A product names the patterns it
applies; the register says which are approved; the difference is the review.

## The shape

```yaml
- pattern_id: private-egress-to-saas
  name: Private egress to a bought service
  status: Approved            # Candidate, Approved, Deprecated, Retired
  category: Integration
  blocks: [private-egress-to-saas]
  intent: >
    What it is for, in one paragraph.
  consequences: >
    What it costs. Every pattern costs something, and a pattern description
    that does not say what is a sales pitch.
  when_not_to_use: >
    The cases it is wrong for. This is the paragraph a review board reads
    first.
  method_ref: PAT-011         # the method's reference pattern this implements
```

`blocks` names building blocks, which must exist.

Who owns the pattern, the decision that approved it and which controls it is
designed to meet are not on it. Those are one organization's, and the estate
says them in its `10_MODEL/model.yaml`:

```yaml
patterns:
  private-egress-to-saas:
    owner_org_id: ORG-VENDORMGMT
    decision_ref: ADR-0007      # where the decision was recorded
    satisfies: [CTL-TPRM-DD, CTL-SANCTIONS]   # controls in the register it is designed to meet
```

`satisfies` is what ties the library to the governance layer: a design that
applies the pattern has an argument for the control, and a control nothing
satisfies is worth a question. The patterns here used to carry all three, in
the card issuer's terms, and the health system in `90_EXAMPLE/thurman-health`
heard fifty-one warnings about an owner and a register it never had. A
pattern in an organization's own library may still carry them, since that
library is the organization's; what `model.yaml` says wins.

`intent`, `consequences` and `when_not_to_use` are all required. A pattern
with no stated cost or no stated exclusion is not a pattern, it is a
preference.

`method_ref` names the method's reference pattern that this one
implements. The method's pattern says what a well-governed integration of
this kind must capture and which enterprise standards it satisfies; the
pattern here says which blocks the house builds it from, what it costs and
when not to. Two patterns here can implement one of the method's, and a
pattern here can implement none: the house decision to deprecate shared
databases has no reference pattern because nothing recommends it.

## What a pattern is not

**Not a block.** A block can be used without any pattern at all. Nothing
here is a gate.

**Not a vendor's reference architecture.** Like blocks, no pattern names a
provider. The same pattern resolves to different products on different
clouds, and that is the point.

**Not exhaustive.** A dozen cover most of what a review board sees. Add one
when a decision gets made for the third time; the file is the interface.

## How a product applies one

A product carries `patterns`, a list of pattern ids. An archetype declares the
patterns its shape applies and every instance inherits them; an instance can
add its own. `terrane validate` refuses a pattern id that is not in the library,
and the rendered catalog under `70_ARTIFACTS/library/` lists which products
apply each pattern, which is the adoption report, generated rather than
surveyed.

## How an interface applies one

An interface carries `patterns` too. Three of the method's reference patterns
are about how two systems talk -- an API contract, a stream, a scheduled
file -- and the question "did this integration use the approved pattern" has
an answer per connection, not per product: the product that owns one end
rarely owns the other. The same two gates apply, and the catalog lists the
interfaces on each pattern under the products.
