```python
from dataclasses import replace


async def handle_pledge_message(message: "SqsMessage", env: "Env") -> None:
    """Queue deployment entrypoint = inline composition + driving adapter."""
    db = get_database_connection(env.database_url)
    occasion_repo = SqlAlchemyOccasionRepository(db)
    contributor_repo = SqlAlchemyContributorRepository(db)
    pledging: ForPledgingToOccasions = PledgingToOccasions(occasion_repo, contributor_repo)

    dto = PledgeSchema.model_validate_json(message.body)
    command = replace(dto.to_command(), pledge_id=make_pledge_id(message.message_id))
    await pledging.pledge_to_occasion(command)
```
