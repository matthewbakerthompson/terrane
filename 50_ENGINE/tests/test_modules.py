"""Tests for modules: the parts a shape is composed from.

The claim is that a new vendor's diagram is chosen, not drawn: a shape names
the parts, a product keeps the ones it needs, and each part brings its own
systems, interfaces, data, relations, controls and patterns. What is checked
here is the composition: `without` drops a part and everything that pointed at
it, a part cannot be dropped when another kept part needs it, a part the shape
marks as always present cannot be dropped at all, the instance can re-bind a
part's parameters, and the governance shorthands on a template produce the
enforcement rows the register expects.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import blocks, importer, model as model_module, validate  # noqa: E402
from terrane.archetype import (  # noqa: E402
    ArchetypeError,
    effective_bind,
    expand,
    landing_providers,
    landing_zone_gaps,
    landing_zone_index,
    load_archetypes,
    parse_archetype,
    resolve_kind,
)
from terrane.loader import load_folder, read_data_file  # noqa: E402
from terrane.answers import estate_answers  # noqa: E402
from terrane.modules import (  # noqa: E402
    ModuleError,
    _check_kits,
    load_modules,
    parse_module,
    provided_count,
    undeclared_tokens,
    uses_of,
)
from terrane.query import load_views  # noqa: E402
from terrane.adoption import candidates, drifts, part_categories  # noqa: E402
from terrane.render_library import (  # noqa: E402
    render_adoption,
    render_landing_zones,
    render_modules,
    render_shapes,
)
from terrane.schema import ENTITY_TYPES  # noqa: E402

from _fixture import (  # noqa: E402
    EXAMPLE_CSV, REPO, Sandbox, seeded_model, seeded_root, setup_shared, teardown_shared,
)


def setUpModule() -> None:
    setup_shared()


def tearDownModule() -> None:
    teardown_shared()


def _library():
    components = blocks.load_components(REPO)
    landing = landing_zone_index(
        record for _path, record in load_folder(REPO / "10_MODEL" / "tech_services")
        if isinstance(record, dict)
    )
    # And what the estate answers, as the loader passes it: the parts ask the
    # estate who owns the egress and where the audit trail goes.
    answers = estate_answers(read_data_file(REPO / "10_MODEL" / "model.yaml"))
    return components, blocks.load_blocks(REPO, components), load_modules(REPO), landing, answers


SHAPE = {
    "archetype_id": "probe-saas",
    "applies_to": "products",
    "provider": "AWS",
    # The landing zone by kind. The parts name what they need; this says
    # which service is that kind here.
    "bind": {
        "container-platform": "TS-AWS-EKS",
        "api-gateway": "TS-AWS-APIGW",
        "secrets-manager": "TS-AWS-SECRETS",
        "private-egress": "TS-AWS-PRIVATELINK",
        "transit-gateway": "TS-AWS-TGW",
        "observability": "TS-AWS-CLOUDWATCH",
    },
    "parameters": [
        {"name": "slug", "required": True},
        {"name": "product_name", "default": "Probe"},
        {"name": "owner_org", "default": "ORG-TECH"},
        {"name": "domain", "default": "Probing"},
        {"name": "classification", "default": "Restricted"},
        {"name": "vendor", "required": True},
        {"name": "caller_system", "required": True},
        {"name": "account", "default": "prod-x"},
    ],
    "entity_defaults": {
        "all": {"status": "Planned", "company_domain": "Probing"},
        "systems": {"owner_org_id": "ORG-TECH", "criticality": "High", "hosting": "AWS",
                    "cloud_provider": "AWS", "cloud_account": "{account}",
                    "environment": "Production", "tags": ["probe"]},
        "interfaces": {"owner_org_id": "ORG-TECH", "protocol": "HTTPS", "direction": "Outbound",
                       "frequency": "Realtime", "integration_style": "Request-response",
                       "auth_method": "MutualTLS"},
    },
    "modules": [
        {"module": "vendor-tenancy", "with": {"vendor": "{vendor}"}},
        {"module": "api-outbound", "with": {"caller_system": "{caller_system}"}},
        "private-egress",
        "sftp-return-feed",
    ],
}


def _instance(**extra) -> dict:
    base = {"product_id": "PRD-P", "name": "Probe", "status": "Planned",
            "owner_org_id": "ORG-TECH",
            "parameters": {"slug": "probe", "vendor": "Acme", "caller_system": "SYS-AUTH-SWITCH"}}
    base.update(extra)
    return base


def _ids(expansion, type_name: str):
    pk = ENTITY_TYPES[type_name].pk
    return sorted(r[pk] for r in expansion.entities.get(type_name, []))


class TestModuleLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.modules = load_modules(REPO)

    def test_the_library_loads_and_every_part_provides_something(self) -> None:
        self.assertGreaterEqual(len(self.modules), 20)
        for module in self.modules.values():
            self.assertTrue(module.description, module.module_id)
            self.assertGreater(
                provided_count(module, self.modules) + sum(len(v) for v in module.relations.values()),
                0, module.module_id,
            )

    def test_requirements_name_parts_that_exist(self) -> None:
        for module in self.modules.values():
            for needed in module.requires:
                self.assertIn(needed, self.modules, "%s requires %s" % (module.module_id, needed))

    def test_a_part_without_a_description_is_refused(self) -> None:
        with self.assertRaises(ModuleError):
            parse_module({"module_id": "x", "name": "X", "provides": {"systems": [{"system_id": "SYS-X"}]}})

    def test_an_empty_part_is_refused(self) -> None:
        with self.assertRaises(ModuleError):
            parse_module({"module_id": "x", "name": "X", "description": "Nothing."})


class TestComposition(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(SHAPE))
        cls.out = expand(_instance(), cls.shape, "products", cls.library)

    def test_the_parts_arrive_together(self) -> None:
        """Four parts, one shape: the vendor, the gateway, the private path
        and the return feed, with the interfaces between them."""
        self.assertEqual(
            _ids(self.out, "systems"),
            ["SYS-PROBE-EGRESS", "SYS-PROBE-GATEWAY", "SYS-PROBE-VENDOR"],
        )
        self.assertEqual(
            _ids(self.out, "interfaces"),
            ["INT-PROBE-CALLER-GATEWAY", "INT-PROBE-EGRESS-VENDOR", "INT-PROBE-GATEWAY-EGRESS",
             "INT-PROBE-VENDOR-RETURN"],
        )
        self.assertEqual(_ids(self.out, "data_assets"), ["DA-PROBE-OUTCOMES"])
        self.assertEqual(
            self.out.modules_applied,
            ["vendor-tenancy", "api-outbound", "private-egress", "sftp-return-feed"],
        )

    def test_every_created_entity_says_which_part_made_it(self) -> None:
        by_id = {r["system_id"]: r for r in self.out.entities["systems"]}
        self.assertEqual(by_id["SYS-PROBE-VENDOR"]["module"], "vendor-tenancy")
        self.assertEqual(by_id["SYS-PROBE-GATEWAY"]["module"], "api-outbound")
        self.assertEqual(by_id["SYS-PROBE-EGRESS"]["module"], "private-egress")

    def test_the_shape_parameters_reach_the_part(self) -> None:
        vendor = next(r for r in self.out.entities["systems"] if r["system_id"] == "SYS-PROBE-VENDOR")
        self.assertEqual(vendor["provider"], "Acme")
        self.assertIsNone(vendor.get("cloud_account"), "a vendor tenancy is not in our account")
        caller = next(r for r in self.out.entities["interfaces"]
                      if r["interface_id"] == "INT-PROBE-CALLER-GATEWAY")
        self.assertEqual(caller["source_system_id"], "SYS-AUTH-SWITCH")

    def test_governance_shorthands_become_enforcement_rows(self) -> None:
        """`controls:` and `policies:` on a template are the register's
        rows, not a note. Third-party due diligence lands on the vendor."""
        governed = {(r["system_id"], r["control_id"])
                    for r in self.out.relations.get("system_governed_by_control", [])}
        self.assertIn(("SYS-PROBE-VENDOR", "CTL-TPRM-DD"), governed)
        policy = {(r["system_id"], r["policy_id"])
                  for r in self.out.relations.get("system_subject_to_policy", [])}
        self.assertIn(("SYS-PROBE-VENDOR", "POL-TPRM"), policy)
        data = {(r["data_asset_id"], r["policy_id"])
                for r in self.out.relations.get("data_subject_to_policy", [])}
        self.assertIn(("DA-PROBE-OUTCOMES", "POL-PRIVACY"), data)

    def test_a_part_brings_its_pattern(self) -> None:
        self.assertIn("private-egress-to-saas", self.out.instance.get("patterns", []))

    def test_every_created_entity_validates(self) -> None:
        for type_name, rows in self.out.entities.items():
            spec = ENTITY_TYPES[type_name]
            for row in rows:
                for field in spec.fields:
                    if field.required:
                        self.assertTrue(row.get(field.name), "%s.%s on %s" % (type_name, field.name, row.get(spec.pk)))


class TestChoosingParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(SHAPE))

    def test_without_drops_a_part_and_what_pointed_at_it(self) -> None:
        out = expand(_instance(without=["sftp-return-feed"]), self.shape, "products", self.library)
        self.assertNotIn("DA-PROBE-OUTCOMES", _ids(out, "data_assets"))
        self.assertNotIn("INT-PROBE-VENDOR-RETURN", _ids(out, "interfaces"))
        self.assertNotIn("sftp-return-feed", out.modules_applied)
        for rows in out.relations.values():
            for row in rows:
                self.assertNotIn("DA-PROBE-OUTCOMES", row.values())

    def test_a_part_another_kept_part_needs_cannot_be_dropped(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(without=["api-outbound"]), self.shape, "products", self.library)
        self.assertIn("private-egress", str(caught.exception))

    def test_dropping_both_is_fine(self) -> None:
        out = expand(_instance(without=["api-outbound", "private-egress"]),
                     self.shape, "products", self.library)
        self.assertEqual(_ids(out, "systems"), ["SYS-PROBE-VENDOR"])

    def test_a_part_the_shape_always_has_cannot_be_dropped(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(_instance(without=["vendor-tenancy"]), self.shape, "products", self.library)

    def test_a_part_that_is_not_in_the_shape_cannot_be_dropped(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(_instance(without=["webhook-inbound"]), self.shape, "products", self.library)

    def test_the_instance_can_add_a_part(self) -> None:
        out = expand(
            _instance(modules=[{"module": "webhook-inbound", "with": {"consumer_system": "SYS-CRM"}}]),
            self.shape, "products", self.library,
        )
        self.assertIn("SYS-PROBE-WEBHOOKS", _ids(out, "systems"))
        self.assertIn("INT-PROBE-WEBHOOKS-CONSUMER", _ids(out, "interfaces"))
        self.assertIn("webhook-inbound", out.modules_applied)

    def test_an_added_part_with_a_missing_required_parameter_is_refused(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(modules=["webhook-inbound"]), self.shape, "products", self.library)
        self.assertIn("consumer_system", str(caught.exception))

    def test_the_instance_can_rebind_a_part(self) -> None:
        """The same gateway part, put on a different platform by the product."""
        out = expand(
            _instance(modules=[{"module": "api-outbound", "with": {"platform": "TS-AZURE-APIM"}}]),
            self.shape, "products", self.library,
        )
        uses = {(r["system_id"], r["tech_service_id"])
                for r in out.relations.get("system_uses_tech_service", [])}
        self.assertIn(("SYS-PROBE-GATEWAY", "TS-AZURE-APIM"), uses)
        self.assertNotIn(("SYS-PROBE-GATEWAY", "TS-AWS-EKS"), uses)
        self.assertEqual(out.modules_applied.count("api-outbound"), 1)

    def test_an_added_part_needs_what_it_requires(self) -> None:
        with self.assertRaises(ArchetypeError):
            expand(_instance(modules=["scim-provisioning"]), self.shape, "products", self.library)


class TestPartsThatCreatePeople(unittest.TestCase):
    """A part provides whatever entity type it names.

    Systems, interfaces and data assets were the only types anybody had
    written one for, which read as a limit of the composer rather than of the
    library. It never was one: the composer walks `provides` by name, so an
    actor costs the same as a system.
    """

    ROLE = {
        "id": "probe-analyst",
        "name": "Probe Analyst",
        "description": "Works the alert queue.",
        "interaction": "Clears alerts",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(SHAPE))

    def _expand(self, modules):
        return expand(_instance(modules=modules), self.shape, "products", self.library)

    def _role_part(self, roles):
        return [{"module": "operator-role",
                 "with": {"system": "SYS-PROBE-VENDOR", "roles": roles}}]

    def test_a_role_the_product_creates_arrives_as_an_actor(self) -> None:
        out = self._expand(self._role_part([self.ROLE]))
        self.assertEqual(_ids(out, "actors"), ["ACT-PROBE-ANALYST"])
        actor = out.entities["actors"][0]
        self.assertEqual(actor["name"], "Probe Analyst")
        self.assertEqual(actor["actor_kind"], "Role")
        self.assertEqual(actor["module"], "operator-role")
        # The shape's `entity_defaults` fold under a part's templates whatever
        # the type is, which is what makes this cheap.
        self.assertEqual(actor["status"], "Planned")
        self.assertEqual(actor["company_domain"], "Probing")

    def test_the_role_is_wired_to_the_system_it_works_in(self) -> None:
        row = self._expand(self._role_part([self.ROLE])).relations["actor_uses_system"][0]
        self.assertEqual(row["actor_id"], "ACT-PROBE-ANALYST")
        self.assertEqual(row["system_id"], "SYS-PROBE-VENDOR")
        self.assertEqual(row["interaction"], "Clears alerts")

    def test_a_product_that_creates_no_role_creates_no_actor(self) -> None:
        """`each` over an empty list produces nothing, which is how the part
        stays optional without a switch of its own."""
        out = self._expand(self._role_part([]))
        self.assertEqual(_ids(out, "actors"), [])
        self.assertEqual(out.relations.get("actor_uses_system", []), [])

    def test_a_role_missing_a_key_fails_by_name_and_says_which_part(self) -> None:
        incomplete = {k: v for k, v in self.ROLE.items() if k != "interaction"}
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(self._role_part([incomplete]))
        message = str(caught.exception)
        self.assertIn("interaction", message)
        self.assertIn("operator-role", message)

    def test_two_people_on_one_system_are_two_rows(self) -> None:
        """A regression. Row de-duplication guessed which columns were the
        endpoints from a list of likely names; for `actor_uses_system` it
        picked `system_id` for both halves of the key, so a second actor on
        the same system was discarded as a repeat of the first."""
        out = self._expand([
            {"module": "operator-access", "as": "cardholder",
             "with": {"actor": "ACT-CARDHOLDER", "system": "SYS-PROBE-VENDOR",
                      "interaction": "Self-service"}},
            {"module": "operator-access", "as": "regulator",
             "with": {"actor": "ACT-REGULATOR", "system": "SYS-PROBE-VENDOR",
                      "interaction": "Inspects"}},
        ])
        rows = out.relations["actor_uses_system"]
        self.assertEqual(
            {r["actor_id"] for r in rows}, {"ACT-CARDHOLDER", "ACT-REGULATOR"}
        )

    def test_the_same_actor_doing_two_different_things_is_two_rows(self) -> None:
        """The qualifier was not in the key at all, so an actor who both used a
        system and administered it was recorded as doing only the first."""
        out = self._expand([
            {"module": "operator-access", "as": "uses",
             "with": {"actor": "ACT-CARDHOLDER", "system": "SYS-PROBE-VENDOR",
                      "interaction": "Self-service"}},
            {"module": "operator-access", "as": "administers",
             "with": {"actor": "ACT-CARDHOLDER", "system": "SYS-PROBE-VENDOR",
                      "interaction": "Administers"}},
        ])
        self.assertEqual(
            sorted(r["interaction"] for r in out.relations["actor_uses_system"]),
            ["Administers", "Self-service"],
        )

    def test_an_exact_repeat_is_still_one_row(self) -> None:
        """The de-duplication is there because a block, a `uses` shorthand and
        a part can each produce the same row. Fixing the key must not cost
        that."""
        same = {"actor": "ACT-CARDHOLDER", "system": "SYS-PROBE-VENDOR",
                "interaction": "Self-service"}
        out = self._expand([
            {"module": "operator-access", "as": "once", "with": dict(same)},
            {"module": "operator-access", "as": "again", "with": dict(same)},
        ])
        self.assertEqual(len(out.relations["actor_uses_system"]), 1)


KIT_SHAPE = dict(SHAPE, modules=[
    {"module": "vendor-baseline", "with": {"vendor": "{vendor}", "caller_system": "{caller_system}"}},
    "private-egress",
    "sftp-return-feed",
])

SLOT_SHAPE = dict(SHAPE, modules=[
    {"module": "vendor-tenancy", "with": {"vendor": "{vendor}"}},
    {"module": "api-outbound", "with": {"caller_system": "{caller_system}"}},
], slots=[
    {"name": "reach", "description": "How our side gets to the vendor",
     "options": ["private-egress", "public-call"], "default": "private-egress"},
    {"name": "return", "options": ["sftp-return-feed", "webhook-inbound"],
     "default": "sftp-return-feed", "optional": True},
])


class TestContracts(unittest.TestCase):
    """What a part needs from the shape is declared, and checked twice: when
    the library loads, and before any template of it is read."""

    MINIMAL = {"module_id": "probe-part", "name": "Probe part", "description": "A probe."}

    def test_a_part_reading_an_undeclared_token_does_not_load(self) -> None:
        with self.assertRaises(ModuleError) as caught:
            parse_module(dict(self.MINIMAL, provides={"systems": [
                {"system_id": "SYS-{slug|upper}-P", "name": "{product_name} for {vendor}"}]}))
        for token in ("{slug}", "{product_name}", "{vendor}"):
            self.assertIn(token, str(caught.exception))

    def test_declaring_needs_is_what_makes_it_load(self) -> None:
        module = parse_module(dict(
            self.MINIMAL, needs=["slug", "product_name", "vendor"],
            provides={"systems": [{"system_id": "SYS-{slug|upper}-P", "name": "{product_name} for {vendor}"}]},
        ))
        self.assertEqual(list(module.needs), ["slug", "product_name", "vendor"])

    def test_a_parameter_default_is_read_too(self) -> None:
        """`operator-access` defaults its system to `SYS-{slug|upper}-VENDOR`,
        which reads `slug` as surely as a template does."""
        with self.assertRaises(ModuleError):
            parse_module(dict(
                self.MINIMAL, parameters=[{"name": "system", "default": "SYS-{slug|upper}-VENDOR"}],
                relations={"actor_uses_system": [{"actor_id": "ACT-X", "system_id": "{system}"}]},
            ))

    def test_a_need_that_is_also_a_parameter_is_refused(self) -> None:
        with self.assertRaises(ModuleError):
            parse_module(dict(self.MINIMAL, needs=["vendor"], parameters=["vendor"],
                              provides={"systems": [{"system_id": "SYS-P", "name": "{vendor}"}]}))

    def test_an_each_template_is_exempt_because_its_keys_are_data(self) -> None:
        module = parse_module(dict(
            self.MINIMAL, parameters=["roles"],
            provides={"actors": [{"each": "{roles}", "actor_id": "ACT-{item|upper}", "name": "{name}"}]},
        ))
        self.assertEqual(list(module.needs), [])

    def test_every_shipped_part_declares_what_it_reads(self) -> None:
        for module in load_modules(REPO).values():
            with self.subTest(module=module.module_id):
                self.assertEqual(undeclared_tokens(module), set())

    def test_a_shape_that_cannot_bind_a_need_is_refused_by_name(self) -> None:
        shape = dict(SHAPE, parameters=[p for p in SHAPE["parameters"] if p["name"] != "product_name"])
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(), parse_archetype(shape), "products", _library())
        message = str(caught.exception)
        self.assertIn("vendor-tenancy", message)
        self.assertIn("{product_name}", message)

    def test_validate_refuses_the_same_shape_before_any_instance_exists(self) -> None:
        model = seeded_model()
        shape = dict(SHAPE, parameters=[p for p in SHAPE["parameters"] if p["name"] != "product_name"])
        model.archetypes["probe-broken"] = parse_archetype(shape)
        errors = [f for f in validate.run(model).errors if f.code == "library.unbound_need"]
        self.assertTrue(errors)
        self.assertIn("{product_name}", errors[0].message)


class TestKits(unittest.TestCase):
    """A kit is a part made of parts: one name for the group, its members'
    own aliases underneath."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(KIT_SHAPE))

    def _expand(self, **extra):
        return expand(_instance(**extra), self.shape, "products", self.library)

    def _gateway_uses(self, out):
        return {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])
                if r["system_id"] == "SYS-PROBE-GATEWAY"}

    def test_a_kit_flattens_to_its_members_under_their_own_aliases(self) -> None:
        out = self._expand()
        self.assertEqual(out.modules_applied, ["vendor-tenancy", "api-outbound", "secrets-management",
                                               "private-egress", "sftp-return-feed"])
        self.assertEqual(_ids(out, "systems"), ["SYS-PROBE-EGRESS", "SYS-PROBE-GATEWAY", "SYS-PROBE-VENDOR"])

    def test_a_member_resolves_its_kind_through_the_shape(self) -> None:
        """The kit carries nothing cloud-specific. Its vault member says it
        needs a secrets manager, and the shape's `bind` says which."""
        self.assertIn("TS-AWS-SECRETS", self._gateway_uses(self._expand()))

    def test_a_member_can_be_re_bound_on_its_own(self) -> None:
        """Naming a member the kit already brought re-binds it, so a product
        does not restate the kit to change one value."""
        out = self._expand(modules=[{"module": "secrets-management", "with": {"vault": "TS-AZURE-KEYVAULT"}}])
        self.assertIn("TS-AZURE-KEYVAULT", self._gateway_uses(out))
        self.assertEqual(out.modules_applied.count("secrets-management"), 1)

    def test_a_member_can_be_dropped_on_its_own(self) -> None:
        out = self._expand(without=["secrets-management"])
        self.assertNotIn("secrets-management", out.modules_applied)
        self.assertIn("api-outbound", out.modules_applied)

    def test_dropping_the_kit_drops_its_members_and_so_is_refused_here(self) -> None:
        """Because the tenancy cannot be dropped, and it is in the kit."""
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(without=["vendor-baseline"])
        self.assertIn("vendor-tenancy", str(caught.exception))

    def test_a_part_required_by_another_is_seen_through_the_kit(self) -> None:
        """`private-egress` requires the tenancy and the gateway, both of
        which arrived inside the kit rather than as listed parts."""
        self.assertIn("private-egress", self._expand().modules_applied)

    def test_a_member_the_shape_also_lists_first_is_refused(self) -> None:
        shape = dict(KIT_SHAPE, modules=["vendor-tenancy"] + list(KIT_SHAPE["modules"]))
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(), parse_archetype(shape), "products", self.library)
        self.assertIn("once through kit vendor-baseline", str(caught.exception))

    def test_a_kit_that_contains_itself_is_refused(self) -> None:
        a = parse_module({"module_id": "kit-a", "name": "A", "description": "x", "modules": ["kit-b"]})
        b = parse_module({"module_id": "kit-b", "name": "B", "description": "x", "modules": ["kit-a"]})
        with self.assertRaises(ModuleError) as caught:
            _check_kits({"kit-a": a, "kit-b": b})
        self.assertIn("kit-a > kit-b > kit-a", str(caught.exception))

    def test_a_kit_counts_what_its_members_make(self) -> None:
        modules = self.library[2]
        self.assertEqual(
            provided_count(modules["vendor-baseline"], modules),
            sum(provided_count(modules[m]) for m in ("vendor-tenancy", "api-outbound", "secrets-management")),
        )


