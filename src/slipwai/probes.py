"""The two probes every generated service answers, and what each is for.

They answer two different questions, and the whole point of there being two is that a platform asks them of
different things.

**Liveness** — `HEALTH_PATH` — is "this process is up and answering". It asks nothing of any dependency, on
purpose: a liveness probe that goes red because a database is unreachable gets the process *restarted*,
turning somebody else's outage into a crash loop of this project's.

**Readiness** — `ready_path`, per backend — is "send me traffic". It runs a trivial query through the
event-store port, so a service whose store has gone away is taken out of the pool rather than left serving
failures. Everything that gates traffic waits on this one: the Compose healthcheck, the ALB target group,
the Container Apps readiness probe, and `make smoke` against a deployed environment.

A separate module from `backends.py` because both paths and the liveness body are read by the parts that
write Compose, the infrastructure variables, the docs and the run skill, and because the file they came
from had said for a while that the constant would become a table one day. It has.
"""
from __future__ import annotations

# The liveness probe every backend agrees on, for the same reason the port is named once: `make demo`
# prints it, `skills/run-the-app` tells the reader to curl it and quotes what comes back, and on a platform
# that asks liveness separately it is the path that decides a restart. Several literals in several files
# was one contract nobody could see, and the first backend to disagree with it would have disagreed
# silently.
HEALTH_PATH = "/health"

# Where each backend answers "send me traffic".
#
# A table rather than a constant, for exactly the reason `HEALTH_BODIES` below is one: a framework that owns
# startup owns the probe too, and both Java backends already serve a *readiness* endpoint — SmallRye Health
# and Actuator each aggregate their registered readiness checks on the path this project configures them
# onto, which is `HEALTH_PATH`. Giving those two a second, hand-written `/ready` beside a maintained one is
# the trade this repository has refused twice already; so their readiness path is the one their framework
# serves, and the three backends whose entry point this factory writes answer on `/ready`.
READY_PATHS = {
    "typescript": "/ready",
    "python": "/ready",
    "go": "/ready",
    "java-quarkus": HEALTH_PATH,
    "java-spring": HEALTH_PATH,
}

# The liveness body, which is where the backends stop agreeing — and the reason this is a table while
# `HEALTH_PATH` is a constant. A framework that owns startup ships the probe too, mounted on its own path
# and answering in its own shape. The path is configurable, so Quarkus's SmallRye Health is pointed at
# `HEALTH_PATH` like everything else; the shape is not, because MicroProfile Health fixes it. A
# hand-written `/health` beside a maintained one would buy back one literal and cost a route this project
# then owns forever, which is the wrong trade — so the literal moved instead.
HEALTH_BODIES = {
    "typescript": '{"status":"ok"}',
    "python": '{"status":"ok"}',
    "go": '{"status":"ok"}',
    "java-quarkus": '{"status":"UP","checks":[...]}',
    # Actuator's, and shorter than its sibling's for a reason worth stating: MicroProfile Health always
    # reports the per-check breakdown, while Actuator hides it unless `show-details` says otherwise — and
    # this project leaves that at `never`, because which dependencies a service has is not something an
    # unauthenticated caller needs. Same status vocabulary, one fewer disclosure.
    "java-spring": '{"status":"UP"}',
}


def ready_path(backend: str) -> str:
    """Where this backend answers "send me traffic" — what Compose, the ALB and the App Service wait on."""
    return READY_PATHS[backend]


def health_body(backend: str) -> str:
    """What this backend's liveness probe answers with, for prose that quotes it."""
    return HEALTH_BODIES[backend]
