"""Connection kinds: the ways two systems are connected here.

`24_CONNECTIONS/` names the recurring shapes of the estate's interfaces -- an
integration style, the protocols that carry it, the authentication it uses --
and the pattern each is built with. An interface is of a kind when its style
is the kind's and its protocol is one of the kind's, which is read off the
interface's own fields: nothing records the kind, so the catalog describes the
estate as it is, and an interface made by hand is counted the same as one made
from a kind. Two kinds may not share a style and a protocol, so an interface is
of one kind at most.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple

from .library import LibraryError, load_layer
from .schema import INTEGRATION_STYLES
from .shipped import shipped_root

#: The estate a read is for, while one is under way (`reading_for`): a
#: drawing adopted into an estate with connection kinds of its own is read
#: with those kinds, after the shipped ones.
_READING_FOR: ContextVar[Optional[Path]] = ContextVar("aac_reading_for", default=None)


@contextmanager
def reading_for(root) -> Iterator[None]:
    """While the block runs, the readers go by the connection kinds of the
    estate at `root` (the shipped ones alone when `root` is None)."""
    token = _READING_FOR.set(Path(root) if root is not None else None)
    try:
        yield
    finally:
        _READING_FOR.reset(token)


def kinds_for_reading() -> Dict[str, "ConnectionKind"]:
    """The connection kinds a reader goes by: the estate's own after the
    shipped ones when the read is for an estate, the shipped ones alone
    otherwise, and none when the library cannot be read, since a drawing
    is not the place to say what is wrong with the library."""
    root = _READING_FOR.get()
    try:
        return load_connections(root if root is not None else shipped_root())
    except LibraryError:
        return {}

CONNECTIONS_DIR = "24_CONNECTIONS"


class ConnectionKind(NamedTuple):
    connection_id: str
    name: str
    description: str
    integration_style: str
    protocols: Tuple[str, ...]
    auth_methods: Tuple[str, ...]
    frequency: str
    direction: str
    patterns: Tuple[str, ...]
    source: Optional[Path] = None
    library: str = ""
    replaced: str = ""

    def defaults(self) -> Dict[str, object]:
        """The fields a new interface of this kind is proposed with."""
        out: Dict[str, object] = {"integration_style": self.integration_style}
        if self.protocols:
            out["protocol"] = self.protocols[0]
        if self.auth_methods:
            out["auth_method"] = self.auth_methods[0]
        if self.frequency:
            out["frequency"] = self.frequency
        if self.direction:
            out["direction"] = self.direction
        if self.patterns:
            out["patterns"] = list(self.patterns)
        return out


def _listed(value) -> Tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return (str(value).strip(),)


def parse_connection(data: dict, source: Optional[Path] = None) -> ConnectionKind:
    where = " (%s)" % source.name if source else ""
    if not isinstance(data, dict) or not data.get("connection_id"):
        raise LibraryError("a connection kind needs a connection_id%s" % where)
    kind_id = str(data["connection_id"])
    if not data.get("name"):
        raise LibraryError("connection kind %s needs a name%s" % (kind_id, where))
    style = str(data.get("integration_style") or "")
    if style not in INTEGRATION_STYLES:
        raise LibraryError(
            "connection kind %s has integration_style %r; it is one of %s%s"
            % (kind_id, style, ", ".join(INTEGRATION_STYLES), where)
        )
    protocols = _listed(data.get("protocols"))
    if not protocols:
        # A kind with no protocol recognizes nothing, and says nothing a new
        # interface could be proposed with.
        raise LibraryError("connection kind %s names no protocol%s" % (kind_id, where))
    return ConnectionKind(
        connection_id=kind_id,
        name=str(data["name"]),
        description=" ".join(str(data.get("description") or "").split()),
        integration_style=style,
        protocols=protocols,
        auth_methods=_listed(data.get("auth_methods")),
        frequency=str(data.get("frequency") or ""),
        direction=str(data.get("direction") or ""),
        patterns=_listed(data.get("patterns")),
        source=source,
    )


def load_connections(root: Path) -> Dict[str, ConnectionKind]:
    """Every kind, in file order, the organization's after the shipped ones.
    A missing folder is an empty catalog: the kinds describe an estate, and
    an estate need not have any yet."""
    return load_layer(
        root, CONNECTIONS_DIR, parse_connection, lambda k: k.connection_id, "connection kind"
    )


def overlaps(kinds: Dict[str, ConnectionKind]) -> List[str]:
    """Each style and protocol two kinds both claim, said as a finding. An
    interface over it would be of both, and the catalog would count it twice."""
    claimed: Dict[Tuple[str, str], str] = {}
    out: List[str] = []
    for kind in kinds.values():
        for protocol in kind.protocols:
            key = (kind.integration_style, protocol.lower())
            if key in claimed:
                out.append(
                    "connection kinds %s and %s both claim %s over %s"
                    % (claimed[key], kind.connection_id, kind.integration_style, protocol)
                )
            else:
                claimed[key] = kind.connection_id
    return out


def find_kind(word: str, kinds: Dict[str, ConnectionKind]) -> Optional[ConnectionKind]:
    """The kind a word names, by its id or its name, case aside: what an
    arrow says (`API call`, `api-call`) or a notebook asks for."""
    key = str(word or "").strip().lower()
    if not key:
        return None
    for kind in kinds.values():
        if key in (kind.connection_id.lower(), kind.name.lower()):
            return kind
    return None


def kind_by_protocol(protocol: str, kinds: Dict[str, ConnectionKind]) -> Optional[ConnectionKind]:
    """The one kind that carries a protocol, when exactly one does: an
    arrow that says `MQ` is a request on a queue here, and one that says a
    protocol two kinds carry says nothing about its kind."""
    key = str(protocol or "").strip().lower()
    hits = [k for k in kinds.values() if key and key in (p.lower() for p in k.protocols)]
    return hits[0] if len(hits) == 1 else None


def kind_of(interface: dict, kinds: Dict[str, ConnectionKind]) -> Optional[str]:
    """The kind an interface's own fields say it is, or None."""
    style = str(interface.get("integration_style") or "")
    protocol = str(interface.get("protocol") or "").lower()
    for kind in kinds.values():
        if kind.integration_style == style and protocol in (p.lower() for p in kind.protocols):
            return kind.connection_id
    return None


def sorted_by_kind(
    interfaces: Sequence[dict], kinds: Dict[str, ConnectionKind]
) -> Tuple[Dict[str, List[dict]], List[dict]]:
    """Each kind's interfaces, and the ones of no kind, in id order."""
    by_kind: Dict[str, List[dict]] = {kind_id: [] for kind_id in kinds}
    none: List[dict] = []
    for record in sorted(interfaces, key=lambda r: str(r.get("interface_id"))):
        found = kind_of(record, kinds)
        (by_kind[found] if found else none).append(record)
    return by_kind, none
