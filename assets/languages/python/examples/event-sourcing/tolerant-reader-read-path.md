```python
from __future__ import annotations

from typing import Any


# On read: raw stored JSON -> validate the stored (possibly old) shape -> upcast to current.
def to_domain_event(raw: Any) -> AccountEvent:
    return upcast_account_event(parse_stored_account_event(raw))


# `parse_stored_account_event` validates against a tolerant schema of every
# persisted version. Unknown fields may be ignored; only fields that were
# optional or have a proven context-invariant default may be absent. It
# validates what is on disk, then the upcaster maps it to the current shape —
# it raises on genuinely corrupt data (a bug, not a business case). Validation
# always runs before upcasting: never let unvalidated data reach the upcaster.
# See the OrderPlaced upcaster example for `upcast_account_event`'s shape.
```
