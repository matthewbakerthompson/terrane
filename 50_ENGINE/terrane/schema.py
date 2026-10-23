"""Entity and relation definitions, aligned to architecture_method_metamodel.v2.

Field names come from the method's canonical metamodel so that the
model in this repository can be exported straight into the CSV/Collibra path
without a translation layer. Anything this repository adds on top is marked
`extension=True` and is listed in `00_METHOD/AAC-07_METAMODEL_CONTRACT.md`.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence


class Field(NamedTuple):
    name: str
    required: bool = False
    enum: Optional[Sequence[str]] = None
    ref: Optional[str] = None  # entity type this field points at
    extension: bool = False


class EntityType(NamedTuple):
    name: str  # plural table name, matching the metamodel
    pk: str
    folder: str
    label: str  # singular, for CLI and messages
    fields: Sequence[Field]
    extension: bool = False


class RelationType(NamedTuple):
    name: str
    left: str  # entity type name
    right: str
    left_column: str
    right_column: str
    qualifier: Optional[str] = None  # third PK column, e.g. `operation`
    extension: bool = False


#: `Proposed` is an extension, and a distinction the business layer relies on:
#: proposed is drafted and not agreed, planned is agreed and not built. A
#: capability map that cannot say which is which is a wish list.
STATUS = ("Proposed", "Planned", "Active", "Deprecated", "Retired")
CRITICALITY = ("High", "Medium", "Low")
DOMAINS = ("Business", "Application", "Data", "Technology", "Governance")
LAYERS = ("Business", "Application", "Data", "Technology")
ABSTRACTION = ("Contextual", "Conceptual", "Logical", "Physical")
CLASSIFICATION = ("Public", "Internal", "Confidential", "Restricted")
ENVIRONMENT = ("Production", "UAT", "Test", "Dev")
HOSTING = ("On-prem", "Azure", "AWS", "GCP", "External", "SaaS")
TIER = ("Tier 1", "Tier 2", "Tier 3")
OPERATION = ("Read", "Write", "ReadWrite")
#: What a governance board said about a change request. The field dictionary
#: names these three and no fourth for "not yet": an undecided request is one
#: whose `status` has not reached a decision, and leaving this empty is how it
#: says so. A "Pending" value here would be a second place to record the same
#: thing, and the two would disagree.
GOVERNANCE_DECISIONS = ("Approved", "Rejected", "Deferred")
#: How an integration behaves, which decides which end depends on which. A
#: caller depends on what it calls; a consumer depends on what feeds it. Left
#: to be inferred from protocol this is a guess, so it is modeled.
INTEGRATION_STYLES = ("Request-response", "Event", "Batch")
#: Who is outside the estate looking in. Kept coarse on purpose: a context
#: diagram with twenty actor types is not a context diagram.
#:
#: The concept is standard and the vocabulary is not. An entity for what sits
#: outside the boundary appears in UML use case diagrams (where the word comes
#: from), in ArchiMate as Business Actor with Business Role beside it, in
#: TOGAF's content metamodel, and in C4 as the Person on a system context
#: diagram. This list is a synthesis of those rather than a quotation of any
#: one of them, and the canonical metamodel this repository consumes has no
#: equivalent entity at all -- which is why a context diagram could not be
#: drawn from it before.
ACTOR_KINDS = ("Person", "Role", "Organization", "External system", "Regulator", "Device")

#: Placement vocabulary. Deliberately provider-neutral at the top level so a
#: multi-cloud estate does not need two sets of views.
CLOUD_PROVIDERS = ("AWS", "Azure", "GCP", "On-prem", "SaaS")
#: Network zones follow the tiering every landing zone ends up with, whatever
#: it calls them: internet-facing, application, data, and shared services.
NETWORK_ZONES = ("Edge", "Public", "Private-App", "Private-Data", "Shared-Services", "On-prem")
RESILIENCE = ("Multi-region", "Multi-AZ", "Single-AZ", "Single-node")

#: Where a capability sits in the map. Deliberately not `abstraction_level`,
#: which is the TOGAF one and already means something else here: a capability
#: map is conceptual at every level of itself.
CAPABILITY_LEVELS = ("L0", "L1", "L2", "L3")
#: Banding taken verbatim from the business architecture repository, whose own
#: method document is explicit that it is "a communication device ... it
#: carries no structural meaning in the metamodel beyond ordering". It is a
#: practitioner convention rather than a standard: TOGAF, BIZBOK and BIAN do
#: not define it, and the nearest formal antecedent is Porter's two-way split
#: of primary and support activities. Treat it as a way to lay out an
#: executive view, not as a fact about a capability.
CAPABILITY_TIERS = ("Direct", "Core", "Enable")
#: Also from the business repository, and also a judgment rather than a
#: measurement: every value in this model is a straw man drafted for a
#: workshop, not something assessed.
STRATEGIC_IMPORTANCE = ("Differentiating", "Essential", "Advantage", "Parity", "Commodity")
#: A value stream either delivers the value or governs how it is delivered.
VALUE_STREAM_TYPES = ("Core", "Management", "Supporting")

#: What kind of thing a framework is, because they are not interchangeable:
#: a standard can be certified against, a method tells you how to work, a
#: reference model gives you a shape, and a body of knowledge gives you a
#: vocabulary and an argument.
FRAMEWORK_TYPES = (
    "Standard", "Reference model", "Practice framework", "Governance framework",
    "Body of knowledge", "Method", "Regulation",
)
#: How firmly a domain answers to a framework. `Governed by` is a fact about
#: the organization; `Aligned to` is a choice; `Informed by` is a borrowing.
FRAMEWORK_ALIGNMENT = ("Governed by", "Aligned to", "Informed by")

#: What a control does about the risk it exists for. The preventive / detective
#: split is the one every control framework shares; corrective is the third
#: bucket most registers add for the controls that only act after the fact.
CONTROL_TYPES = ("Preventive", "Detective", "Corrective")
#: How often a control runs. `Per event` is the one worth having: most
#: controls a system enforces fire on a transaction, not on a calendar.
CONTROL_FREQUENCIES = (
    "Continuous", "Per event", "Daily", "Weekly", "Monthly", "Quarterly", "Annually",
)

_COMMON = (
    Field("name", required=True),
    Field("description"),
    Field("status", required=True, enum=STATUS),
    Field("togaf_layer", enum=LAYERS),
    Field("architecture_domain", enum=DOMAINS),
    Field("abstraction_level", enum=ABSTRACTION),
    Field("last_reviewed"),
    # Extensions used by the view engine and the CMDB reconciliation.
    Field("company_domain", extension=True),
    Field("company_subdomain", extension=True),
    Field("tags", extension=True),
    Field("archetype", extension=True),
    Field("archetype_instance", extension=True),
    # Which part of the shape produced it, from `28_MODULES/`. Set by
    # expansion, so a diagram can say "this came with the return feed".
    Field("module", extension=True),
    # Where the record came from, when it was not authored here. Once in the
    # common set: declared again on systems, data assets and processes, it was
    # a second `source` column in every export and a duplicate key in every
    # record the importer wrote.
    Field("source", extension=True),
)

ENTITY_TYPES: Dict[str, EntityType] = {}


def _register(entity: EntityType) -> None:
    names = [f.name for f in entity.fields]
    twice = sorted({name for name in names if names.count(name) > 1})
    if twice:
        # A field declared twice is a column written twice in every export
        # and a key written twice in every record the importer makes.
        raise ValueError("%s declares %s twice" % (entity.name, ", ".join(twice)))
    ENTITY_TYPES[entity.name] = entity


_register(
    EntityType(
        name="systems",
        pk="system_id",
        folder="systems",
        label="system",
        fields=_COMMON
        + (
            Field("owner_org_id", required=True, ref="org_units"),
            Field("criticality", required=True, enum=CRITICALITY),
            Field("service_tier", enum=TIER),
            Field("hosting", enum=HOSTING),
            Field("environment", enum=ENVIRONMENT),
            Field("provider"),
            Field("system_category"),
            Field("data_classification_supported", enum=CLASSIFICATION),
            Field("platform_service_dependencies"),
            Field("governance_policy_ids"),
            Field("control_ids"),
            # What kind of thing this is, from `25_COMPONENTS/`. Optional:
            # something with no type still draws, it just gets no shape, no
            # category and no defaults.
            Field("component_type", extension=True),
            Field("product", extension=True),
            Field("cmdb_ci_sys_id", extension=True),
            Field("cmdb_ci_class", extension=True),
            # Placement. Where a thing actually runs, as opposed to what it is
            # for. An application landscape that cannot answer "which account,
            # which region, which subnet tier" is not much use to the people who
            # have to operate or secure it.
            Field("cloud_provider", enum=CLOUD_PROVIDERS, extension=True),
            Field("cloud_account", extension=True),
            Field("region", extension=True),
            Field("network_zone", enum=NETWORK_ZONES, extension=True),
            Field("availability_zone", extension=True),
            Field("deployment_unit", extension=True),
            Field("resilience", enum=RESILIENCE, extension=True),
        ),
    )
)

_register(
    EntityType(
        name="interfaces",
        pk="interface_id",
        folder="interfaces",
        label="interface",
        fields=_COMMON
        + (
            Field("source_system_id", required=True, ref="systems"),
            Field("target_system_id", required=True, ref="systems"),
            Field("owner_org_id", ref="org_units"),
            Field("protocol"),
            Field("direction"),
            Field("frequency"),
            Field("integration_style", enum=INTEGRATION_STYLES, extension=True),
            Field("auth_method"),
            Field("data_classification", enum=CLASSIFICATION),
            # The patterns this interface applies, from `27_PATTERNS/`. Three
            # of the method's reference patterns are about how two systems
            # talk, so "did this integration use the approved pattern" is
            # asked of the interface, not of a product that may own neither
            # end of it.
            Field("patterns", extension=True),
            # The interface one end offers that this connection goes
            # through: the API it calls, the topic it reads. Both ends are
            # still written, because the canonical metamodel joins two
            # systems and every reader of a connection asks for both; the
            # offered interface's own system has to be one of them.
            Field("offered_interface_id", ref="offered_interfaces", extension=True),
        ),
    )
)

#: What a system offers for others to connect to: an API, a topic, a file
#: drop. An extension. The canonical `interfaces` are connections between two
#: systems, closer to ArchiMate's flow than to its application interface, so a
#: service with forty consumers had forty records and nothing the forty were
#: connections to; the six products' APIs were systems of their own, named for
#: the door rather than for the service behind it. In ArchiMate and in TOGAF's
#: content metamodel what is deployed is the component, and the interface is
#: its point of access, composed in it. The fields are the ones a connection
#: carries, said once for every connection through it.
_register(
    EntityType(
        name="offered_interfaces",
        pk="offered_interface_id",
        folder="offered_interfaces",
        label="offered interface",
        extension=True,
        fields=_COMMON
        + (
            # The system that offers it, the way a stage names its stream.
            Field("system_id", required=True, ref="systems"),
            Field("owner_org_id", ref="org_units"),
            Field("protocol"),
            Field("integration_style", enum=INTEGRATION_STYLES),
            Field("auth_method"),
            Field("data_classification", enum=CLASSIFICATION),
            Field("frequency"),
            # Where its contract is written down: an OpenAPI or AsyncAPI
            # file, a schema registry subject, a URL.
            Field("specification"),
            Field("patterns"),
        ),
    )
)

_register(
    EntityType(
        name="data_assets",
        pk="data_asset_id",
        folder="data_assets",
        label="data asset",
        fields=_COMMON
        + (
            Field("data_owner_org_id", ref="org_units"),
            Field("data_steward_org_id", ref="org_units"),
            Field("source_of_truth", ref="systems"),
            Field("classification", enum=CLASSIFICATION),
            Field("risk_level", enum=CRITICALITY),
            Field("pii_flag", enum=("Yes", "No")),
            Field("pii_types"),
            Field("table_name"),
            Field("schema"),
            Field("lineage_reference"),
            Field("quality_rules"),
            Field("governance_policy_ids"),
            Field("control_ids"),
        ),
    )
)

_register(
    EntityType(
        name="tech_services",
        pk="tech_service_id",
        folder="tech_services",
        label="technology service",
        fields=_COMMON
        + (
            Field("owner_org_id", ref="org_units"),
            Field("provider"),
            Field("service_category"),
            Field("service_name"),
            # From `25_COMPONENTS/`: what kind of service this is, and what a
            # given provider calls it. The block says "a load balancer"; the
            # product is that block's answer for one cloud.
            Field("component_type", extension=True),
            # The further kinds a landing-zone service answers for. Key Vault
            # is the secrets manager and the key management on Azure, and
            # `component_type` is one value: the kind it is drawn as. This is
            # the second, and only the landing zone reads it.
            Field("answers_for", extension=True),
            Field("product", extension=True),
            Field("cloud_provider", enum=CLOUD_PROVIDERS, extension=True),
            Field("cloud_account", extension=True),
            Field("region", extension=True),
            Field("network_zone", enum=NETWORK_ZONES, extension=True),
            Field("availability_zone", extension=True),
            Field("cidr", extension=True),
        ),
    )
)

_register(
    EntityType(
        name="capabilities",
        pk="capability_id",
        folder="capabilities",
        label="capability",
        fields=_COMMON
        + (
            Field("owner_org_id", ref="org_units"),
            Field("maturity_level"),
            # A capability map is a tree. Without the parent it is a list, and
            # a list of two hundred capabilities is not a map of anything.
            Field("parent_capability_id", ref="capabilities", extension=True),
            Field("capability_level", enum=CAPABILITY_LEVELS, extension=True),
            Field("capability_tier", enum=CAPABILITY_TIERS, extension=True),
            Field("strategic_importance", enum=STRATEGIC_IMPORTANCE, extension=True),
        ),
    )
)

_register(
    EntityType(
        name="frameworks",
        pk="framework_id",
        folder="frameworks",
        label="framework",
        fields=_COMMON
        + (
            Field("publisher"),
            Field("framework_type", enum=FRAMEWORK_TYPES),
            # What the framework is actually for. Without it, a mapping claims
            # coverage the framework does not give.
            Field("scope"),
            Field("version"),
            Field("url"),
        ),
        extension=True,
    )
)

_register(
    EntityType(
        name="value_streams",
        pk="value_stream_id",
        folder="value_streams",
        label="value stream",
        fields=_COMMON
        + (
            Field("value_stream_type", enum=VALUE_STREAM_TYPES),
            Field("stakeholders"),
            # The sentence the whole stream is judged against. A value stream
            # without one is a process model with ambition.
            Field("value_proposition"),
            Field("owner_org_id", ref="org_units"),
        ),
        # Canonical: the metamodel names this entity and its key. The fields
        # beyond the common set are additions.
    )
)

_register(
    EntityType(
        name="value_stream_stages",
        pk="stage_id",
        folder="value_stream_stages",
        label="value stream stage",
        fields=_COMMON
        + (
            Field("value_stream_id", required=True, ref="value_streams"),
            Field("stage_order"),
            # What has to be true to leave the stage. Stages without one get
            # named after departments rather than after progress.
            Field("exit_criterion"),
            Field("owner_org_id", ref="org_units"),
        ),
        extension=True,
    )
)

_register(
    EntityType(
        name="org_units",
        pk="org_unit_id",
        folder="org_units",
        label="org unit",
        fields=_COMMON
        + (
            Field("dama_role"),
            Field("parent_org_unit_id", ref="org_units", extension=True),
        ),
    )
)

#: Policies and controls are canonical: the metamodel names both, and the four
#: relation tables that join them to systems and data assets. They were out of
#: scope here on the grounds that the governance register owns them. It still
#: does -- both are imported from the business layer, never authored here --
#: but without them the estate could not answer the question an audit
#: actually asks: which system enforces this control, and which controls does
#: this Restricted system record none of.
_register(
    EntityType(
        name="policies",
        pk="policy_id",
        folder="policies",
        label="policy",
        fields=_COMMON
        + (
            Field("purpose"),
            Field("regulatory_framework"),
            Field("owner_org_id", ref="org_units"),
            Field("effective_date"),
            # Where the policy is registered outside the model, so the audit
            # trail leads somewhere. Carried from the business layer.
            Field("external_ref", extension=True),
        ),
    )
)

_register(
    EntityType(
        name="controls",
        pk="control_id",
        folder="controls",
        label="control",
        fields=_COMMON
        + (
            Field("control_type", enum=CONTROL_TYPES),
            Field("frequency", enum=CONTROL_FREQUENCIES),
            Field("regulatory_framework"),
            Field("owner_org_id", ref="org_units"),
            Field("maturity_rating"),
            # Which policy the control gives effect to. A reference field
            # rather than a relation because a control answers to one policy;
            # a control that answers to two is two controls sharing a name.
            Field("policy_id", ref="policies", extension=True),
            Field("external_ref", extension=True),
            # The Cyber Risk Institute profile reference, where the control
            # maps to one. The business layer records it, so it is kept.
            Field("cri_ref", extension=True),
        ),
    )
)

#: Actors are an extension. The canonical metamodel has no entity for the people
#: and organizations outside the estate that use it, and without them a system
#: context diagram -- the most basic architecture diagram there is -- cannot be
#: drawn at all.
_register(
    EntityType(
        name="actors",
        pk="actor_id",
        folder="actors",
        label="actor",
        extension=True,
        fields=_COMMON
        + (
            Field("actor_kind", enum=ACTOR_KINDS),
            Field("internal", enum=("Yes", "No")),
            Field("owner_org_id", ref="org_units"),
            Field("volume"),
        ),
    )
)

#: Flows are an extension. The canonical metamodel models processes and steps
#: for business architecture; this is the thin version needed to draw a
#: transaction through the estate, which is a technology question and a
#: different granularity from a process model.
_register(
    EntityType(
        name="flows",
        pk="flow_id",
        folder="flows",
        label="flow",
        extension=True,
        fields=_COMMON
        + (
            Field("owner_org_id", ref="org_units"),
            Field("trigger"),
            Field("criticality", enum=CRITICALITY),
            Field("target_latency"),
        ),
    )
)

# Processes are canonical in the metamodel and authored in the business
# architecture repository, where the steps, the flows and the BPMN live. What
# arrives here is the process itself and what it touches: the capabilities it
# supports, the systems and data it uses, the controls and policies on it.
# That is enough to draw a system's reach across the organization, and it is
# the join that turns a capability map into a realization map.
_register(
    EntityType(
        name="processes",
        pk="process_id",
        folder="processes",
        label="process",
        extension=True,
        fields=_COMMON
        + (
            Field("value_stream_id", ref="value_streams"),
            Field("owner_org_id", ref="org_units"),
            Field("business_unit"),
            Field("criticality", enum=CRITICALITY),
            Field("risk_level"),
            Field("process_level"),
            Field("trigger"),
            Field("frequency"),
            Field("rto_hours"),
            Field("rpo_hours"),
            Field("data_classification", enum=CLASSIFICATION),
            Field("pii_flag"),
        ),
    )
)

# Products are an extension. The canonical metamodel has no entity that groups
# systems under a business offering, and that grouping is exactly what makes a
# new product a small edit rather than a new diagram.
_register(
    EntityType(
        name="products",
        pk="product_id",
        folder="products",
        label="product",
        extension=True,
        fields=_COMMON
        + (
            Field("owner_org_id", required=True, ref="org_units"),
            Field("criticality", enum=CRITICALITY),
            Field("product_category"),
            Field("launch_date"),
            # The patterns this product applies, from `27_PATTERNS/`. Set by
            # the archetype that built it and added to by the instance. The
            # rendered catalog reads adoption off this field, which is what
            # makes "did this design use the approved pattern" a query.
            Field("patterns", extension=True),
            # The kind of thing this product is, from `29_TYPES/`. What the
            # Assemble panel asks first, and what `terrane validate` holds the
            # product's parts to.
            Field("build_type", extension=True),
        ),
    )
)

# The change-management entities, all three canonical. The model could already
# say what is planned -- `status` carries that on every entity -- but not when
# it lands, in what order, under whose initiative, or on whose decision.
# Nothing in the estate held a date until these arrived.
#
# The canonical metamodel names the entity and its key and leaves the field
# list to the field dictionary, as it does for `value_streams`. The fields
# below are the dictionary's, including the two `affected_*_ids` semicolon
# lists. Those are declared so a canonical import is not answered with a page
# of `field.unknown`, and are read by nothing: the relation tables are the
# truth, the same way they are for `control_ids` on a system.
_register(
    EntityType(
        name="roadmaps",
        pk="roadmap_id",
        folder="roadmaps",
        label="roadmap",
        fields=_COMMON
        + (
            # Required, because a roadmap nobody owns is a wish list, which is
            # the thing modeling roadmaps at all is meant to prevent.
            Field("owner_org_id", required=True, ref="org_units"),
            # Quarters, not dates: YYYY-Qn, as the field dictionary says. A
            # roadmap that names the day something lands is claiming more than
            # anyone knows in the quarter it is written.
            Field("start_date"),
            Field("end_date"),
            Field("time_horizon_years"),
            Field("governance_board"),
            Field("principle_ids"),
            Field("notes"),
        ),
    )
)

_register(
    EntityType(
        name="work_packages",
        pk="work_package_id",
        folder="work_packages",
        label="work package",
        fields=_COMMON
        + (
            Field("owner_org_id", required=True, ref="org_units"),
            # A canonical foreign key, so a roadmap's contents need no relation
            # table: a work package belongs to one roadmap, and a view follows
            # the field with `via: roadmap_id` like any other reference.
            Field("roadmap_id", ref="roadmaps"),
            # Which decision let the work start. An extension, the same shape
            # and for the same reason as `policy_id` on a control: a work
            # package proceeds on one authorization, and work proceeding on
            # two decisions is two work packages that were funded together.
            # Without it, a change request would have to repeat the system
            # list its own work package already carries.
            Field("change_request_id", ref="architecture_change_requests", extension=True),
            Field("start_date"),
            Field("end_date"),
            Field("budget_usd"),
            Field("risk_level"),
            Field("affected_system_ids"),
            Field("affected_process_ids"),
            Field("principle_ids"),
            Field("notes"),
        ),
    )
)

_register(
    EntityType(
        name="architecture_change_requests",
        pk="change_request_id",
        folder="architecture_change_requests",
        label="change request",
        fields=_COMMON
        + (
            Field("requestor_org_id", ref="org_units"),
            Field("approver_org_id", ref="org_units"),
            Field("request_date"),
            Field("decision_date"),
            # Empty until the board has decided. `status` says where the
            # request has got to; this says what was decided. Keeping them
            # apart is what stops an undecided request reading as a rejected
            # one on a report that only shows one of the two.
            Field("governance_decision", enum=GOVERNANCE_DECISIONS),
            Field("decision_rationale"),
            Field("impact_assessment"),
            Field("principle_alignment"),
            Field("affected_system_ids"),
            Field("affected_process_ids"),
            Field("notes"),
        ),
    )
)


RELATION_TYPES: Dict[str, RelationType] = {}


def _register_relation(relation: RelationType) -> None:
    RELATION_TYPES[relation.name] = relation


for _rel in (
    RelationType(
        "system_uses_tech_service", "systems", "tech_services", "system_id", "tech_service_id"
    ),
    RelationType(
        "interface_transports_data_asset",
        "interfaces",
        "data_assets",
        "interface_id",
        "data_asset_id",
    ),
    # Governance, canonical. The metamodel names all four, and together they
    # are the join an audit walks: from a regulation to a policy, to a
    # control, to the system or the data the control is enforced on.
    RelationType(
        "system_governed_by_control", "systems", "controls", "system_id", "control_id"
    ),
    RelationType(
        "system_subject_to_policy", "systems", "policies", "system_id", "policy_id"
    ),
    RelationType(
        "data_governed_by_control", "data_assets", "controls", "data_asset_id", "control_id"
    ),
    RelationType(
        "data_subject_to_policy", "data_assets", "policies", "data_asset_id", "policy_id"
    ),
    # Derived, never authored. The business layer records which processes a
    # control governs and which capabilities each process supports; joining
    # the two on the way in says which capabilities a control governs. The
    # `basis` qualifier keeps the inference honest: `Process` means a process
    # under this capability is governed by the control, `Descendant` means a
    # capability below this one is. That join is what lets the estate notice
    # a system realizing a governed capability while recording none of its
    # controls, which is the most useful thing a governance layer can say.
    # What a process touches, as the business layer records it. Every row
    # here is imported; the estate never authors a process.
    RelationType("process_supports_capability", "processes", "capabilities",
                 "process_id", "capability_id", extension=True),
    RelationType("process_uses_system", "processes", "systems",
                 "process_id", "system_id", qualifier="role", extension=True),
    RelationType("process_uses_data_asset", "processes", "data_assets",
                 "process_id", "data_asset_id", qualifier="access", extension=True),
    RelationType("process_governed_by_control", "processes", "controls",
                 "process_id", "control_id", extension=True),
    RelationType("process_subject_to_policy", "processes", "policies",
                 "process_id", "policy_id", extension=True),
    # Where in a framework a capability is placed, as a path in the
    # framework's own terms: "Sales and Service > Sales > Customer Offer" in
    # BIAN, "Service management > Incident Management" in ITIL. The other
    # framework link, below, says how firmly a domain follows a framework;
    # this one says where each capability sits in it, and a framework's
    # landscape is drawn from these paths.
    RelationType("capability_references_framework", "capabilities", "frameworks",
                 "capability_id", "framework_id", qualifier="ref", extension=True),
    RelationType(
        "capability_governed_by_control",
        "capabilities",
        "controls",
        "capability_id",
        "control_id",
        qualifier="basis",
        extension=True,
    ),
    RelationType(
        "capability_subject_to_policy",
        "capabilities",
        "policies",
        "capability_id",
        "policy_id",
        qualifier="basis",
        extension=True,
    ),
    # Extensions. The canonical metamodel routes system-to-capability and
    # system-to-data linkage through processes and steps, which is correct for
    # process modeling but leaves an application landscape unable to answer
    # "what capability does this system realize" without a join through work
    # this repository does not hold.
    RelationType(
        "system_realizes_capability",
        "systems",
        "capabilities",
        "system_id",
        "capability_id",
        extension=True,
    ),
    # Which body of practice a capability answers to. A qualifier rather than
    # a field because a domain answers to more than one, and how firmly it does
    # so is the part worth recording: PCI DSS governs payments whether anybody
    # likes it or not, while BIZBOK merely informs how the map was built.
    RelationType(
        "capability_aligns_to_framework",
        "capabilities",
        "frameworks",
        "capability_id",
        "framework_id",
        qualifier="alignment",
        extension=True,
    ),
    # What a stage of a value stream needs in order to happen. This is the
    # join that lets "which systems are on the critical path of originations"
    # be answered without anybody drawing it by hand.
    RelationType(
        "stage_crosses_capability",
        "value_stream_stages",
        "capabilities",
        "stage_id",
        "capability_id",
        extension=True,
    ),
    RelationType(
        "system_reads_writes",
        "systems",
        "data_assets",
        "system_id",
        "data_asset_id",
        qualifier="operation",
        extension=True,
    ),
    RelationType(
        "product_includes_system",
        "products",
        "systems",
        "product_id",
        "system_id",
        extension=True,
    ),
    RelationType(
        "actor_uses_system",
        "actors",
        "systems",
        "actor_id",
        "system_id",
        qualifier="interaction",
        extension=True,
    ),
    # A step is an interface traversal, not a system visit. Naming the
    # interface makes an unmodeled hop impossible to express, which keeps the
    # sequence diagram honest by construction.
    RelationType(
        "flow_step",
        "flows",
        "interfaces",
        "flow_id",
        "interface_id",
        qualifier="sequence",
        extension=True,
    ),
    RelationType(
        "tech_service_connects_to",
        "tech_services",
        "tech_services",
        "from_tech_service_id",
        "to_tech_service_id",
        qualifier="connection",
        extension=True,
    ),
    RelationType(
        "product_realizes_capability",
        "products",
        "capabilities",
        "product_id",
        "capability_id",
        extension=True,
    ),
    # What a work package touches and what a change request is about. The
    # canonical metamodel carries both as semicolon lists on the record --
    # `affected_system_ids` -- and a list in a cell cannot be joined, filtered
    # or drawn. Same decision as `control_ids`: accept the column, model the
    # truth as rows. The qualifier says what the work does to the system,
    # because "builds it" and "changes it in place" are different risks and a
    # target-state diagram that cannot tell them apart is decoration.
    RelationType(
        "work_package_affects_system",
        "work_packages",
        "systems",
        "work_package_id",
        "system_id",
        qualifier="effect",
        extension=True,
    ),
    RelationType(
        "change_request_affects_system",
        "architecture_change_requests",
        "systems",
        "change_request_id",
        "system_id",
        extension=True,
    ),
):
    _register_relation(_rel)


#: Fields carried on interfaces under the v1 field dictionary, which uses
#: `from_system`/`to_system` where v2 canonical uses `source_system_id`/
#: `target_system_id`. v2 wins; these are accepted on load and normalized.
FIELD_ALIASES: Dict[str, Dict[str, str]] = {
    "interfaces": {
        "from_system": "source_system_id",
        "to_system": "target_system_id",
    }
}


def entity_type_for_folder(folder: str) -> Optional[EntityType]:
    for entity in ENTITY_TYPES.values():
        if entity.folder == folder:
            return entity
    return None


def required_fields(entity_type: EntityType) -> List[str]:
    return [f.name for f in entity_type.fields if f.required]


def field_map(entity_type: EntityType) -> Dict[str, Field]:
    return {f.name: f for f in entity_type.fields}
