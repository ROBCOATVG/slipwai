"""PLACEHOLDER — this is NOT a working OIDC client.

Selecting Keycloak wires the container, the environment variables, and the group-to-role
mapping. The protocol flow is deliberately not written here.

OIDC is one of the few places where writing it yourself from memory is a bad idea. Before
implementing, load `skills/secure-oauth-oidc/SKILL.md` — it covers what this file must get
right and what silently breaks if it does not:

  - Authorization Code flow with PKCE. Never the implicit grant.
  - `state` bound to the session (CSRF) and `nonce` bound to the ID token (replay).
  - Full ID-token validation: signature against the issuer's JWKS, `iss`, `aud`, `exp`,
    `nonce`.
  - Exact redirect-URI registration; no wildcards.
  - Mix-up defence when more than one issuer is possible.

Use a maintained OIDC client library rather than hand-rolling these checks.

The parity hazard worth knowing about now: group-to-role mapping is where this breaks in the
least helpful way. Groups that exist in staging but not production produce an authorisation
model that passes every test and fails in production. Assert the mapping at startup (see
`assert_role_mapping`) so a misconfigured environment refuses to boot instead of misbehaving
under load.

Roles are yours to name. Nothing below prescribes a role set, because an authorisation model
is a product decision. Declare your own and the mechanism follows it::

    mapping = {"admin": "app-admin", "operator": "app-operator", "viewer": "app-viewer"}

When the flow is written, read the groups from the claim named by ``OIDC_GROUPS_CLAIM`` rather than
from a literal: Keycloak's group-membership mapper writes ``groups``, Cognito writes
``cognito:groups``, and the one mapping below serves both.

The three group names in `docker/keycloak/realms/app.json` and in `.env.example` are the local
fixture those values are checked against, not a prescription.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

#: Application role -> the provider group that grants it.
RoleMapping = Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    roles: tuple[str, ...]


def assert_role_mapping(mapping: RoleMapping) -> None:
    """Assert every configured role has a group, at startup.

    Called by the composition root. Fails loudly rather than granting nothing silently: a
    mapping assembled from environment variables at runtime may be missing an entry, and a
    missing group grants nothing while looking identical to a permissions bug.
    """
    if not mapping:
        raise ValueError(
            "OIDC group mapping is empty, so no principal can ever hold a role. Declare the "
            "roles this product has before wiring the provider."
        )
    missing = [role for role, group in mapping.items() if not group or not group.strip()]
    if missing:
        raise ValueError(
            f"OIDC group mapping incomplete for: {', '.join(sorted(missing))}. A missing "
            "group grants nothing and looks identical to a permissions bug at runtime."
        )


def resolve_roles(group_claims: Sequence[str], mapping: RoleMapping) -> tuple[str, ...]:
    """Map provider group claims to application roles. Pure, so testable without a provider."""
    # Keycloak's group-membership mapper emits `/app-admin` when `full.path` is true and
    # `app-admin` when it is false. Accepting both means a realm exported with the other
    # setting does not silently grant nobody anything.
    claims = {claim.removeprefix("/") for claim in group_claims}
    return tuple(role for role, group in mapping.items() if group in claims)


def not_implemented() -> None:
    raise NotImplementedError(
        "OIDC flow not implemented. See the guidance at the top of this file and the "
        "secure-oauth-oidc skill."
    )
