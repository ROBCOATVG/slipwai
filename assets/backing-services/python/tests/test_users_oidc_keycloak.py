from __future__ import annotations

import pytest

from delivery_starter.adapters.driving.http.users.oidc_keycloak import (
    Customer,
    customer_from_claims,
    not_implemented,
)

CUSTOMERS_ISSUER = "http://localhost:8081/realms/customers"
STAFF_ISSUER = "http://localhost:8081/realms/app"

VERIFIED_CUSTOMER = {
    "iss": CUSTOMERS_ISSUER,
    "sub": "a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34",
    "email": "ada@example.com",
    "email_verified": True,
}


def test_accepts_a_verified_customer_of_the_expected_realm() -> None:
    assert customer_from_claims(VERIFIED_CUSTOMER, CUSTOMERS_ISSUER) == Customer(
        subject="a8f3c1e2-0b4d-4f6a-9c7e-2d1b5e8f0a34", email="ada@example.com"
    )


def test_refuses_the_staff_realm_whose_issuer_differs_by_one_path_segment() -> None:
    with pytest.raises(ValueError, match="is not http://localhost:8081/realms/customers"):
        customer_from_claims({**VERIFIED_CUSTOMER, "iss": STAFF_ISSUER}, CUSTOMERS_ISSUER)


def test_refuses_a_token_with_no_subject_because_nothing_else_is_a_stable_key() -> None:
    with pytest.raises(ValueError, match="no sub claim"):
        customer_from_claims({**VERIFIED_CUSTOMER, "sub": ""}, CUSTOMERS_ISSUER)


def test_refuses_an_unverified_email_because_it_is_one_anybody_can_type() -> None:
    with pytest.raises(ValueError, match="verified email"):
        customer_from_claims({**VERIFIED_CUSTOMER, "email_verified": False}, CUSTOMERS_ISSUER)


def test_the_token_validation_itself_refuses_rather_than_pretending() -> None:
    """A placeholder that returned a customer would be worse than one that raises: every use case
    downstream would pass in tests against a customer nobody authenticated."""
    with pytest.raises(NotImplementedError, match="not implemented"):
        not_implemented()
