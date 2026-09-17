```python
def test_sets_retry_limit():
    worker.set_retry_limit(3)
    assert worker.get_retry_limit() == 3  # Trivial
```
