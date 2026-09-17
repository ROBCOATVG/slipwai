"""What an answer becomes under a target, and how to name it in a drawing.

Two functions every target's pages need and nothing else needs much: what this service's answer to an axis
is provisioned as under the target it is going to — `rds`, `cognito`, `flexible-server` — and the Mermaid
node id for a name. They live below the pages rather than inside one of them so that a second cloud's page
reads the same declaration as the first, rather than importing the first cloud's module to get at it.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..services import App
from ..targets import provisioned_as


def provisioned(service: App, axis: str, target: str) -> str | None:
    """What this service's answer to an axis becomes under the target — `rds`, `cognito` — or nothing."""
    if axis not in service.selection.axes:
        return None
    return provisioned_as(CATALOG, axis, service.selection.option(axis), target)


def node(name: str) -> str:
    """A Mermaid node id: the name with anything Mermaid would read as syntax replaced."""
    return "".join(c if c.isalnum() else "_" for c in name)
