```python
# Repository against a real database — fresh schema per test
class TestSqlOrderRepository:
    def test_persists_and_retrieves_an_order(self, test_db: Connection) -> None:
        repo = SqlOrderRepository(test_db)
        test_order = get_test_order()

        repo.save(test_order)
        found = repo.find_by_id(test_order.id)

        assert found == test_order
```
