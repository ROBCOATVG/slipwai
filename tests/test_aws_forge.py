"""How a project going to `aws` reaches the forge its pipeline is configured on.

`scripts/bootstrap.py` is the one thing a person runs on the first day, and the forge is the part of it that
is somebody else's server: self-hosted, often behind a proxy, reached with a token whose scopes are unknown
until it is refused. What is proved here is that the requests get through such a proxy, and that a refusal
reads as one — because the failure this suite was written for reported an answered 403 as an unreachable
host, and sent whoever read it to the network for two rounds. What the whole target is given is
`test_aws_target.py`; the stack itself is `test_aws_stack.py`.
"""
from __future__ import annotations

import contextlib
import http.server
import importlib.util
import io
import json
import os
import re
import tempfile
import threading
from itertools import takewhile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default


def load_script(path: Path):
    """A generated script imported as a module, so its own functions can be called rather than its CLI."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"{path} is not importable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# What a proxy in front of a self-hosted forge does, which is the case the real thing failed on: the default
# `Python-urllib/3.x` agent is refused before the forge is reached, and every other answer is the forge's.
FORGE_ANSWERS = {
    "/api/v1/user": (200, b'{"login": "me"}'),
    "/api/v1/repos/me/there": (200, b'{"full_name": "me/there"}'),
    "/api/v1/repos/me/missing": (404, b'{"message": "Not Found"}'),
    "/api/v1/refused": (401, b'{"message": "invalid username, password or token"}'),
    "/api/v1/repos/me/refused": (401, b'{"message": "invalid username, password or token"}'),
}


def deployed_environments(repo: Path) -> set[str]:
    """Every environment the generated workflows deploy to, read out of the workflows themselves.

    Derived rather than listed, because listing is exactly what went wrong: the trust policy named one
    subject and nobody noticed the jobs asked for others. An environment added to a workflow, or a new
    workflow that declares one, has to fail here rather than in somebody's account.
    """
    found: set[str] = set()
    for workflow in sorted((repo / ".github/workflows").glob("*.yml")):
        text = workflow.read_text()
        for value in re.findall(r"^ +environment: (.+)$", text, re.MULTILINE):
            found |= named(value.strip(), text)
    return found


def named(value: str, workflow: str) -> set[str]:
    """One `environment:` value as the environments it stands for.

    `rollback.yml` takes its environment as a `choice` dispatch input, so the options are the environments a
    run of it can be pointed at — and a token naming each of them is one that workflow can be issued.
    """
    expression = re.fullmatch(r"\$\{\{ *inputs\.(\w+) *\}\}", value)
    if not expression:
        return {value}
    options = workflow.split("inputs:", 1)[1].split(f"{expression.group(1)}:", 1)[1]
    listed = options.split("options:", 1)[1].splitlines()[1:]
    return {line.strip().removeprefix("- ") for line in takewhile(lambda line: line.strip().startswith("- "), listed)}


def trust_subjects(stack: str) -> list[str]:
    """The `sub` values the deploy role's trust admits, read out of the bootstrap stack."""
    condition = stack.split('variable = "token.actions.githubusercontent.com:sub"', 1)[1]
    return re.findall(r'"([^"]+)"', condition.split("values", 1)[1].split("]", 1)[0])


