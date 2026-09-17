```python
# WRONG — catching and re-raising just to add a message is noise, not
# clarity. It hides the original exception type behind a vague wrapper.
try:
    pledge_contribution(occasion, eligibility, pledge)
except Exception as exc:
    raise PledgeError("Failed to pledge") from exc
```
