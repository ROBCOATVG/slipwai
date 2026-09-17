"""The environment this process was given, and what happens when it cannot be used.

Driven through the model rather than through the entry point: `main` reads nothing itself, so what
is worth asserting is that the model carries the defaults `.env.example` writes down and that a
value the service cannot use is refused with the variable named.
"""

from __future__ import annotations

import pytest

# Parenthesised because this package is named after the project, and a project's name can be
# long enough to put a one-line import over the line-length gate.
from delivery_starter.settings import (
    ConfigurationError,
    Settings,
    load_settings,
)


def test_carries_the_defaults_the_environment_template_writes_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("HOST", raising=False)

    settings = load_settings()

    assert settings.port == 3000
    assert settings.host == "0.0.0.0"


def test_reads_a_variable_whatever_case_the_environment_spells_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORT", "8080")

    assert load_settings().port == 8080


def test_refuses_a_variable_it_cannot_use_and_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The point of checking the environment at start-up rather than at the point of use.

    An operator only ever sees the variable, so the refusal has to name the variable and not the
    field the validator happens to call it.
    """
    monkeypatch.setenv("PORT", "the-usual-one")

    with pytest.raises(ConfigurationError) as refusal:
        load_settings()

    assert "PORT" in str(refusal.value)


def test_refuses_an_address_that_is_not_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Absent is fine — `main` falls back to the bound port. Present and not a URL is not: it would
    # be printed, pasted, and lead nowhere.
    monkeypatch.setenv("PUBLIC_BASE_URL", "service.internal:3000")

    with pytest.raises(ConfigurationError) as refusal:
        load_settings()

    assert "PUBLIC_BASE_URL" in str(refusal.value)


def test_ignores_everything_in_the_environment_that_is_not_this_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A container's environment holds far more than one service's own, and refusing the rest would
    # refuse every deployment.
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")

    assert isinstance(load_settings(), Settings)


def test_an_allow_list_is_read_the_way_a_deployment_writes_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a.example, http://b.example,")

    # A trailing comma must not become a permission for the empty string, which is what an `origin`
    # header carries when a request has none.
    assert load_settings().cors_origins() == ["http://a.example", "http://b.example"]


def test_no_origin_is_allowed_until_one_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    # Empty is the default, and it is same-origin only.
    assert load_settings().cors_origins() == []
