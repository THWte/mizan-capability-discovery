"""
MIZAN Agent Society v1 - Governed Memory

An append-only, namespace-scoped memory store shared by every agent in the
society. Two rules give it its governance teeth:

1. **Namespace-scoped writes.** An agent may only write keys under its own
   namespace (``f"{agent_role}/..."``) or the shared namespace
   (``"shared/..."``). This prevents one agent from silently overwriting
   another agent's state (e.g. Evolution Agent cannot write into
   Architecture Guardian's namespace to fake a PASS verdict).
2. **Append-only.** Writing an already-used key raises
   ``AgentContractError`` -- callers must write a new, distinct key instead
   of overwriting an existing entry. Combined with ``audit_log()``, this
   gives the society a complete, tamper-evident history of who wrote what
   and when (the agent-memory analogue of Invariant 7, Complete Reverse
   Traceability).

Governed Memory also rejects any value carrying a promoted-truth-status key
(``fact``/``accepted_fact``/...) at any nesting depth, mirroring the same
Invariant 2 rule enforced at the Handoff Contract layer -- memory is a
second place that promotion could otherwise be smuggled in, so it is
checked here too, recursively (see ``epistemic.py``).

3. **Privileged shared-namespace ACL.** Not every ``shared/*`` key is
   equally sensitive. A small set of shared sub-namespaces (currently
   ``shared/architecture_approval/*`` and ``shared/verified/*``) are
   reserved for the Architecture Guardian only -- no other agent may write
   into them, even though they live under the otherwise-open ``shared/``
   prefix. This prevents, e.g., the Evolution Agent or QA/Red-Team agent
   from writing a fake architecture-approval record into shared memory.
"""
from __future__ import annotations

import dataclasses
from typing import Any

from .epistemic import FORBIDDEN_KEYS, validate_no_promoted_epistemic_state
from .errors import AgentContractError
from .registry import ARCHITECTURE_GUARDIAN, KNOWN_AGENT_ROLES

# Kept as an alias of the shared, canonical list in ``epistemic.py`` so
# this module and ``handoff_contract.py`` can never drift apart on what
# counts as "forbidden".
FORBIDDEN_VALUE_KEYS = FORBIDDEN_KEYS

# shared/<prefix>/... namespaces that only specific agent roles may write
# to, even though they are nominally under the shared/ prefix that is
# otherwise open to every known agent role.
SHARED_PRIVILEGED_PREFIXES: dict[str, tuple[str, ...]] = {
    "shared/architecture_approval/": (ARCHITECTURE_GUARDIAN,),
    "shared/verified/": (ARCHITECTURE_GUARDIAN,),
}


@dataclasses.dataclass(frozen=True)
class MemoryEntry:
    key: str
    value: Any
    written_by: str
    written_at: str
    version: int


class GovernedMemory:
    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._log: list[MemoryEntry] = []

    def write(self, *, key: str, value: Any, written_by: str, written_at: str) -> MemoryEntry:
        if written_by not in KNOWN_AGENT_ROLES:
            raise AgentContractError(f"Unknown writer agent role: {written_by!r}.")
        if not key or "/" not in key:
            raise AgentContractError(
                f"Memory key {key!r} must be namespaced as 'namespace/...'."
            )
        namespace = key.split("/", 1)[0]
        if namespace != written_by and namespace != "shared":
            raise AgentContractError(
                f"Agent {written_by!r} cannot write key {key!r}: outside its own "
                f"namespace ({written_by}/...) and not in the shared namespace "
                "(shared/...)."
            )
        if namespace == "shared":
            for prefix, allowed_roles in SHARED_PRIVILEGED_PREFIXES.items():
                if key.startswith(prefix) and written_by not in allowed_roles:
                    raise AgentContractError(
                        f"Key {key!r} is in a privileged shared namespace "
                        f"({prefix}*) reserved for {allowed_roles}; "
                        f"{written_by!r} may not write it."
                    )
        if key in self._entries:
            raise AgentContractError(
                f"Key {key!r} already exists. Governed memory is append-only: "
                "write a new, distinct key instead of overwriting an existing "
                "entry."
            )
        validate_no_promoted_epistemic_state(value)
        entry = MemoryEntry(
            key=key,
            value=value,
            written_by=written_by,
            written_at=written_at,
            version=len(self._log) + 1,
        )
        self._entries[key] = entry
        self._log.append(entry)
        return entry

    def read(self, key: str) -> MemoryEntry:
        if key not in self._entries:
            raise AgentContractError(f"No memory entry for key {key!r}.")
        return self._entries[key]

    def audit_log(self) -> tuple[MemoryEntry, ...]:
        """Full, ordered, append-only write history -- every agent's write,
        in the order it occurred, is visible here. Nothing can be removed
        or rewritten retroactively."""
        return tuple(self._log)