@contextlib.contextmanager
def stub_forge():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — the name is http.server's
            agent = self.headers.get("User-Agent", "")
            status, body = (
                (403, b"error code: 1010\n") if agent.startswith("Python-urllib")
                else FORGE_ANSWERS.get(self.path, (404, b'{"message": "Not Found"}'))
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class AwsForgeTest(FactoryTestCase):
    def generate_aws(self, directory: str, name: str):
        return self.generate(
            directory, name, "event-modelling", "go", "none", target="aws",
            event_store="memory", http=axis_default("http", "go", "aws"),
        )

    def test_bootstrap_names_itself_to_the_forge_and_tells_a_refusal_from_an_unreachable_host(self) -> None:
        """A self-hosted forge often sits behind a proxy, and the default `Python-urllib/3.x` agent is a
        banned signature on those: Cloudflare answers 403 `error code: 1010` before the forge sees anything.
        So the requests name themselves — and whatever *is* answered has to read as an answer, because
        "cannot reach the forge" sends whoever reads it to the network when the reason is in the body."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "forged")
            bootstrap = load_script(repo / "scripts/bootstrap.py")
            with stub_forge() as api:
                # A banned agent would be 403 here, so 200 is the proof the script named itself.
                self.assertEqual(bootstrap.gitea(api, "t", "GET", "/repos/me/there"), 200)
                self.assertEqual(bootstrap.gitea(api, "t", "GET", "/repos/me/missing"), 404)
                self.assertEqual(json.loads(bootstrap.fetch_json(api, "t", "/user"))["login"], "me")
                # An answered status is quoted with its body and what to check — not called unreachable.
                with self.assertRaises(bootstrap.Failure) as refused:
                    bootstrap.fetch_json(api, "t", "/refused")
                self.assertIn("answered 401", str(refused.exception))
                self.assertIn("GITEA_TOKEN", str(refused.exception))
                self.assertNotIn("cannot reach", str(refused.exception))
                # Only a 404 means a repository is not there. A refusal leaves it unknown, and creating one
                # that may already exist is not the answer to being told no.
                host = api.removeprefix("http://").removesuffix("/api/v1")
                with self.assertRaises(bootstrap.Failure) as unknown:
                    bootstrap.ensure_repository("http", host, "me/refused", "t")
                self.assertIn("whether it exists is unknown", str(unknown.exception))
                bootstrap.ensure_repository("http", host, "me/there", "t")  # there: nothing to do
            # A genuine connection failure still says the forge could not be reached.
            with self.assertRaises(bootstrap.Failure) as unreachable:
                bootstrap.fetch_json(api, "t", "/user")
            self.assertIn("cannot reach the forge", str(unreachable.exception))

    def test_the_github_trust_names_the_subject_github_issues_not_the_one_it_used_to(self) -> None:
        """Since 15 July 2026 a new repository's tokens say `repo:owner@<id>/name@<id>`, and a trust naming
        `repo:owner/name` matches nothing — `Not authorized to perform sts:AssumeRoleWithWebIdentity` under a
        trust policy that reads correctly. So the script asks GitHub what the prefix is, the stack takes it as
        a variable, and only when the forge cannot be asked does the name form stand, said out loud."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "trusted")
            stack = (repo / "infra/bootstrap/main.tf").read_text()
            self.assertEqual(
                trust_subjects(stack),
                [
                    "${local.subject_prefix}:ref:refs/heads/main",
                    "${local.subject_prefix}:environment:staging",
                    "${local.subject_prefix}:environment:production",
                ],
            )
            fallback = 'var.oidc_subject_prefix != "" ? var.oidc_subject_prefix : "repo:${var.repository}"'
            self.assertIn(f"subject_prefix = {fallback}", stack)
            self.assertIn('variable "oidc_subject_prefix"', (repo / "infra/bootstrap/variables.tf").read_text())
            script = (repo / "scripts/bootstrap.py").read_text()
            self.assertIn('f"-var=oidc_subject_prefix={subject_prefix}"', script)
            self.assertIn('if decision["forge"] == "github" else ""', script)

            bootstrap = load_script(repo / "scripts/bootstrap.py")
            tools = Path(directory) / "bin"
            tools.mkdir()
            gh = tools / "gh"
            immutable = "repo:me@83953097/trusted@1338299873"

            def asked(answer: str) -> tuple[str, str]:
                gh.write_text(f"#!/bin/sh\n{answer}\n")
                gh.chmod(0o755)
                said = io.StringIO()
                with contextlib.redirect_stderr(said):
                    prefix = bootstrap.github_subject_prefix("me/trusted")
                return prefix, said.getvalue()

            path = os.environ["PATH"]
            os.environ["PATH"] = f"{tools}{os.pathsep}{path}"
            try:
                # What GitHub says the token will carry is what the trust names, and the difference is announced.
                prefix, said = asked(f"echo '{{\"use_default\": true, \"sub_claim_prefix\": \"{immutable}\"}}'")
                self.assertEqual(prefix, immutable)
                self.assertIn(f"GitHub issues tokens for me/trusted as {immutable}", said)
                # A repository still on the name form gets exactly the trust it had, with nothing to say.
                prefix, said = asked("echo '{\"use_default\": true, \"sub_claim_prefix\": \"repo:me/trusted\"}'")
                self.assertEqual((prefix, said), ("repo:me/trusted", ""))
                # A refusal, and an answer without the field, both fall back to the name form and say so by name.
                refused = "echo '{\"message\": \"Resource not accessible\"}' >&2; exit 1"
                for answer in (refused, "echo '{\"use_default\": true}'"):
                    prefix, said = asked(answer)
                    self.assertEqual(prefix, "repo:me/trusted", answer)
                    self.assertIn(
                        "could not read me/trusted's OIDC subject prefix from GitHub; trusting repo:me/trusted", said,
                    )
                    self.assertIn("gh api /repos/me/trusted/actions/oidc/customization/sub", said)
                # No gh at all: the name form, quietly — configure_github will name the missing tool itself.
                gh.unlink()
                os.environ["PATH"] = str(Path(directory) / "empty")
                self.assertEqual(bootstrap.github_subject_prefix("me/trusted"), "repo:me/trusted")
            finally:
                os.environ["PATH"] = path

    def test_every_environment_the_workflows_deploy_to_is_a_subject_the_trust_admits(self) -> None:
        """GitHub does not put the same subject in every token. A job with no `environment:` gets
        `<prefix>:ref:refs/heads/main`; a job that declares one gets `<prefix>:environment:<name>` instead,
        with no ref in it at all. A trust naming only the first is a project that cannot deploy — the build
        job assumes the role and every job that would apply anything is refused — and nothing says so until
        an account does. So both sides are derived: the environments out of the workflows this factory
        writes, the subjects out of the stack it writes beside them."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "covered")
            environments = deployed_environments(repo)
            self.assertEqual(environments, {"staging", "production"})
            subjects = trust_subjects((repo / "infra/bootstrap/main.tf").read_text())
            prefix = "${local.subject_prefix}"
            self.assertIn(f"{prefix}:ref:refs/heads/main", subjects)
            for environment in environments:
                self.assertIn(f"{prefix}:environment:{environment}", subjects, subjects)
            # And nothing beyond them: a subject no job asks for is trust given away, and `environment:*`
            # would hand the deploy role to whatever environment anybody adds to the repository later.
            self.assertEqual(
                {s.split(":environment:", 1)[1] for s in subjects if ":environment:" in s}, environments
            )
            self.assertNotIn("*", "".join(subjects))
            # The other half, and the reason naming the environments is safe at all: `make bootstrap` holds
            # each of them to main, so a job elsewhere never gets a token carrying that subject.
            self.assertEqual(set(load_script(repo / "scripts/bootstrap.py").ENVIRONMENTS), environments)

    def test_bootstrap_holds_each_environment_to_main_and_survives_being_run_again(self) -> None:
        """An `:environment:` subject carries no branch, so trusting one is only safe because the environment
        itself refuses to deploy anything but `main` — otherwise any branch could declare `environment:
        staging` and be the deploy role, and `rollback.yml` is a dispatch run from a branch. The policy is a
        custom one naming main rather than `protected_branches`, which admits whatever branches carry a
        protection rule: the repository `./init` just created protects none, so that would admit nothing.
        `make bootstrap` is run again after `add-service`, so an environment already there is not a failure
        and not a second policy; a forge that refuses is said out loud over an account already bootstrapped."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "fenced")
            bootstrap = load_script(repo / "scripts/bootstrap.py")
            tools = Path(directory) / "bin"
            tools.mkdir()
            log, gh = Path(directory) / "calls", tools / "gh"
            # A forge that records what it was asked and answers the environment and its branch policies
            # apart, which is the difference between "already configured" and "configured but unrestricted".
            existing, policies = Path(directory) / "environment.json", Path(directory) / "policies.json"
            gh.write_text(
                f'#!/bin/sh\necho "$@" >> {log}\ncat >> {log}\necho >> {log}\n'
                f'case "$*" in *deployment-branch-policies*) cat {policies} ;; *) cat {existing} ;; esac\n'
            )
            gh.chmod(0o755)
            existing.write_text('{"deployment_branch_policy": null}')
            policies.write_text('{"branch_policies": []}')

            def ran() -> tuple[str, str]:
                log.write_text("")
                said = io.StringIO()
                with contextlib.redirect_stderr(said):
                    bootstrap.ensure_environments("me/fenced")
                return log.read_text(), said.getvalue()

            path = os.environ["PATH"]
            os.environ["PATH"] = f"{tools}{os.pathsep}{path}"
            try:
                calls, _ = ran()
                for environment in bootstrap.ENVIRONMENTS:
                    self.assertIn(f"--method PUT /repos/me/fenced/environments/{environment}", calls)
                    self.assertIn(
                        f"--method POST /repos/me/fenced/environments/{environment}/deployment-branch-policies",
                        calls,
                    )
                self.assertIn('"protected_branches": false', calls)
                self.assertIn('"custom_branch_policies": true', calls)
                self.assertIn('"name": "main"', calls)
                # Run again against what that left behind: nothing is created twice, and the environment is
                # not written at all — that PUT is a replace, so rewriting it would take off a wait timer or
                # a reviewer somebody has since added by hand.
                existing.write_text(
                    '{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}'
                )
                policies.write_text('{"branch_policies": [{"id": 1, "name": "main", "type": "branch"}]}')
                calls, said = ran()
                self.assertNotIn("--method PUT", calls)
                self.assertNotIn("--method POST", calls)
                self.assertIn("environment staging deploys from main only", said)
                # A refusal — protection rules need a plan on a private repository, a token needs a scope —
                # names what is left undone rather than raising over an account that is already bootstrapped.
                gh.write_text('#!/bin/sh\necho "Resource not accessible by integration" >&2\nexit 1\n')
                gh.chmod(0o755)
                _, refused = ran()
                self.assertIn("could not configure the staging environment of me/fenced", refused)
                self.assertIn("Settings → Environments", refused)
            finally:
                os.environ["PATH"] = path

    def test_a_failed_push_leaves_init_saying_how_to_pick_it_up(self) -> None:
        """`./init` runs under `set -e`, so an exit 1 from the push would end it before the line that says
        how to resume — which is the only thing left to go on when the forge has just refused."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "resumable")
            init = (repo / "init").read_text()
            self.assertIn('python3 scripts/bootstrap.py push "$repository" || true', init)
            self.assertLess(
                init.index("bootstrap.py push"), init.index("Not bootstrapped. When the repository exists")
            )