class TestSlots(unittest.TestCase):
    """A slot is one need and the parts that can fill it. The shape names the
    default; the instance chooses; nothing else touches it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shape = parse_archetype(dict(SLOT_SHAPE))

    def _expand(self, **extra):
        return expand(_instance(**extra), self.shape, "products", self.library)

    def test_the_default_fills_the_slot_when_the_instance_says_nothing(self) -> None:
        out = self._expand()
        self.assertEqual(out.choices, {"reach": "private-egress", "return": "sftp-return-feed"})
        self.assertIn("SYS-PROBE-EGRESS", _ids(out, "systems"))
        self.assertEqual(_ids(out, "data_assets"), ["DA-PROBE-OUTCOMES"])

    def test_the_instance_chooses(self) -> None:
        out = self._expand(choose={"reach": "public-call"})
        self.assertNotIn("SYS-PROBE-EGRESS", _ids(out, "systems"))
        self.assertIn("INT-PROBE-GATEWAY-VENDOR", _ids(out, "interfaces"))
        self.assertEqual(out.choices["reach"], "public-call")

    def test_an_option_the_slot_does_not_offer_is_refused_with_the_options_named(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(choose={"reach": "sso-federation"})
        self.assertIn("private-egress, public-call", str(caught.exception))

    def test_a_slot_the_shape_does_not_have_is_refused(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(choose={"reaches": "public-call"})
        self.assertIn("reaches", str(caught.exception))

    def test_an_optional_slot_may_be_left_empty(self) -> None:
        out = self._expand(choose={"return": "none"})
        self.assertEqual(out.choices["return"], "")
        self.assertEqual(_ids(out, "data_assets"), [])

    def test_a_required_slot_may_not_be(self) -> None:
        with self.assertRaises(ArchetypeError):
            self._expand(choose={"reach": "none"})

    def test_a_required_slot_with_no_default_must_be_chosen(self) -> None:
        shape = dict(SLOT_SHAPE, slots=[dict(SLOT_SHAPE["slots"][0], default=None)])
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(), parse_archetype(shape), "products", self.library)
        self.assertIn("reach", str(caught.exception))
        out = expand(_instance(choose={"reach": "public-call"}), parse_archetype(shape), "products", self.library)
        self.assertEqual(out.choices["reach"], "public-call")

    ANSWERED = dict(SLOT_SHAPE, slots=[
        SLOT_SHAPE["slots"][0],
        dict(SLOT_SHAPE["slots"][1], default="webhook-inbound",
             **{"with": {"webhook-inbound": {"consumer_system": "{caller_system}"}}}),
    ])

    def _consumer(self, out):
        return next(r for r in out.entities["interfaces"] if r["interface_id"] == "INT-PROBE-WEBHOOKS-CONSUMER")

    def test_a_slot_option_arrives_with_what_the_shape_answers_for_it(self) -> None:
        """The listener asks who consumes the vendor's events. The shape knows
        who called the vendor and says so under the slot's `with`, so a
        product on the default says nothing; without it, the default could
        not expand at all."""
        bare = dict(SLOT_SHAPE, slots=[SLOT_SHAPE["slots"][0], dict(SLOT_SHAPE["slots"][1], default="webhook-inbound")])
        with self.assertRaises(ArchetypeError) as caught:
            expand(_instance(), parse_archetype(bare), "products", self.library)
        self.assertIn("consumer_system", str(caught.exception))
        out = expand(_instance(), parse_archetype(self.ANSWERED), "products", self.library)
        self.assertEqual(self._consumer(out)["target_system_id"], "SYS-AUTH-SWITCH")

    def test_the_product_s_own_answer_for_the_part_wins(self) -> None:
        out = expand(
            _instance(modules=[{"module": "webhook-inbound", "with": {"consumer_system": "SYS-CORE-LEDGER"}}]),
            parse_archetype(self.ANSWERED), "products", self.library,
        )
        self.assertEqual(self._consumer(out)["target_system_id"], "SYS-CORE-LEDGER")

    def test_an_answer_for_a_part_the_slot_does_not_offer_is_refused(self) -> None:
        shape = dict(SLOT_SHAPE, slots=[
            SLOT_SHAPE["slots"][0],
            dict(SLOT_SHAPE["slots"][1], **{"with": {"api-outbound": {"caller_system": "SYS-X"}}}),
        ])
        with self.assertRaises(ArchetypeError) as caught:
            parse_archetype(shape)
        self.assertIn("sftp-return-feed, webhook-inbound", str(caught.exception))

    def test_kept_ids_rename_every_record_and_row_the_shape_makes(self) -> None:
        """`ids` maps what the shape makes to what the estate calls it; the
        record, the interfaces that join it, the relation rows and the
        governance the part carries all follow."""
        out = self._expand(choose={"reach": "public-call"},
                           ids={"SYS-PROBE-VENDOR": "SYS-PROBE-SAAS", "INT-PROBE-GATEWAY-VENDOR": "INT-PROBE-GATEWAY-SAAS"})
        self.assertIn("SYS-PROBE-SAAS", _ids(out, "systems"))
        self.assertNotIn("SYS-PROBE-VENDOR", _ids(out, "systems"))
        gateway = next(r for r in out.entities["interfaces"] if r["interface_id"] == "INT-PROBE-GATEWAY-SAAS")
        self.assertEqual(gateway["target_system_id"], "SYS-PROBE-SAAS")
        included = {row["system_id"] for row in out.relations["product_includes_system"]}
        self.assertIn("SYS-PROBE-SAAS", included)
        self.assertNotIn("SYS-PROBE-VENDOR", included)
        governed = {row["system_id"] for row in out.relations["system_governed_by_control"]}
        self.assertIn("SYS-PROBE-SAAS", governed)
        self.assertNotIn("SYS-PROBE-VENDOR", governed)

    def test_overrides_and_exclusions_may_use_the_kept_names(self) -> None:
        out = self._expand(ids={"SYS-PROBE-VENDOR": "SYS-PROBE-SAAS"}, overrides={"SYS-PROBE-SAAS": {"name": "Kept"}})
        self.assertEqual(next(r for r in out.entities["systems"] if r["system_id"] == "SYS-PROBE-SAAS")["name"], "Kept")

    def test_an_id_the_shape_does_not_make_cannot_be_kept(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(ids={"SYS-PROBE-NOPE": "SYS-PROBE-X"})
        self.assertIn("does not make", str(caught.exception))
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(ids={"SYS-PROBE-VENDOR": "SYS-PROBE-GATEWAY"})
        self.assertIn("makes as well", str(caught.exception))

    def test_what_fills_a_slot_is_changed_by_choosing_not_by_dropping(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(without=["private-egress"])
        self.assertIn("choose", str(caught.exception))

    def test_a_chosen_part_can_be_re_bound_like_any_other(self) -> None:
        out = self._expand(modules=[{"module": "sftp-return-feed", "with": {"ingest_system": "SYS-CRM"}}])
        rows = out.relations.get("system_reads_writes", [])
        self.assertIn("SYS-CRM", {r["system_id"] for r in rows})

    def test_an_option_that_is_always_composed_is_refused_at_parse(self) -> None:
        with self.assertRaises(ArchetypeError):
            parse_archetype(dict(SLOT_SHAPE, modules=list(SLOT_SHAPE["modules"]) + ["private-egress"]))

    def test_a_default_outside_the_options_is_refused_at_parse(self) -> None:
        with self.assertRaises(ArchetypeError):
            parse_archetype(dict(SLOT_SHAPE, slots=[dict(SLOT_SHAPE["slots"][0], default="sso-federation")]))


class TestTheLibraryKnowsItself(unittest.TestCase):
    """Where each part is used, and which are used by nothing."""

    def test_a_part_nothing_composes_is_reported_and_a_slot_option_is_not(self) -> None:
        report = validate.run(seeded_model())
        unused = {f.message.split()[1] for f in report.warnings if f.code == "library.unused_part"}
        # Every shipped part is on a shape, in a kit, behind a slot or on a
        # build type's menu; byok-encryption is on the bought-saas menu.
        self.assertEqual(unused, set())
        with Sandbox() as root:
            (root / "28_MODULES" / "orphan.yaml").write_text(
                "- module_id: orphan-part\n  name: Orphan\n  category: Test\n"
                "  description: A part nothing lists.\n  needs: [slug]\n"
                "  provides:\n    systems:\n      - system_id: \"SYS-{slug|upper}-ORPHAN\"\n"
                "        name: Orphan\n        system_category: Application\n        network_zone: Private-App\n",
                encoding="utf-8",
            )
            report = validate.run(model_module.load(root))
            unused = {f.message.split()[1] for f in report.warnings if f.code == "library.unused_part"}
            self.assertEqual(unused, {"orphan-part"})
            self.assertNotIn("webhook-inbound", unused)
            self.assertNotIn("secrets-management", unused)

    def test_uses_of_says_how_each_part_is_reached(self) -> None:
        modules = load_modules(REPO)
        uses = uses_of(modules, load_archetypes(REPO).values())
        self.assertIn("kit vendor-baseline", uses["secrets-management"])
        self.assertTrue(any("slot reach" in by for by in uses["public-call"]))
        self.assertEqual(uses["byok-encryption"], [])


class TestKinds(unittest.TestCase):
    """A part names the kind of shared service a parameter stands for; the
    shape binds the kind to the service that is that kind on its landing
    zone. Nothing in the library names a cloud."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()

    def _expand(self, shape: dict, **extra):
        return expand(_instance(**extra), parse_archetype(shape), "products", self.library)

    def _gateway_uses(self, out):
        return {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])
                if r["system_id"] == "SYS-PROBE-GATEWAY"}

    def test_no_shipped_part_names_a_cloud(self) -> None:
        """Fourteen defaults used to. A part that says `TS-AWS-EKS` is a part
        for one cloud, and a part chosen in a slot on the Azure shape bound
        AWS services because of it."""
        for module in load_modules(REPO).values():
            for param in module.parameters:
                with self.subTest(module=module.module_id, parameter=param.name):
                    self.assertFalse(
                        isinstance(param.default, str)
                        and param.default.startswith(("TS-AWS-", "TS-AZURE-")),
                        "%s.%s defaults to %s" % (module.module_id, param.name, param.default),
                    )

    def test_a_parameter_that_names_a_kind_is_not_asked_of_the_instance(self) -> None:
        module = parse_module({
            "module_id": "p", "name": "p", "description": "x", "needs": ["slug"],
            "parameters": [{"name": "platform", "component": "container-platform"}],
            "provides": {"systems": [{"system_id": "SYS-{slug|upper}-P", "name": "P", "uses": ["{platform}"]}]},
        })
        self.assertEqual(module.parameters[0].component, "container-platform")
        self.assertFalse(module.parameters[0].required)

    def test_the_shape_binds_the_kind(self) -> None:
        uses = self._gateway_uses(self._expand(dict(SHAPE)))
        self.assertIn("TS-AWS-APIGW", uses)  # api-outbound's front door: an api-gateway
        self.assertIn("TS-AWS-EKS", uses)    # its platform: a container-platform

    def test_with_wins_over_the_bind(self) -> None:
        out = self._expand(dict(SHAPE), modules=[{"module": "api-outbound", "with": {"front_door": "TS-AZURE-APIM"}}])
        self.assertIn("TS-AZURE-APIM", self._gateway_uses(out))
        self.assertNotIn("TS-AWS-APIGW", self._gateway_uses(out))

    def test_a_block_bind_counts_and_the_shape_wins(self) -> None:
        shape = parse_archetype(dict(
            SHAPE, bind={"api-gateway": "TS-AWS-APIGW"},
            blocks=[{"block": "public-api-tier", "bind": {"api-gateway": "TS-AZURE-APIM", "dns": "TS-NET-ROUTE53"}}],
        ))
        zone = effective_bind(shape)
        self.assertEqual(zone["dns"], "TS-NET-ROUTE53")
        self.assertEqual(zone["api-gateway"], "TS-AWS-APIGW")

    def test_two_blocks_binding_one_kind_two_ways_is_refused(self) -> None:
        shape = parse_archetype(dict(SHAPE, bind={}, blocks=[
            {"block": "public-api-tier", "as": "a", "bind": {"api-gateway": "TS-AWS-APIGW"}},
            {"block": "public-api-tier", "as": "b", "bind": {"api-gateway": "TS-AZURE-APIM"}},
        ]))
        with self.assertRaises(ArchetypeError) as caught:
            effective_bind(shape)
        self.assertIn("api-gateway", str(caught.exception))

    def test_a_kind_nothing_can_answer_for_is_refused_by_kind(self) -> None:
        """On a provider with no landing zone at all, and with no bind, the
        part is refused by kind with the line to add. Google Cloud was that
        provider until its zone was modeled; Oracle's cloud stands in."""
        shape = dict(SHAPE, bind={}, provider="OCI")
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(shape)
        message = str(caught.exception)
        self.assertIn("api-outbound", message)
        self.assertIn("landing-zone", message)
        self.assertIn("bind:", message)

    def test_a_default_stands_where_the_shape_binds_nothing(self) -> None:
        """The identity provider is the same on every cloud, so the federation
        part keeps a default; a shape that binds `identity-provider` overrides it."""
        out = self._expand(dict(SHAPE, modules=list(SHAPE["modules"]) + ["sso-federation"]))
        uses = {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])}
        self.assertIn("TS-ENTRA-ID", uses)

    def test_validate_refuses_a_kind_nothing_can_answer_for(self) -> None:
        """A shape with no bind is fine where the landing zone has the kind.
        Where it does not -- an event stream on a landing zone with none --
        the shape is refused with the tag and the line to add. On a provider
        with no landing zone at all it waits instead, as on an empty model:
        the data center holds one tagged service, so it has a zone; Oracle
        Cloud holds none, and a neutral identity provider does not make one."""
        model = seeded_model()
        model.archetypes["probe-unbound"] = parse_archetype(dict(
            SHAPE, archetype_id="probe-unbound", bind={}, provider="On-prem",
            modules=list(SHAPE["modules"]) + ["async-worker"],
        ))
        model.archetypes["probe-elsewhere"] = parse_archetype(dict(
            SHAPE, archetype_id="probe-elsewhere", bind={}, provider="OCI",
            modules=list(SHAPE["modules"]) + ["async-worker"],
        ))
        report = validate.run(model)
        errors = [f for f in report.errors if f.code == "library.unbound_component"]
        self.assertTrue(errors)
        self.assertTrue(all("probe-unbound" in f.message for f in errors))
        self.assertIn("bind: {", errors[0].message)
        self.assertIn("landing-zone", errors[0].message)
        waiting = [f.message for f in report.warnings if f.code == "library.no_landing_zone"]
        self.assertTrue(any("probe-elsewhere" in m and "on OCI" in m for m in waiting), waiting)

    def test_validate_refuses_a_bind_to_a_service_that_does_not_exist(self) -> None:
        model = seeded_model()
        model.archetypes["probe-ghost"] = parse_archetype(
            dict(SHAPE, bind=dict(SHAPE["bind"], **{"api-gateway": "TS-NOWHERE"})))
        errors = [f for f in validate.run(model).errors if f.code == "library.bind_unknown"]
        self.assertTrue(errors)
        self.assertIn("TS-NOWHERE", errors[0].message)


