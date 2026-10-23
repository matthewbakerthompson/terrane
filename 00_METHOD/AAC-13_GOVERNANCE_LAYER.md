# AAC-13 — The governance layer

Controls and policies were out of scope here for a reason that is still true:
the governance register owns them, and a second copy would be a second place
for them to be wrong. The register does not hold the estate, so it cannot say
where a control is enforced. *Which system enforces this control* is a fact
about systems. *Which controls does this Restricted system record none of* is
a fact about both. Answering either needs the register and the estate in one
place.

So the register is imported, never authored, and the estate says where it is
enforced.

## What is held

Two entities, both canonical. `policies` and `controls` are named in
`architecture_method_metamodel.v2`, with the primary keys and field names the
field dictionary gives them, so they export into the same CSV layout as
everything else.

Four relations, also canonical:

| Relation | Reads as |
|---|---|
| `system_governed_by_control` | This system enforces this control |
| `data_governed_by_control` | This control is enforced on this data |
| `system_subject_to_policy` | This system is bound by this policy |
| `data_subject_to_policy` | This data is bound by this policy |

These rows are authored here — in `10_MODEL/relations/governance.yaml`, by
hand, by whoever knows — because they are facts about the estate rather than
about the register. The metamodel has semicolon-list columns for the same information
(`control_ids`, `governance_policy_ids`) and is explicit that they are
compatibility fields. The relation tables are the truth, and the export
writes them as such.

A control names the policy it gives effect to (`policy_id`). That is a
reference field rather than a relation because a control answers to one
policy; a control that answers to two is two controls sharing a name.

## The join that is derived

The business layer records which processes a control governs and which
capabilities each process supports. Neither processes nor steps are held here
— see [AAC-07](AAC-07_METAMODEL_CONTRACT.md) for why — so the importer does
the join on the way in and keeps only its result:

```
process_governed_by_control  ×  process_supports_capability
                       ↓
        capability_governed_by_control  (basis: Process)
```

Then it rolls up. A control governing a process under *Payment Posting*
governs something inside *Payments*, and a system that realizes the whole
domain should be asked about it. Every ancestor gets a row, marked
`basis: Descendant`, so the roll-up is never mistaken for something the
business said.

`capability_subject_to_policy` is derived the same way from the policies.

Both are extensions, both are written to
`10_MODEL/relations/governance_from_business_layer.yaml`, and neither should
be edited: the import overwrites them. If a pair is wrong, the process
mapping in the business repository is wrong, and that is where to fix it.

## Governed capabilities with no control recorded

The authored relations and the derived ones together support one check:

> The business says this capability is governed by this control. The estate
> says this system realizes the capability. The system records no control for
> it.

Either the system enforces the control and the model does not record it, or
the control is enforced somewhere this system is not. Neither case shows in
the register or the estate alone. **Coverage** lists the systems it applies to as *Systems realizing a governed
capability and recording none of its controls*. In the placeholder estate the
card servicing product is left in this state on purpose, so the report has a
row to show.

## What else the layer says

Four more gaps in **Coverage**, and the question each one raises:

| Gap | The question |
|---|---|
| Controls nothing in the estate enforces | Is this a mechanism or a document? |
| Restricted systems recording no control | Uncontrolled, or undocumented? |
| Personal data subject to no policy | Which policy governs this data? |
| Policies with no control under them | Is this meant to be enforced, or is it a statement of intent? |

And one warning in `terrane validate`: `governance.no_control`, for a live system
handling Restricted data with no control recorded. It fires only when the
model holds a register at all, so a model without one does not get it on
every system.

The count of that warning over quarters measures governance coverage. Like
the other counts in [AAC-05](AAC-05_CHANGE_FLOW.md), it belongs on a dashboard
as a number, not as a list.

## The views

| View | Kind | What it answers |
|---|---|---|
| `control-coverage` | report | Every control, and what enforces it: systems, data, and the capabilities it governs through the business layer |
| `policy-landscape` | report | Every policy, the controls that give effect to it, and what it binds |
| `system-governance` | diagram, takes a system | One system and everything that obliges it, including the controls reached through the capabilities it realizes |

The first two are reports for the usual reason: they answer a question with a
set. The third draws one system and what obliges it, and a control that
appears on it through a capability and not through the system is the gap
**Coverage** lists, drawn. It is rendered once for every live,
high-criticality system handling Restricted data.

## Impact through controls and policies

A control is enforced by what it governs, so it sits downstream of the system
the way a capability does: retire the system and the control has lost an
enforcement point. A policy runs the other way — the subject is obliged by it,
so when the policy changes the subject has work to do. And a control gives
effect to a policy, so it changes when the policy does.

```bash
cd 50_ENGINE && python -m terrane impact CTL-PCI-EVIDENCE
```

lists what the control depends on for its enforcement — the systems, the
data, the capabilities, the policy — and

```bash
cd 50_ENGINE && python -m terrane impact SYS-DISPUTES-SAAS --only controls
```

lists the controls that lose something if the disputes platform goes.

## Two things this is not

**It is not a control assessment.** Nothing here says whether a control is
effective, tested, or passing. The field dictionary has a fact table for that
(`facts.control_assessments`) and it belongs in the governance tooling, not in
an architecture model. What this holds is where the control is enforced, which
is one input an assessment needs.

**It is not authored here.** Every control and policy in the model came
through `import_business_layer.py`. Add one in the business repository and
re-run the import. The only thing to write here is the enforcement point.

## Placeholder content

Every control, policy and enforcement row in the shipped model is a placeholder.
The register was drafted for a workshop and is marked `Proposed` throughout;
the enforcement rows were written to exercise the mechanism and to leave two
deliberate gaps for the coverage report to find. None of it describes a real
organization's controls, and none of it should be quoted as one.
