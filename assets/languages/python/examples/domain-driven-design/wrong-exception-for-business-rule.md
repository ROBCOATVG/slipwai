```python
# WRONG — throwing for what should be an expected business outcome. Nothing
# in the function's signature says this can fail, and every caller must
# remember to catch this specific exception type.
def pledge_contribution(
    occasion: "Occasion", eligibility: "Eligibility", pledge: "NewPledge"
) -> "Occasion":
    if occasion.is_funding_closed:
        raise FundingClosedError()
    ...
```
