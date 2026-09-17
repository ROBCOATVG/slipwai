```python
# tests/helpers/test_db.py — fresh database per test, no shared state
@pytest.fixture
def test_db() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")  # or a throwaway container for real Postgres
    try:
        apply_migrations(connection, MIGRATIONS)
        yield connection
    finally:
        connection.close()
```
