from typing import Literal, TypedDict


class Health(TypedDict):
    status: Literal["ok"]


def health() -> Health:
    return {"status": "ok"}
