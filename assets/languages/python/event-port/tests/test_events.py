from delivery_starter.application.ports.events import AppendResult


def test_version_conflict_is_a_value() -> None:
    assert AppendResult("version-conflict", 2).outcome == "version-conflict"
