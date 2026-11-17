# Review of the handed-over surfaces

Seven pages under `docs/design/surfaces/`, reviewed against the research note and the specification.

## Counts

| Surface | Blocker | Should-address | Nice-to-have |
|---|---|---|---|
| Booking | 2 | 3 | 1 |
| Calendar | 1 | 2 | 0 |

## Booking — `docs/design/surfaces/booking.html`

- **Blocker** — Nothing says what happens when two members book the same boat.
- **Blocker** — No error state for a boat out of service.
- **Should-address** — The empty state says nothing about how to book.
- **Nice-to-have** — The calendar could start on Monday.

## Calendar — `docs/design/surfaces/calendar.html`

- [Critical] Two bookings can overlap on the same slot.
- [Should-address] The legend is missing.
