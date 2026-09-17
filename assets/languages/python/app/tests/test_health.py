from delivery_starter import health


def test_health_reports_ready() -> None:
    assert health() == {"status": "ok"}