class TestTheLandingZoneKnowsItsGaps(unittest.TestCase):
    """The kinds the parts name that a provider's landing zone cannot answer,
    said ahead of any shape asking, and measured against the providers the
    shapes land on rather than every provider with a tagged service."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.modules = load_modules(REPO)
        cls.shapes = list(load_archetypes(REPO).values())
        cls.zone = landing_zone_index(seeded_model().all_of("tech_services"))

    def _gaps(self, zone=None):
        zone = self.zone if zone is None else zone
        return {(g.provider, g.kind): g for g in landing_zone_gaps(self.modules, self.shapes, zone)}

    def test_only_the_providers_shapes_land_on_are_measured(self) -> None:
        """The on-prem data center carries the tag and is one `vpc`; nothing
        lands there, so it is not a landing zone with nine gaps."""
        self.assertEqual(landing_providers(self.shapes), ["AWS", "Azure", "GCP"])
        self.assertFalse([p for p, _k in self._gaps() if p not in ("AWS", "Azure", "GCP")])

    def test_a_kind_no_tagged_service_answers_for_is_a_gap_naming_the_parts_that_ask(self) -> None:
        """Azure had no event stream until the rewards product's worker asked
        for one and Event Hubs was tagged; without that record the gap is
        back, naming the part."""
        without = {key: ids for key, ids in self.zone.items() if key != ("Azure", "event-stream")}
        gap = self._gaps(without)[("Azure", "event-stream")]
        self.assertEqual(gap.asked_by, (("async-worker", "stream"),))
        self.assertEqual(gap.bound_by, ())
        self.assertEqual(self._gaps(), {}, "the shipped landing zones answer for every kind asked")

    def test_a_kind_a_shape_binds_by_hand_is_still_a_gap_and_the_shape_is_named(self) -> None:
        """With Key Vault not answering for `kms` -- as it did not until the
        record said so -- a shape that binds the kind by hand is the only
        thing composing a kms part there. The next Azure shape would have to
        say the same, so it is a gap, and the shape that binds it is the fix
        to copy. No shipped shape binds by hand any more: the Azure product
        shape binds `kms: landing-zone`, which is the gap itself."""
        without = {key: ids for key, ids in self.zone.items() if key != ("Azure", "kms")}
        self.assertEqual(self._gaps(without)[("Azure", "kms")].bound_by, ())
        by_hand = parse_archetype({
            "archetype_id": "probe-by-hand", "applies_to": "products", "provider": "Azure",
            "bind": {"kms": "TS-AZURE-KEYVAULT"},
        })
        gaps = {(g.provider, g.kind): g
                for g in landing_zone_gaps(self.modules, self.shapes + [by_hand], without)}
        self.assertEqual(gaps[("Azure", "kms")].bound_by, ("probe-by-hand",))

    def test_a_service_that_is_two_kinds_answers_for_both(self) -> None:
        """Key Vault is the secrets manager and the key management on Azure,
        and `component_type` is one value; `answers_for` is the second. The
        kms gap on Azure closed the day the record said so."""
        self.assertEqual(self.zone[("Azure", "secrets-manager")], ["TS-AZURE-KEYVAULT"])
        self.assertEqual(self.zone[("Azure", "kms")], ["TS-AZURE-KEYVAULT"])
        self.assertNotIn(("Azure", "kms"), self._gaps())
        # Written as a list in YAML, as a semicolon string out of a CSV.
        for form in (["kms", "hsm"], "kms;hsm", "kms, hsm"):
            zone = landing_zone_index([{
                "tech_service_id": "TS-P", "cloud_provider": "GCP", "tags": ["landing-zone"],
                "component_type": "secrets-manager", "answers_for": form,
            }])
            self.assertEqual(sorted(k for _p, k in zone), ["hsm", "kms", "secrets-manager"])

    def test_a_kind_the_library_does_not_hold_is_an_error(self) -> None:
        """A misspelled kind on the one tagged service is exactly the gap nothing
        else would find: the service draws fine and never answers."""
        model = seeded_model()
        record = next(s for s in model.all_of("tech_services") if s["tech_service_id"] == "TS-AZURE-KEYVAULT")
        original = record.get("answers_for")
        record["answers_for"] = ["kms", "key-managment"]
        try:
            errors = [f for f in validate.run(model).errors if f.code == "library.unknown_kind"]
        finally:
            record["answers_for"] = original
        self.assertEqual(len(errors), 1)
        self.assertIn("TS-AZURE-KEYVAULT says it is a `key-managment`", errors[0].message)

    def test_validate_names_the_shape_that_binds_a_gap_by_hand(self) -> None:
        model = seeded_model()
        model.archetypes["probe-by-hand"] = parse_archetype({
            "archetype_id": "probe-by-hand", "applies_to": "products", "provider": "Azure",
            "bind": {"kms": "TS-AZURE-KEYVAULT"},
        })
        record = next(s for s in model.all_of("tech_services") if s["tech_service_id"] == "TS-AZURE-KEYVAULT")
        original = record.get("answers_for")
        record["answers_for"] = []
        try:
            report = validate.run(model)
        finally:
            record["answers_for"] = original
        messages = [f.message for f in report.warnings if f.code == "library.landing_zone_gap"]
        self.assertTrue(
            any("`kms`" in m and "probe-by-hand binds it by hand" in m for m in messages),
            messages,
        )
        # And the Azure product shape, which binds its store's key to the
        # landing zone, is refused there: it would not compose.
        refused = [f.message for f in report.errors if f.code == "library.unbound_component"]
        self.assertTrue(
            any("azure-digital-product binds `kms`" in m and "to the landing zone" in m for m in refused),
            refused,
        )

    def test_a_kind_the_zone_has_or_a_shared_service_answers_is_not_a_gap(self) -> None:
        gaps = self._gaps()
        self.assertNotIn(("AWS", "api-gateway"), gaps)
        self.assertNotIn(("AWS", "identity-provider"), gaps)  # Entra answers on every cloud
        self.assertNotIn(("Azure", "identity-provider"), gaps)

    def test_a_part_with_a_default_does_not_ask_the_landing_zone(self) -> None:
        def part(module_id: str, **parameter):
            return parse_module({
                "module_id": module_id, "name": module_id, "description": "x", "needs": ["slug"],
                "parameters": [dict(name="keys", component="kms", **parameter)],
                "provides": {"systems": [{"system_id": "SYS-{slug|upper}-K", "name": "K", "uses": ["{keys}"]}]},
            })
        parts = {"asks": part("asks"), "brings": part("brings", default="TS-OUR-KEYS")}
        # An Azure landing zone with something in it: a provider with none at
        # all has no gaps, only the wait each shape on it reports.
        zone = {("Azure", "api-gateway"): ["TS-GW"]}
        gap = {(g.provider, g.kind): g for g in landing_zone_gaps(parts, self.shapes, zone)}[("Azure", "kms")]
        self.assertEqual(gap.asked_by, (("asks", "keys"),))

    def test_the_queue_the_aws_landing_zone_did_not_have(self) -> None:
        """Four parts ask for a `message-queue`; until SQS carried the tag,
        none could have landed on AWS, and nothing said so."""
        without = {key: ids for key, ids in self.zone.items() if key != ("AWS", "message-queue")}
        gap = self._gaps(without)[("AWS", "message-queue")]
        self.assertEqual([m for m, _p in gap.asked_by],
                         ["event-consumer", "event-hub", "event-publisher", "notification-service"])
        self.assertNotIn(("AWS", "message-queue"), self._gaps())

    def test_validate_says_each_gap_once_as_a_warning_with_the_fix(self) -> None:
        shipped = validate.run(seeded_model())
        self.assertFalse([f for f in shipped.warnings if f.code == "library.landing_zone_gap"])
        # Untag Event Hubs and the gap the rewards product closed is back.
        model = seeded_model()
        record = next(s for s in model.all_of("tech_services") if s["tech_service_id"] == "TS-AZURE-EVENTHUBS")
        original = record.get("tags")
        record["tags"] = [t for t in model.list_of(record, "tags") if t != "landing-zone"]
        try:
            report = validate.run(model)
        finally:
            record["tags"] = original
        messages = [f.message for f in report.warnings if f.code == "library.landing_zone_gap"]
        self.assertIn(
            "the Azure landing zone answers for no `event-stream`; async-worker (stream) asks "
            "for one; tag a service of that kind on Azure `landing-zone`, or every shape there "
            "binds it",
            messages,
        )
        self.assertEqual(len(messages), len(set(messages)))
        self.assertFalse([f for f in report.errors if f.code == "library.landing_zone_gap"])


class TestShapeAdoption(unittest.TestCase):
    """Who is on a shape and how far they have moved, and who could be.
    Against the repository's own model: the seed is an export whose products
    carry no archetype, so there nobody is on a shape."""

    @classmethod
    def setUpClass(cls) -> None:
        from terrane import model as model_module

        cls.live = model_module.load(REPO)
        cls.modules = load_modules(REPO)
        cls.shapes = list(cls.live.archetypes.values())
        cls.drift = {d.product_id: d for d in drifts(cls.live, cls.shapes, cls.modules)}
        cls.fits = candidates(cls.live, cls.shapes, cls.modules)

    def test_drift_is_read_off_the_product_file(self) -> None:
        """The loaded record has its instance keys stripped; the file has
        what the product said beyond its shape."""
        rewards = self.drift["PRD-REWARDS"]
        self.assertEqual(rewards.added, ["async-worker"])
        self.assertEqual(rewards.extras, {"interfaces": 1})
        self.assertEqual(rewards.overrides, ["SYS-REWARDS-API", "SYS-REWARDS-WORKER"])
        self.assertEqual(rewards.answered_defaults, [], "uksouth is the shape's own default")
        self.assertEqual(rewards.moves, 4)

    def test_a_choice_against_the_default_is_a_move_and_the_default_is_not(self) -> None:
        self.assertEqual(self.drift["PRD-IDV"].choices["reach"], ("private-egress", False))
        self.assertEqual(self.drift["PRD-SCREENING"].choices["reach"], ("private-egress", True))

    def test_a_shape_s_footprint_is_what_its_parts_make(self) -> None:
        azure = next(a for a in self.shapes if a.archetype_id == "azure-digital-product")
        rows = part_categories(azure, self.modules)
        self.assertEqual(
            [(alias, category) for alias, category, _required in rows],
            [("api-service", "Application"), ("web-channel", "Channel"),
             ("relational-datastore", "Datastore"), ("event-publisher", "Integration")],
        )
        self.assertEqual([alias for alias, _c, required in rows if required], ["api-service"])

    def test_in_the_seed_every_product_is_a_candidate_and_in_the_repository_none_is_left(self) -> None:
        """The seed is an export in which no product carries a shape, so there
        the products that moved are what they were before they did:
        candidates for the shape they now sit on. In the repository every
        product a shape would reproduce is on it."""
        seeded = seeded_model()
        by = {(c.product_id, c.archetype_id): c
              for c in candidates(seeded, list(seeded.archetypes.values()), self.modules)}
        collections = by[("PRD-COLLECTIONS-WORKSPACE", "azure-digital-product")]
        self.assertEqual([alias for alias, _c in collections.missing_optional], ["event-publisher"])
        # Three of the Azure shape's four parts fit better than three of the
        # AWS shape's seven, so the tie goes one way.
        self.assertNotIn(("PRD-COLLECTIONS-WORKSPACE", "aws-product-onboarding"), by)
        self.assertIn(("PRD-CARD-SERVICING", "azure-digital-product"), by)
        self.assertIn(("PRD-DISPUTES", "vendor-saas-service"), by)
        self.assertEqual(self.fits, [])

    def test_the_estate_s_names_survive_a_shape_that_named_them_otherwise(self) -> None:
        """The vendor shape says `-VENDOR` where the estate said `-SAAS`;
        `ids` keeps the estate's names, and everything the shape makes
        follows them, so what pointed at them did not change."""
        vendor = self.live.get("systems", "SYS-DISPUTES-SAAS")
        self.assertEqual(vendor["archetype_instance"], "PRD-DISPUTES")
        self.assertEqual(vendor["name"], "Pega Smart Dispute")
        self.assertIsNone(self.live.get("systems", "SYS-DISPUTES-VENDOR"))
        self.assertEqual(self.live.get("interfaces", "INT-DISPUTES-SAAS-FEED")["source_system_id"], "SYS-DISPUTES-SAAS")
        self.assertEqual(self.live.get("data_assets", "DA-DISPUTES-VENDOR-FEED")["source_of_truth"], "SYS-DISPUTES-SAAS")
        transported = {(str(r["interface_id"]), str(r["data_asset_id"]))
                       for r in self.live.relation_rows("interface_transports_data_asset")}
        self.assertIn(("INT-DISPUTES-SAAS-FEED", "DA-DISPUTES-VENDOR-FEED"), transported)
        governed = {(str(r["system_id"]), str(r["control_id"])) for r in self.live.relation_rows("system_governed_by_control")}
        self.assertIn(("SYS-DISPUTES-SAAS", "CTL-REGE-ACK"), governed, "the estate's own rows still attach")
        self.assertIn(("SYS-DISPUTES-SAAS", "CTL-TPRM-DD"), governed, "and the shape's attach to the kept name")
        drift = self.drift["PRD-DISPUTES"]
        self.assertEqual(len(drift.renamed), 5)
        self.assertEqual(drift.moves, 1 + 6 + 5, "classification answered, six overrides, five names kept")
        collections = self.drift["PRD-COLLECTIONS-WORKSPACE"]
        self.assertEqual(list(collections.dropped), ["event-publisher"])
        self.assertIsNone(self.live.get("systems", "SYS-COLLECT-EVENTS"))

    def test_a_shape_built_on_no_parts_still_has_a_footprint(self) -> None:
        """`batch-data-product` provides its systems itself. Its footprint is
        those, so the product it was written from can be found by it: in the
        seed, an export in which no product carries a shape, Customer 360 is
        what it was in the repository until it moved."""
        batch = next(a for a in self.shapes if a.archetype_id == "batch-data-product")
        self.assertEqual(part_categories(batch, self.modules),
                         [("pipeline", "Pipeline", True), ("semantic", "Analytics", True)])
        seeded = seeded_model()
        fits = {(c.product_id, c.archetype_id): c
                for c in candidates(seeded, list(seeded.archetypes.values()), self.modules)}
        self.assertIn(("PRD-CUSTOMER-360", "batch-data-product"), fits)
        self.assertEqual(fits[("PRD-CUSTOMER-360", "batch-data-product")].spare, [])
        platform = next(a for a in self.shapes if a.archetype_id == "core-platform-service")
        self.assertEqual(part_categories(platform, self.modules), [("svc", "Platform", True)])
        self.assertIn(("PRD-IDENTITY", "core-platform-service"), fits)

    def test_the_identity_service_moved_onto_the_shape_written_from_it(self) -> None:
        svc = self.live.get("systems", "SYS-IDENTITY-SVC")
        self.assertEqual(svc["archetype_instance"], "PRD-IDENTITY")
        self.assertEqual(svc["cmdb_ci_sys_id"], "18293040506a7b8c")
        self.assertEqual(svc["cloud_account"], "azure-platform-prod")
        self.assertEqual(svc["network_zone"], "Shared-Services")
        self.assertEqual(svc["resilience"], "Multi-AZ")
        # Three products' interfaces point at the id, and still do.
        self.assertEqual(self.live.get("interfaces", "INT-CARDSVC-API-IDENTITY")["target_system_id"], "SYS-IDENTITY-SVC")
        self.assertIsNotNone(self.live.get("tech_services", "TS-IDENTITY-WAF"), "the shape's front door comes with it")
        drift = self.drift["PRD-IDENTITY"]
        self.assertEqual(list(drift.overrides), ["SYS-IDENTITY-SVC"])
        self.assertEqual(list(drift.answered_defaults), ["classification"])
        self.assertEqual(drift.moves, 2)

    def test_customer_360_moved_onto_the_shape_written_from_it(self) -> None:
        pipeline = self.live.get("systems", "SYS-CUST360-PIPELINE")
        self.assertEqual(pipeline["archetype_instance"], "PRD-CUSTOMER-360")
        self.assertEqual(pipeline["data_classification_supported"], "Restricted")
        self.assertEqual(self.live.get("interfaces", "INT-CUST360-INGEST")["integration_style"], "Batch")
        # The planned feed to regulatory reporting is hand-authored still,
        # and points at the id the shape makes.
        feed = self.live.get("interfaces", "INT-CUST360-REGREPORTING")
        self.assertEqual(feed["source_system_id"], "SYS-CUST360-SEMANTIC")
        self.assertIsNone(feed.get("archetype_instance"))
        drift = self.drift["PRD-CUSTOMER-360"]
        self.assertEqual(list(drift.overrides), ["INT-CUST360-INGEST", "INT-CUST360-PIPE-SEMANTIC"])
        self.assertEqual(list(drift.answered_defaults), ["classification"])
        self.assertEqual(drift.moves, 3)

    def test_card_servicing_moved_onto_its_shape_without_a_rename(self) -> None:
        """The first live product moved: the slug makes exactly the ids the
        estate already pointed at, so nothing that named them changed, and
        what the shape's defaults got wrong is overrides."""
        api = self.live.get("systems", "SYS-CARDSVC-API")
        self.assertEqual(api["archetype_instance"], "PRD-CARD-SERVICING")
        self.assertEqual(api["cmdb_ci_sys_id"], "f60718293040506a")
        self.assertEqual(api["service_tier"], "Tier 1")
        self.assertEqual(api["cloud_account"], "azure-cards-prod")
        self.assertEqual(self.live.get("systems", "SYS-CARDSVC-STORE")["name"], "Card Servicing Datastore")
        self.assertEqual(self.live.get("systems", "SYS-CARDSVC-EVENTS")["criticality"], "Medium")
        realized = {(r["system_id"], r["capability_id"]) for r in self.live.relation_rows("system_realizes_capability")}
        self.assertIn(("SYS-CARDSVC-WEB", "CAP-SERV"), realized)
        card = self.drift["PRD-CARD-SERVICING"]
        self.assertEqual(list(card.overrides), ["DA-CARDSVC-OPERATIONAL", "INT-CARDSVC-API-STORE", "SYS-CARDSVC-API",
                                                "SYS-CARDSVC-EVENTS", "SYS-CARDSVC-STORE", "SYS-CARDSVC-WEB"])
        self.assertEqual(list(card.added), [])
        # A Tier 1 product holding Restricted data answers the shape's two
        # defaults against it; the region is the shape's own.
        self.assertEqual(list(card.answered_defaults), ["classification", "criticality"])
        self.assertEqual(card.moves, 8)

    def test_validate_names_the_candidates(self) -> None:
        # In the seed, where no product carries a shape; the repository has
        # none left to name.
        messages = [f.message for f in validate.run(seeded_model()).warnings if f.code == "library.shape_candidate"]
        self.assertTrue(
            any(m.startswith("product PRD-COLLECTIONS-WORKSPACE has the systems of azure-digital-product's") for m in messages),
            messages,
        )
        self.assertTrue(any("(no event-publisher, which is optional)" in m for m in messages), messages)
        self.assertEqual([f.message for f in validate.run(self.live).warnings if f.code == "library.shape_candidate"], [])

    def test_the_page_says_all_three_things(self) -> None:
        page = render_adoption(self.modules, self.shapes, self.live)
        self.assertIn("| Collections Workspace (`PRD-COLLECTIONS-WORKSPACE`) | `azure-digital-product` |", page)
        self.assertIn("| Dispute Management (`PRD-DISPUTES`) | `vendor-saas-service` |", page)
        self.assertIn("`DA-DISPUTES-OUTCOMES`, `INT-DISPUTES-CALLER-GATEWAY`", page, "the kept ids are a column")
        self.assertIn("None.", page.split("## Candidates")[1].split("## No shape fits")[0])
        self.assertIn("| Card Servicing (`PRD-CARD-SERVICING`) | `azure-digital-product` |", page)
        self.assertIn("reach: `private-egress` (not the default)", page)
        self.assertIn("| Customer 360 (`PRD-CUSTOMER-360`) | `batch-data-product` |", page)
        self.assertIn("| Customer Identity Service (`PRD-IDENTITY`) | `core-platform-service` |", page)
        self.assertEqual(page.split("## No shape fits")[1].strip(), "None.",
                         "every shape written from a live product has that product on it")
        self.assertEqual(page, render_adoption(self.modules, self.shapes, self.live))


