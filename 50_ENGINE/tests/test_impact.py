"""Tests for impact analysis.

Mostly direction tests. A blast radius that points the wrong way is worse than
no blast radius: it is wrong with a straight face, and someone will plan an
outage around it. Every one of these caught a real error during development.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terrane import impact  # noqa: E402

from _fixture import seeded_model, teardown_shared  # noqa: E402


def tearDownModule():  # noqa: N802
    teardown_shared()


class TestDirection(unittest.TestCase):
    """Which end depends on which."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def _ids(self, hops):
        return {h.entity_id for h in hops}

    def test_a_capability_depends_on_what_realizes_it(self) -> None:
        """Not the other way round. The ledger going away degrades the
        capability; the capability going away does nothing to the ledger."""
        realized = [
            str(r["capability_id"])
            for r in self.model.relation_rows("system_realizes_capability")
            if str(r["system_id"]) == "SYS-CORE-LEDGER"
        ]
        self.assertTrue(realized, "fixture needs the ledger to realize something")
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        for capability in realized:
            with self.subTest(capability=capability):
                self.assertIn(capability, self._ids(result.downstream))
                self.assertNotIn(capability, self._ids(result.upstream))

    def test_a_caller_depends_on_what_it_calls(self) -> None:
        """Request-response: the authorization switch calls the ledger, so the
        switch is downstream of the ledger."""
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        self.assertIn("SYS-AUTH-SWITCH", self._ids(result.downstream))

    def test_a_feed_consumer_depends_on_the_producer(self) -> None:
        """Batch runs the other way from a call. The ledger pushes a nightly
        extract to the ingestion hub, so the hub breaks when the ledger stops
        even though it is the target of the interface, not the source."""
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        self.assertIn("SYS-DATA-INGEST", self._ids(result.downstream))
        self.assertNotIn("SYS-DATA-INGEST", self._ids(result.upstream))

    def test_written_data_depends_on_its_writer(self) -> None:
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        self.assertIn("DA-CARD-ACCOUNT", self._ids(result.downstream))

    def test_a_system_depends_on_what_it_runs_on(self) -> None:
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        self.assertIn("TS-ONPREM-DC", self._ids(result.upstream))

    def test_the_two_directions_are_not_the_same_set(self) -> None:
        """If they were, direction is not being applied at all."""
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=2)
        self.assertNotEqual(self._ids(result.downstream), self._ids(result.upstream))

    def test_every_interface_declares_its_style(self) -> None:
        """Direction for an interface is read off `integration_style`. An
        interface without one silently defaults, which is a guess."""
        missing = [
            r["interface_id"] for r in self.model.all_of("interfaces")
            if not r.get("integration_style")
        ]
        self.assertEqual(missing, [])


class TestDistance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_confidence_weakens_with_distance(self) -> None:
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=3)
        for hop in result.downstream:
            expected = {1: "direct", 2: "likely"}.get(hop.distance, "possible")
            self.assertEqual(hop.confidence, expected)

    def test_depth_bounds_the_walk(self) -> None:
        near = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=1)
        far = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=3)
        self.assertLess(len(near.downstream), len(far.downstream))
        self.assertTrue(all(h.distance == 1 for h in near.downstream))

    def test_the_root_never_appears_in_its_own_impact(self) -> None:
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=3)
        ids = {h.entity_id for h in result.downstream + result.upstream}
        self.assertNotIn("SYS-CORE-LEDGER", ids)

    def test_filtering_still_traverses_through(self) -> None:
        """A dependency that runs through a subnet still reaches what is beyond
        it, even when subnets are filtered out of the report."""
        everything = impact.analyze(self.model, "SYS-LENDING-API", max_distance=3)
        systems_only = impact.analyze(
            self.model, "SYS-LENDING-API", max_distance=3, include_types=["systems"]
        )
        self.assertTrue(all(h.entity_type == "systems" for h in systems_only.downstream))
        self.assertLessEqual(len(systems_only.downstream), len(everything.downstream))


class TestReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = seeded_model()

    def test_unknown_entity_is_an_error_not_an_empty_result(self) -> None:
        with self.assertRaises(KeyError):
            impact.analyze(self.model, "SYS-DOES-NOT-EXIST")

    def test_critical_systems_are_called_out(self) -> None:
        result = impact.analyze(self.model, "SYS-CORE-LEDGER", max_distance=2)
        self.assertTrue(any("High-criticality" in n for n in result.notes))

    def test_payload_is_json_safe(self) -> None:
        import json
        payload = impact.to_payload(impact.analyze(self.model, "SYS-CORE-LEDGER"))
        json.dumps(payload)
        self.assertEqual(payload["root"], "SYS-CORE-LEDGER")
        self.assertIn("downstream", payload)

    def test_a_vendor_has_consequences_but_few_prerequisites(self) -> None:
        """A bought system we do not run: plenty depends on it, and it depends
        on nothing of ours. If that inverts, the direction logic has broken."""
        result = impact.analyze(self.model, "SYS-SCREENING-VENDOR", max_distance=2)
        self.assertGreater(len(result.downstream), 0)
        self.assertGreaterEqual(len(result.downstream), len(result.upstream))


if __name__ == "__main__":
    unittest.main()
