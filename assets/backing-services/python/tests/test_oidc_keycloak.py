from __future__ import annotations

import pytest

from delivery_starter.adapters.driving.http.auth.oidc_keycloak import (
    assert_role_mapping,
    not_implemented,
    resolve_roles,
)

MAPPING = {"admin": "app-admin", "operator": "app-operator", "viewer": "app-viewer"}


def test_grants_only_the_roles_whose_groups_the_token_carries() -> None:
    assert resolve_roles(["app-admin", "app-viewer"], MAPPING) == ("admin", "viewer")


def test_accepts_a_full_path_group_claim_because_a_realm_may_be_exported_either_way() -> None:
    assert resolve_roles(["/app-operator"], MAPPING) == ("operator",)


def test_grants_nothing_for_a_group_that_maps_to_no_role() -> None:
    assert resolve_roles(["some-other-group"], MAPPING) == ()


def test_refuses_to_boot_on_an_incomplete_mapping_rather_than_granting_nothing_silently() -> None:
    with pytest.raises(ValueError, match="incomplete for: operator"):
        assert_role_mapping({**MAPPING, "operator": "   "})


def test_refuses_an_empty_mapping_because_no_principal_could_ever_hold_a_role() -> None:
    with pytest.raises(ValueError, match="empty"):
        assert_role_mapping({})


def test_accepts_a_complete_mapping() -> None:
    assert_role_mapping(MAPPING)


def test_the_flow_itself_refuses_rather_than_pretending() -> None:
    """A placeholder that returned a principal would be worse than one that raises: every downstream
    authorisation check would pass in tests and grant nothing in production."""
    with pytest.raises(NotImplementedError, match="not implemented"):
        not_implemented()
