from delivery_starter.flags import (
    default_source,
    environment_source,
    fixed_source,
    flag_enabled,
    flag_key,
    flag_variable,
)


def test_a_flag_is_spelled_the_way_the_stack_asks_ecs_to_spell_it() -> None:
    # The same transform as `FLAG_${upper(replace(flag.key, "-", "_"))}` in flags.tf, which is
    # what puts the value in this container's environment at start-up. If this expectation
    # changes the flag stops arriving — and an absent flag reads as off, so nothing says so.
    assert flag_variable("checkout-v2") == "FLAG_CHECKOUT_V2"
    assert flag_variable("publish-table") == "FLAG_PUBLISH_TABLE"


def test_the_key_is_the_exact_inverse_of_the_variable() -> None:
    # Exact only because `check-flags.py` holds a key to `[a-z0-9][a-z0-9-]*`: no underscore can
    # be in a key, so every underscore in the variable came from a dash.
    for key in ("checkout-v2", "publish-table", "a", "b2b-invoicing-v10"):
        assert flag_key(flag_variable(key)) == key


def test_a_variable_that_is_not_a_flag_has_no_key() -> None:
    assert flag_key("DATABASE_URL") is None
    assert flag_key("PGSSLMODE") is None
    # The browser's spelling of the same flag. It is a flag, but it is not this side's — the
    # prefix anchor is what keeps the two apart, here and in `check-flags.py`'s read pattern.
    assert flag_key("VITE_FLAG_CHECKOUT_V2") is None


def test_an_environment_source_reads_a_key_under_the_name_the_stack_gives_it() -> None:
    # The transform is the environment's business and nobody else's: this is the only source that
    # knows a flag is carried under a different name than the one it is declared with.
    assert environment_source({"FLAG_CHECKOUT_V2": "on"}).value("checkout-v2") == "on"
    assert environment_source({}).value("checkout-v2") is None


def test_an_environment_source_snapshots_every_flag_and_nothing_that_is_not_one() -> None:
    # What the service serves to the browser app, which cannot read these itself. The database URL
    # is in the same environment and is not a flag; `VITE_FLAG_…` is a flag and is not this side's.
    source = environment_source(
        {
            "FLAG_CHECKOUT_V2": "on",
            "FLAG_PUBLISH_TABLE": "off",
            "DATABASE_URL": "postgres://nope",
            "VITE_FLAG_CHECKOUT_V2": "on",
        }
    )
    assert source.snapshot() == {"checkout-v2": "on", "publish-table": "off"}


def test_a_fixed_source_is_keyed_by_the_flag_key_so_a_test_never_spells_a_variable() -> None:
    assert fixed_source({"checkout-v2": "on"}).value("checkout-v2") == "on"
    assert fixed_source({}).value("checkout-v2") is None
    assert fixed_source({"checkout-v2": "on"}).snapshot() == {"checkout-v2": "on"}


def test_the_default_source_is_the_transport_this_service_has() -> None:
    # Where a flag comes from is this one function, and a change of transport is a change to it
    # alone. Asked for a key nothing declares so that somebody who has exported a real flag to
    # try a feature locally does not fail this suite by doing so.
    assert default_source().value("no-flag-sets-this") is None


def test_a_flag_is_on_only_for_the_value_make_flag_writes() -> None:
    assert flag_enabled("checkout-v2", fixed_source({"checkout-v2": "on"})) is True
    assert flag_enabled("checkout-v2", fixed_source({"checkout-v2": "off"})) is False


def test_a_flag_nothing_set_is_off_rather_than_an_error() -> None:
    # The window between merging code that reads a flag and the apply that creates its
    # parameter. Off is a feature nobody can see yet; a KeyError is a task that will not start.
    assert flag_enabled("checkout-v2", fixed_source({})) is False


def test_a_value_the_reader_does_not_understand_is_off() -> None:
    # What a shell, a tfvars file or a hand-run `aws ssm put-parameter` would let somebody
    # write. None of them is the spelling, so all of them are off: a flag whose value is not
    # understood hides the feature it gates rather than half-revealing one.
    for value in ("true", "1", "ON", "yes"):
        assert flag_enabled("checkout-v2", fixed_source({"checkout-v2": value})) is False


def test_a_flag_reads_through_whichever_source_it_is_given() -> None:
    # The two implementations meeting at one call: same key, same answer, different transport.
    assert flag_enabled("checkout-v2", environment_source({"FLAG_CHECKOUT_V2": "on"})) is True
    assert flag_enabled("checkout-v2", environment_source({})) is False