class TestAProductThatChooses(unittest.TestCase):
    """PRD-IDV is on the Azure vendor shape and chooses in both slots. It is
    the committed product that shows the slots and the binds doing their
    work, so the seeded estate is checked for what it drew."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def _uses(self, system_id):
        return {r["tech_service_id"] for r in self.model.relation_rows("system_uses_tech_service")
                if r["system_id"] == system_id}

    def test_the_private_path_runs_on_azure(self) -> None:
        self.assertEqual(self._uses("SYS-IDV-EGRESS"), {"TS-AZURE-PRIVATELINK", "TS-AZURE-VWAN"})
        self.assertEqual(self._uses("SYS-IDV-GATEWAY"), {"TS-AZURE-AKS", "TS-AZURE-APIM", "TS-AZURE-KEYVAULT"})

    def test_our_side_lands_in_the_subscription_the_product_names(self) -> None:
        """The vendor stays in its tenancy; the gateway, the egress and the
        listener are ours and say which subscription and region."""
        for ours in ("SYS-IDV-GATEWAY", "SYS-IDV-EGRESS", "SYS-IDV-WEBHOOKS"):
            record = self.model.get("systems", ours)
            self.assertEqual((record["cloud_account"], record["region"]), ("azure-risk-prod", "uksouth"), ours)
        vendor = self.model.get("systems", "SYS-IDV-VENDOR")
        self.assertIn(vendor.get("cloud_account"), (None, ""), "the vendor's tenancy is not a subscription of ours")

    def test_the_vendor_calls_back_rather_than_sending_a_file(self) -> None:
        interfaces = set(self.model.entities["interfaces"])
        self.assertIn("INT-IDV-VENDOR-WEBHOOKS", interfaces)
        self.assertIn("INT-IDV-WEBHOOKS-CONSUMER", interfaces)
        self.assertNotIn("INT-IDV-VENDOR-RETURN", interfaces)
        self.assertNotIn("DA-IDV-OUTCOMES", self.model.entities["data_assets"])

    def test_every_new_system_is_delivered_by_the_work_package(self) -> None:
        report = validate.run(self.model)
        unscheduled = [f for f in report.warnings if f.code == "change.unscheduled" and "IDV" in f.message]
        self.assertEqual(unscheduled, [])
        self.assertEqual(report.errors, [])


class TestKindsResolveThemselves(unittest.TestCase):
    """A shape names its provider; a part's kind finds the one landing-zone
    service of that kind there. `bind` is the override, not the requirement."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()

    def _gateway_uses(self, out):
        return {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])
                if r["system_id"] == "SYS-PROBE-GATEWAY"}

    def _expand(self, shape: dict, library=None, **extra):
        return expand(_instance(**extra), parse_archetype(shape), "products", library or self.library)

    def test_a_shape_with_no_bind_resolves_against_its_provider(self) -> None:
        out = self._expand(dict(SHAPE, bind={}))
        # The gateway's platform and front door: a container platform and an
        # API gateway, found on the AWS landing zone with nothing bound.
        self.assertTrue({"TS-AWS-EKS", "TS-AWS-APIGW"} <= self._gateway_uses(out))

    def test_the_same_shape_on_azure_finds_the_azure_services(self) -> None:
        out = self._expand(dict(SHAPE, bind={}, provider="Azure"))
        uses = self._gateway_uses(out)
        self.assertIn("TS-AZURE-AKS", uses)
        self.assertIn("TS-AZURE-APIM", uses)
        self.assertNotIn("TS-AWS-EKS", uses)

    def test_an_explicit_bind_wins_over_the_landing_zone(self) -> None:
        out = self._expand(dict(SHAPE, bind={"api-gateway": "TS-AZURE-APIM"}))
        self.assertIn("TS-AZURE-APIM", self._gateway_uses(out))
        self.assertNotIn("TS-AWS-APIGW", self._gateway_uses(out))

    def test_a_neutral_service_answers_for_any_provider(self) -> None:
        """Entra is the identity provider on every cloud, tagged with no
        provider, and resolves for an AWS shape as it would for an Azure one."""
        found, candidates = resolve_kind("identity-provider", "AWS", self.library[3])
        self.assertEqual(found, "TS-ENTRA-ID")
        self.assertEqual(candidates, ["TS-ENTRA-ID"])

    def test_the_providers_own_service_beats_a_neutral_one(self) -> None:
        zone = {("", "identity-provider"): ["TS-ENTRA-ID"], ("Azure", "identity-provider"): ["TS-AZURE-B2C"]}
        self.assertEqual(resolve_kind("identity-provider", "Azure", zone)[0], "TS-AZURE-B2C")
        self.assertEqual(resolve_kind("identity-provider", "AWS", zone)[0], "TS-ENTRA-ID")

    def test_two_services_of_one_kind_is_refused_by_name(self) -> None:
        crowded = dict(self.library[3])
        crowded[("AWS", "api-gateway")] = ["TS-AWS-APIGW", "TS-AWS-APIGW-LEGACY"]
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(dict(SHAPE, bind={}), library=self.library[:3] + (crowded,))
        message = str(caught.exception)
        self.assertIn("TS-AWS-APIGW and TS-AWS-APIGW-LEGACY", message)
        self.assertIn("bind:", message)

    def test_the_index_lists_only_what_is_tagged_and_typed(self) -> None:
        """A NAT gateway is a private-egress too. It is not tagged, so a part
        asking for the private egress on AWS finds PrivateLink and nothing
        else; a service with no component type cannot answer for any kind."""
        index = landing_zone_index([
            {"tech_service_id": "TS-A", "component_type": "private-egress", "cloud_provider": "AWS",
             "tags": ["landing-zone"]},
            {"tech_service_id": "TS-NAT", "component_type": "private-egress", "cloud_provider": "AWS",
             "tags": ["network-fabric"]},
            {"tech_service_id": "TS-UNTYPED", "cloud_provider": "AWS", "tags": "landing-zone"},
            {"tech_service_id": "TS-SAAS", "component_type": "identity-provider", "cloud_provider": "SaaS",
             "tags": "landing-zone;other"},
        ])
        self.assertEqual(index, {("AWS", "private-egress"): ["TS-A"], ("", "identity-provider"): ["TS-SAAS"]})
        self.assertEqual(resolve_kind("private-egress", "AWS", self.library[3]), ("TS-AWS-PRIVATELINK", ["TS-AWS-PRIVATELINK"]))

    def test_no_shipped_shape_binds_a_kind_the_landing_zone_resolves(self) -> None:
        """The shapes stopped saying what the tag already says. What is left
        under `bind` is an override -- Key Vault standing for key management
        on the Azure shape -- or nothing."""
        for shape in load_archetypes(REPO).values():
            for kind, service in shape.bind.items():
                with self.subTest(shape=shape.archetype_id, kind=kind):
                    found, _candidates = resolve_kind(kind, shape.provider, self.library[3])
                    self.assertNotEqual(found, service, "%s binds what would resolve anyway" % kind)

    def test_validate_names_an_ambiguous_kind(self) -> None:
        model = seeded_model()
        model.entities["tech_services"]["TS-AWS-APIGW-LEGACY"] = dict(
            model.entities["tech_services"]["TS-AWS-APIGW"],
            tech_service_id="TS-AWS-APIGW-LEGACY", name="The old gateway")
        model.archetypes["probe-crowded"] = parse_archetype(dict(SHAPE, bind={}))
        errors = [f for f in validate.run(model).errors if f.code == "library.ambiguous_kind"]
        self.assertTrue(errors)
        self.assertIn("TS-AWS-APIGW-LEGACY", errors[0].message)


