"""What an estate says about the library it builds on, in `model.yaml`.

The shipped library names no record of any estate. It used to name the
sample's: the vendor parts gave the private egress to `ORG-TECH` and sent the
audit trail to `SYS-SIEM`, the shapes bound the sample's Key Vault by id, and
every pattern named an owner and the controls it met in the card issuer's
register. A second estate built on that library had to hold eighteen records
under the sample's ids and heard fifty-one warnings about the rest
(`90_EXAMPLE/thurman-health`).

What the library needs of an estate it now asks for, and the estate answers
in two places in its `model.yaml`:

`answers`
    A parameter of a shape or a part marked `estate: true` -- who owns the
    shared network, where a vendor's audit trail goes, which controls govern
    a vendor tenancy -- takes the value under its name here, ahead of its
    default, wherever a product does not say otherwise. A technology service
    is not answered here: a part or a shape names its kind, and the landing
    zone answers that (`archetype.resolve_kind`).

`patterns`
    Per pattern id: the org unit that owns the pattern here, the decision
    record that approved it, and which controls in the register it is
    designed to meet. The pattern says what it is for and what it costs, and
    that travels; these three are one organization's, so they live with its
    model. Not on the control records, which in the sample are imported and
    rewritten whole by the next import.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

ANSWERS_KEY = "answers"
PATTERNS_KEY = "patterns"

#: The fields of a pattern that are the adopting organization's rather than
#: the method's. A pattern in an organization's own library may still carry
#: them, since that library is the organization's; a shipped one does not
#: (`test_patterns.py`), and `patterns` in `model.yaml` wins where both say.
ADOPTED_FIELDS = ("owner_org_id", "decision_ref", "satisfies")


class EstateError(ValueError):
    """`answers` or `patterns` in `model.yaml` is not the shape it should be."""


def _listed(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def estate_answers(config: Mapping[str, Any]) -> Dict[str, Any]:
    """The estate's answers, by parameter name."""
    raw = (config or {}).get(ANSWERS_KEY) or {}
    if not isinstance(raw, dict):
        raise EstateError(
            "`%s` in model.yaml maps a parameter name to the estate's answer, "
            "as `platform_org: ORG-...`" % ANSWERS_KEY
        )
    return {str(name): value for name, value in raw.items()}


def pattern_adoption(config: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Per pattern id, what the estate says of it: owner, decision, controls.

    Refused rather than half read: a field this does not know is most likely
    a misspelling of one it does, and a pattern quietly left unowned is the
    kind of gap the warnings exist to find.
    """
    raw = (config or {}).get(PATTERNS_KEY) or {}
    if not isinstance(raw, dict):
        raise EstateError(
            "`%s` in model.yaml maps a pattern id to who owns it here and what it meets"
            % PATTERNS_KEY
        )
    out: Dict[str, Dict[str, Any]] = {}
    for pattern_id, said in raw.items():
        if not isinstance(said, dict):
            raise EstateError(
                "`%s.%s` in model.yaml is a mapping of %s"
                % (PATTERNS_KEY, pattern_id, ", ".join(ADOPTED_FIELDS))
            )
        unknown = sorted(str(k) for k in said if k not in ADOPTED_FIELDS)
        if unknown:
            raise EstateError(
                "`%s.%s` in model.yaml says %s; a pattern's own estate says only %s"
                % (PATTERNS_KEY, pattern_id, ", ".join(unknown), ", ".join(ADOPTED_FIELDS))
            )
        entry: Dict[str, Any] = {}
        if "owner_org_id" in said:
            entry["owner_org_id"] = str(said["owner_org_id"] or "")
        if "decision_ref" in said:
            entry["decision_ref"] = str(said["decision_ref"] or "")
        if "satisfies" in said:
            entry["satisfies"] = _listed(said["satisfies"])
        out[str(pattern_id)] = entry
    return out


def adopted_patterns(patterns: Mapping[str, Any], config: Mapping[str, Any]) -> Dict[str, Any]:
    """The library's patterns, each with what this estate says of it.

    Everything that read `pattern.owner_org_id` or `pattern.satisfies` -- the
    gate, the catalog, the app's cards -- reads it through this, so none of
    them has to know where the answer was written.
    """
    adoption = pattern_adoption(config)
    out: Dict[str, Any] = {}
    for pattern_id, pattern in patterns.items():
        said = adoption.get(pattern_id)
        out[pattern_id] = pattern._replace(**said) if said else pattern
    return out
