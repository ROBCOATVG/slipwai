```python
import logging
from typing import Protocol


# Driven port — application-owned because the use case consumes it.
# Probe methods take domain types only, return None, and never influence
# control flow. No log levels, no metric names, no framework types.
class PledgeInstrumentation(Protocol):
    def pledge_rejected(self, reason: "PledgeRejectionReason", occasion_id: "OccasionId") -> None: ...
    def pledge_accepted(self, amount: "Money", occasion_id: "OccasionId") -> None: ...


class PledgingToOccasions:
    """Use case announces domain facts; the adapter decides severity."""

    def __init__(self, persistence: "PledgePersistence", instrumentation: PledgeInstrumentation) -> None:
        self._persistence = persistence
        self._instrumentation = instrumentation

    async def pledge_to_occasion(self, dto: "PledgeToOccasionCommand") -> "PledgeResult":
        ...  # calls self._instrumentation.pledge_rejected/pledge_accepted as outcomes occur


class TelemetryPledgeInstrumentation:
    """Adapter decides severity, metric names, span attributes — swappable
    without touching a use case."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def pledge_rejected(self, reason: "PledgeRejectionReason", occasion_id: "OccasionId") -> None:
        self._logger.warning("Pledge rejected", extra={"reason": reason, "occasion_id": occasion_id})

    def pledge_accepted(self, amount: "Money", occasion_id: "OccasionId") -> None:
        self._logger.info(
            "Pledge accepted",
            extra={
                "minor_units": amount.minor_units,
                "currency": amount.currency,
                "occasion_id": occasion_id,
            },
        )
```