class TestRenderedParts(unittest.TestCase):
    """The parts and the shapes are cataloged beside the diagrams, with the
    columns nobody keeps by hand: where a part is used, which products are
    on a shape."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.modules = load_modules(REPO)
        cls.shapes = list(load_archetypes(REPO).values())
        cls.model = seeded_model()
        cls.parts = render_modules(cls.modules, cls.shapes, cls.model)
        cls.catalog = render_shapes(cls.shapes, cls.modules, cls.model)
        cls.zones = render_landing_zones(cls.modules, cls.shapes, cls.model)

    def test_every_provider_a_shape_lands_on_has_a_landing_zone_section(self) -> None:
        self.assertIn("| [AWS](#aws) | `aws-product-onboarding`, `saas-onboarding` |", self.zones)
        self.assertIn('<a id="azure"></a>', self.zones)
        self.assertIn("## Shared", self.zones)
        self.assertNotIn("On-prem", self.zones)

    def test_a_landing_zone_lists_what_it_has_and_what_is_asked_of_it_that_it_lacks(self) -> None:
        self.assertIn("(`TS-AWS-APIGW`) | `api-outbound` (front_door)", self.zones)
        self.assertIn(
            "| `identity-provider` | Microsoft Entra ID (`TS-ENTRA-ID`) | `admin-console` (idp), "
            "`identity-hub` (idp), `sso-federation` (idp) |",
            self.zones,
        )
        self.assertIn("| `foundation-model-service` | Amazon Bedrock (`TS-AWS-BEDROCK`) | `ml-inference-service` (models) |",
                      self.zones)
        self.assertIn("(`TS-NET-VPN`) — ambiguous | — |", self.zones)
        self.assertIn(
            "| `event-stream` | Azure Event Hubs (`TS-AZURE-EVENTHUBS`) | `async-worker` (stream) |",
            self.zones,
        )
        # A kind with no service is the row to read; untagging Event Hubs makes one.
        model = seeded_model()
        record = next(s for s in model.all_of("tech_services") if s["tech_service_id"] == "TS-AZURE-EVENTHUBS")
        record["tags"] = [t for t in model.list_of(record, "tags") if t != "landing-zone"]
        self.assertIn(
            "| `event-stream` | **none** | `async-worker` (stream) |",
            render_landing_zones(self.modules, self.shapes, model),
        )
        self.assertIn(
            "| `kms` | Azure Key Vault (`TS-AZURE-KEYVAULT`) — a `secrets-manager` that answers "
            "for it | `byok-encryption` (kms) |",
            self.zones,
        )

    def test_every_part_is_in_the_catalog(self) -> None:
        for module in self.modules.values():
            with self.subTest(part=module.module_id):
                self.assertIn('<a id="%s"></a>' % module.module_id, self.parts)
                self.assertIn("## %s" % module.name, self.parts)

    def test_a_kit_says_what_it_is_made_of(self) -> None:
        self.assertIn("kit of `vendor-tenancy`, `api-outbound`, `secrets-management`", self.parts)

    def test_a_part_says_where_it_is_used_and_how(self) -> None:
        self.assertIn("SaaS onboarding (slot reach)", self.parts)
        self.assertIn("kit vendor-baseline", self.parts)
        self.assertIn("Nothing composes it", self.parts)

    def test_a_part_says_what_it_needs_and_what_kinds_it_names(self) -> None:
        self.assertIn("**Needs from the shape.** `product_name`, `slug`, `vendor`.", self.parts)
        self.assertIn("`front_door` is of kind `api-gateway`", self.parts)

    def test_every_shape_is_in_the_catalog_with_its_slots(self) -> None:
        for shape in self.shapes:
            with self.subTest(shape=shape.archetype_id):
                self.assertIn('<a id="%s"></a>' % shape.archetype_id, self.catalog)
        self.assertIn("**Slot `reach`.** `private-egress` (default), `public-call`.", self.catalog)
        self.assertIn(", or none", self.catalog)

    def test_the_products_on_a_shape_are_read_off_the_model(self) -> None:
        """Against the repository's own model every shape has a product now,
        the two written from live products included. The seed is an export
        in which a product is plain rows with no `archetype`, so no shape has
        products there, and a shape with none says so rather than showing
        nothing."""
        from terrane import model as model_module

        live = model_module.load(REPO)
        catalog = render_shapes(list(live.archetypes.values()), self.modules, live)
        self.assertIn("Identity Document Verification (`PRD-IDV`)", catalog)
        self.assertIn("NICE Actimize Screening (`PRD-SCREENING`)", catalog)
        self.assertIn("Customer 360 (`PRD-CUSTOMER-360`)", catalog)
        self.assertIn("Customer Identity Service (`PRD-IDENTITY`)", catalog)
        self.assertNotIn("**Products.** None yet.", catalog)
        seeded = seeded_model()
        self.assertIn("**Products.** None yet.", render_shapes(list(seeded.archetypes.values()), self.modules, seeded))

    def test_a_shape_lists_its_blocks_binds_and_its_overrides_and_nothing_resolvable(self) -> None:
        """What a shape's blocks bind is listed, and what the landing zone
        answers for each -- Key Vault standing for key management on the Azure
        product shape. No shipped shape binds a service by id."""
        self.assertIn("`kms` → the landing zone's (`TS-AZURE-KEYVAULT`)", self.catalog)
        self.assertNotIn("`api-gateway` → `TS-AWS-APIGW`", self.catalog)
        self.assertNotIn("`secrets-manager` →", self.catalog)

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(self.parts, render_modules(self.modules, self.shapes, self.model))
        self.assertEqual(self.catalog, render_shapes(self.shapes, self.modules, self.model))
        self.assertEqual(self.zones, render_landing_zones(self.modules, self.shapes, self.model))


class TestShippedShapes(unittest.TestCase):
    """The four composed shapes expand to the ids the seeded model relies on."""

    SAMPLES = {
        "saas-onboarding": {"slug": "acme", "product_name": "Acme", "vendor": "Acme", "owner_org": "ORG-TECH",
                            "domain": "Probing", "account": "prod-acme", "caller_system": "SYS-AUTH-SWITCH"},
        "vendor-saas-service": {"slug": "acme", "product_name": "Acme", "vendor": "Acme", "owner_org": "ORG-TECH",
                                "domain": "Probing", "upstream_system": "SYS-CRM", "account": "azure-probe-prod"},
        "aws-product-onboarding": {"slug": "acme", "product_name": "Acme", "owner_org": "ORG-TECH",
                                   "domain": "Probing", "account": "prod-acme"},
        "azure-digital-product": {"slug": "acme", "product_name": "Acme", "owner_org": "ORG-TECH",
                                  "domain": "Probing", "account": "azure-probe-prod"},
    }
    EXPECT = {
        "saas-onboarding": ["SYS-ACME-EGRESS", "SYS-ACME-FEDERATION", "SYS-ACME-GATEWAY", "SYS-ACME-VENDOR"],
        "vendor-saas-service": ["SYS-ACME-GATEWAY", "SYS-ACME-VENDOR"],
        "aws-product-onboarding": ["SYS-ACME-ALB", "SYS-ACME-API", "SYS-ACME-BUCKET", "SYS-ACME-DB",
                                   "SYS-ACME-EDGE", "SYS-ACME-WEB", "SYS-ACME-WORKER"],
        "azure-digital-product": ["SYS-ACME-API", "SYS-ACME-EVENTS", "SYS-ACME-STORE", "SYS-ACME-WEB"],
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        cls.shapes = load_archetypes(REPO)

    def _expand(self, archetype_id: str, **extra):
        shape = self.shapes[archetype_id]
        instance = {"product_id": "PRD-ACME", "name": "Acme", "status": "Planned",
                    "owner_org_id": "ORG-TECH", "parameters": dict(self.SAMPLES[archetype_id])}
        instance.update(extra)
        return expand(instance, shape, "products", self.library)

    def test_the_defaults_are_the_shape_as_it_was_before_it_had_slots(self) -> None:
        """The screening product says nothing under `choose` and gets what it
        got when the private path and the return feed were listed parts."""
        out = self._expand("saas-onboarding")
        self.assertEqual(out.choices, {"reach": "private-egress", "return": "sftp-return-feed"})
        self.assertEqual(out.modules_applied[:3], ["vendor-tenancy", "api-outbound", "secrets-management"])

    def test_choosing_the_public_path_is_one_line_not_a_second_shape(self) -> None:
        out = self._expand("saas-onboarding", choose={"reach": "public-call"})
        self.assertEqual(_ids(out, "systems"), ["SYS-ACME-FEDERATION", "SYS-ACME-GATEWAY", "SYS-ACME-VENDOR"])
        self.assertIn("INT-ACME-GATEWAY-VENDOR", _ids(out, "interfaces"))

    def test_a_vendor_that_sends_nothing_back(self) -> None:
        out = self._expand("saas-onboarding", choose={"return": "none"})
        self.assertEqual(_ids(out, "data_assets"), [])
        self.assertEqual(out.choices["return"], "")

    def test_the_two_vendor_shapes_share_the_baseline_and_differ_in_the_binding(self) -> None:
        """The claim the kit makes: one part, two landing zones, and the
        difference is the shape's `bind`."""
        aws = self._expand("saas-onboarding")
        azure = self._expand("vendor-saas-service")
        for out in (aws, azure):
            self.assertEqual(out.modules_applied[:3], ["vendor-tenancy", "api-outbound", "secrets-management"])

        def gateway_uses(out):
            return {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])
                    if r["system_id"] == "SYS-ACME-GATEWAY"}

        self.assertIn("TS-AWS-SECRETS", gateway_uses(aws))
        self.assertIn("TS-AZURE-KEYVAULT", gateway_uses(azure))
        self.assertNotIn("TS-AWS-SECRETS", gateway_uses(azure))

    def test_the_private_path_on_the_azure_shape_binds_azure_services(self) -> None:
        """The reason the round exists. Before it, choosing the private path
        on the Azure vendor shape bound PrivateLink and the AWS transit
        gateway, because the part carried them as defaults."""

        def egress_uses(out):
            return {r["tech_service_id"] for r in out.relations.get("system_uses_tech_service", [])
                    if r["system_id"] == "SYS-ACME-EGRESS"}

        azure = self._expand("vendor-saas-service", choose={"reach": "private-egress"})
        self.assertEqual(egress_uses(azure), {"TS-AZURE-PRIVATELINK", "TS-AZURE-VWAN"})
        aws = self._expand("saas-onboarding")
        self.assertEqual(egress_uses(aws), {"TS-AWS-PRIVATELINK", "TS-AWS-TGW"})

    def test_every_composed_shape_expands_to_its_systems(self) -> None:
        for archetype_id, expected in self.EXPECT.items():
            self.assertTrue(self.shapes[archetype_id].modules, archetype_id)
            self.assertEqual(_ids(self._expand(archetype_id), "systems"), expected, archetype_id)

    def test_the_same_parts_bind_differently_per_cloud(self) -> None:
        aws = self._expand("aws-product-onboarding")
        azure = self._expand("azure-digital-product")
        self.assertEqual(aws.modules_applied[0], "api-service")
        self.assertEqual(azure.modules_applied[0], "api-service")
        aws_uses = {r["tech_service_id"] for r in aws.relations["system_uses_tech_service"]
                    if r["system_id"] == "SYS-ACME-API"}
        azure_uses = {r["tech_service_id"] for r in azure.relations["system_uses_tech_service"]
                      if r["system_id"] == "SYS-ACME-API"}
        self.assertIn("TS-AWS-EKS", aws_uses)
        self.assertNotIn("TS-AWS-EKS", azure_uses)
        self.assertIn("TS-AZURE-AKS", azure_uses)
        self.assertNotIn("TS-AZURE-AKS", aws_uses)

    def test_a_shape_relation_across_two_parts_goes_when_either_is_dropped(self) -> None:
        shape = self.shapes["aws-product-onboarding"]
        instance = {"product_id": "PRD-ACME", "name": "Acme", "status": "Planned",
                    "owner_org_id": "ORG-TECH", "without": ["async-worker"],
                    "parameters": dict(self.SAMPLES["aws-product-onboarding"])}
        out = expand(instance, shape, "products", self.library)
        self.assertNotIn("SYS-ACME-WORKER", _ids(out, "systems"))
        readers = {r["system_id"] for r in out.relations.get("system_reads_writes", [])}
        self.assertNotIn("SYS-ACME-WORKER", readers)

    def test_excluding_the_store_takes_what_pointed_at_its_data(self) -> None:
        """Found re-running the walkthrough on 2026-10-22. Excluding the
        store dropped the data asset mastered in it, but the API's
        read-write row to that asset stayed, and `terrane validate` failed
        on a dangling reference: the cascade stopped one step out."""
        out = self._expand("azure-digital-product", exclude=["SYS-ACME-STORE"])
        self.assertEqual(_ids(out, "systems"), ["SYS-ACME-API", "SYS-ACME-EVENTS", "SYS-ACME-WEB"])
        self.assertNotIn("DA-ACME-OPERATIONAL", _ids(out, "data_assets"))
        self.assertIn(("DA-ACME-OPERATIONAL", "SYS-ACME-STORE"), out.dropped_dependents)
        for relation_name, rows in out.relations.items():
            for row in rows:
                self.assertNotIn("DA-ACME-OPERATIONAL", row.values(), relation_name)
        # And as the loader takes it: a product file in the seeded estate,
        # validated, and every entity that went said so.
        product = (
            "product_id: PRD-ACME\nname: Acme\nstatus: Planned\nowner_org_id: ORG-DIGITAL\n"
            "archetype: azure-digital-product\nparameters:\n  slug: acme\n  product_name: Acme\n"
            "  owner_org: ORG-DIGITAL\n  domain: Servicing\n  account: azure-cards-prod\n"
            "exclude:\n  - SYS-ACME-STORE\n"
        )
        with Sandbox(seed=True) as root:
            (root / "10_MODEL" / "products" / "PRD-ACME.yaml").write_text(product, encoding="utf-8")
            model = model_module.load(root)
            report = validate.run(model, load_views(root / "30_VIEWS"))
        self.assertEqual([f.message for f in report.errors], [])
        self.assertIsNone(model.get("data_assets", "DA-ACME-OPERATIONAL"))
        self.assertIn(
            "PRD-ACME: DA-ACME-OPERATIONAL dropped because it referenced excluded SYS-ACME-STORE",
            model.warnings,
        )
        self.assertIn(
            "PRD-ACME: INT-ACME-API-STORE dropped because it referenced excluded SYS-ACME-STORE",
            model.warnings,
        )


class TestSeededEstate(unittest.TestCase):
    """The screening onboarding in the example is composed, and clean."""

    def test_the_seeded_model_validates(self) -> None:
        model = seeded_model()
        report = validate.run(model, load_views(seeded_root() / "30_VIEWS"))
        self.assertEqual([f for f in report.findings if f.severity == "error"], [])

    def test_the_screening_gateway_knows_its_part(self) -> None:
        model = seeded_model()
        self.assertEqual(model.entities["systems"]["SYS-SCREENING-GATEWAY"].get("module"), "api-outbound")
        self.assertIn("INT-SCREENING-VENDOR-AUDIT", model.entities["interfaces"])

    def test_third_party_controls_are_recorded_once(self) -> None:
        model = seeded_model()
        rows = [r for r in model.relations["system_governed_by_control"]
                if r["system_id"] == "SYS-SCREENING-VENDOR" and r["control_id"] == "CTL-TPRM-DD"]
        self.assertEqual(len(rows), 1)


class TestNewFormEndpoints(unittest.TestCase):
    """The New form chooses parts; what it chooses reaches the instance file."""

    PARAMS = {"slug": "probe", "product_name": "Probe", "vendor": "Acme", "owner_org": "ORG-PRODUCT",
              "domain": "Probing", "account": "prod-probe", "caller_system": "SYS-AUTH-SWITCH"}

    def _server(self, root: Path):
        sys.path.insert(0, str(root / "50_ENGINE"))
        sys.path.insert(0, str(REPO / "80_APP" / "app"))
        import importlib

        import server as server_module

        importlib.reload(server_module)
        server_module.REPO_ROOT = root
        importer.import_csv(root, EXAMPLE_CSV, model_module.load(root))
        return server_module

    def test_the_overview_lists_the_parts_and_what_each_still_asks(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            shape = next(a for a in server.api_overview(None, None)["archetypes"]
                         if a["id"] == "saas-onboarding")
            parts = {m["alias"]: m for m in shape["modules"]}
            # The kit is a heading; its three members are switches of their own.
            self.assertTrue(parts["vendor-baseline"]["kit"])
            self.assertEqual(parts["vendor-baseline"]["members"],
                             ["vendor-tenancy", "api-outbound", "secrets-management"])
            self.assertEqual([m["alias"] for m in shape["modules"] if not m["kit"]],
                             ["vendor-tenancy", "api-outbound", "secrets-management",
                              "sso-federation", "audit-forwarding", "vendor-monitoring"])
            self.assertEqual(parts["vendor-tenancy"]["in_kit"], "vendor-baseline")
            self.assertFalse(parts["vendor-tenancy"]["optional"])
            self.assertTrue(parts["secrets-management"]["optional"])
            # `vendor` reaches the tenancy through the kit; the part asks nothing more.
            self.assertNotIn("vendor", [p["name"] for p in parts["vendor-tenancy"]["parameters"]])
            # The gateway's platform is a kind now. The part says "a container
            # platform"; the shape binds it; the form shows what it gets.
            platform = next(p for p in parts["api-outbound"]["parameters"] if p["name"] == "platform")
            self.assertEqual(platform["component"], "container-platform")
            self.assertEqual(platform["bound"], "TS-AWS-EKS")
            self.assertNotIn("platform", [p["name"] for p in parts["vendor-baseline"]["parameters"]])
            # The slots, with their options, their defaults, and what each
            # option would ask for once chosen.
            slots = {s["name"]: s for s in shape["slots"]}
            self.assertEqual([o["id"] for o in slots["reach"]["options"]], ["private-egress", "public-call"])
            self.assertEqual(slots["reach"]["default"], "private-egress")
            self.assertFalse(slots["reach"]["optional"])
            self.assertTrue(slots["return"]["optional"])
            feed = next(o for o in slots["return"]["options"] if o["id"] == "sftp-return-feed")
            self.assertIn("ingest_system", [p["name"] for p in feed["parameters"]])

    def test_instantiating_writes_the_chosen_parts(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            result = server.api_instantiate(None, {
                "archetype": "saas-onboarding", "id": "PRD-PROBE",
                "values": {"name": "Probe", "status": "Planned", "owner_org_id": "ORG-PRODUCT"},
                "parameters": dict(self.PARAMS),
                "without": ["vendor-monitoring"],
                "choose": {"return": "none"},
                "moduleParams": {
                    "audit-forwarding": {"siem_system": "SYS-SIEM"},
                    # Given for an option the product did not choose: not
                    # written, because it would be a lie about what the
                    # product has.
                    "sftp-return-feed": {"ingest_system": "SYS-CRM"},
                },
            })
            self.assertEqual(result.get("errors", []), [])
            text = (root / "10_MODEL" / "products" / "PRD-PROBE.yaml").read_text(encoding="utf-8-sig")
            self.assertIn("without: [vendor-monitoring]", text)
            self.assertIn("choose:\n  return: none", text)
            self.assertIn("modules:\n  - module: audit-forwarding\n    with:\n      siem_system: SYS-SIEM", text)
            self.assertNotIn("ingest_system", text)

            reloaded = model_module.load(root)
            self.assertIn("SYS-PROBE-VENDOR", reloaded.entities["systems"])
            self.assertIn("INT-PROBE-VENDOR-AUDIT", reloaded.entities["interfaces"])
            self.assertNotIn("DA-PROBE-OUTCOMES", reloaded.entities["data_assets"])
            self.assertNotIn("INT-PROBE-VENDOR-RETURN", reloaded.entities["interfaces"])

    def test_the_library_lists_the_parts_and_who_uses_them(self) -> None:
        with Sandbox() as root:
            server = self._server(root)
            parts = {m["id"]: m for m in server.api_library(None, None)["modules"]}
            self.assertIn("api-outbound", parts)
            self.assertIn("SaaS onboarding", parts["api-outbound"]["inShapes"])
            self.assertIn("Vendor SaaS service", parts["api-outbound"]["inShapes"])
            # A slot option is a use, and says which slot; a kit member says
            # which kit; a build type that lists a part is a user of it too,
            # so a part only a type offers is on a menu rather than forgotten.
            self.assertEqual(parts["webhook-inbound"]["inShapes"],
                             ["SaaS onboarding (slot return)", "Vendor SaaS service (slot return)",
                              "Vendor SaaS service on Google Cloud (slot return)",
                              "type Bought SaaS capability"])
            self.assertIn("kit vendor-baseline", parts["vendor-tenancy"]["inShapes"])
            self.assertEqual(parts["byok-encryption"]["inShapes"], ["type Bought SaaS capability"])
            self.assertTrue(parts["vendor-baseline"]["kit"])


class TestHubAndSpoke(unittest.TestCase):
    """A template with `each` is produced once per spoke the instance names."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = _library()
        # The hubs name kinds the vendor probe does not bind: a message queue
        # for the event hub. The shape says which service is that kind here.
        cls.shape = parse_archetype(dict(
            SHAPE,
            bind=dict(SHAPE["bind"], **{"message-queue": "TS-AZURE-SERVICEBUS"}),
            modules=[{"module": "vendor-tenancy", "with": {"vendor": "{vendor}"}}],
        ))

    def _expand(self, modules):
        return expand(_instance(modules=modules), self.shape, "products", self.library)

    def test_one_interface_per_spoke(self) -> None:
        out = self._expand([{"module": "integration-hub",
                             "with": {"spokes": ["SYS-CORE-LEDGER", "SYS-CRM", "SYS-STATEMENTS"]}}])
        self.assertIn("SYS-PROBE-HUB", _ids(out, "systems"))
        self.assertEqual(
            [i for i in _ids(out, "interfaces") if i.endswith("-HUB")],
            ["INT-PROBE-CORE-LEDGER-HUB", "INT-PROBE-CRM-HUB", "INT-PROBE-STATEMENTS-HUB"],
        )
        link = next(i for i in out.entities["interfaces"] if i["interface_id"] == "INT-PROBE-CRM-HUB")
        self.assertEqual(link["source_system_id"], "SYS-CRM")
        self.assertEqual(link["target_system_id"], "SYS-PROBE-HUB")
        self.assertEqual(link["module"], "integration-hub")
        hub = next(s for s in out.entities["systems"] if s["system_id"] == "SYS-PROBE-HUB")
        self.assertIn("hub", hub["tags"])

    def test_an_empty_list_produces_nothing(self) -> None:
        out = self._expand([{"module": "event-hub", "with": {"spokes": ["SYS-CRM"]}}])
        ids = _ids(out, "interfaces")
        self.assertIn("INT-PROBE-CRM-BUS", ids)
        self.assertFalse([i for i in ids if i.startswith("INT-PROBE-BUS-")], "no subscribers, no links")

    def test_relations_repeat_too(self) -> None:
        out = self._expand([{"module": "network-hub",
                             "with": {"spokes": ["TS-NET-VPC-LENDING", "TS-NET-VPC-SHARED"]}}])
        self.assertIn("TS-PROBE-TRANSIT", _ids(out, "tech_services"))
        rows = {(r["from_tech_service_id"], r["to_tech_service_id"])
                for r in out.relations.get("tech_service_connects_to", [])}
        self.assertIn(("TS-NET-VPC-LENDING", "TS-PROBE-TRANSIT"), rows)
        self.assertIn(("TS-NET-VPC-SHARED", "TS-PROBE-TRANSIT"), rows)

    def test_the_spokes_are_required(self) -> None:
        with self.assertRaises(ArchetypeError) as caught:
            self._expand(["integration-hub"])
        self.assertIn("spokes", str(caught.exception))

    def test_the_stem_filter(self) -> None:
        from terrane.archetype import substitute
        self.assertEqual(substitute("{x|stem}", {"x": "SYS-CORE-LEDGER"}), "CORE-LEDGER")
        self.assertEqual(substitute("{x|stem|lower}", {"x": "SYS-CRM"}), "crm")
        self.assertEqual(substitute("{x|stem}", {"x": "PLAIN"}), "PLAIN")

    def test_the_lending_product_has_its_hub(self) -> None:
        model = model_module.load(REPO)
        self.assertIn("SYS-LENDING-HUB", model.entities["systems"])
        spokes = sorted(i["source_system_id"] for i in model.entities["interfaces"].values()
                        if i.get("target_system_id") == "SYS-LENDING-HUB")
        self.assertEqual(spokes, ["SYS-CORE-LEDGER", "SYS-CREDIT-BUREAU", "SYS-CRM"])


if __name__ == "__main__":
    unittest.main()
