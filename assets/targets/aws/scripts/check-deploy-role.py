#!/usr/bin/env python3
"""Fail when the service stack declares IAM the deploy role is not allowed to create or delete.

Two stacks meet at the deploy role, and nothing else connects them. `infra/bootstrap/` makes the role once,
applied by a person with admin credentials (`make bootstrap`): PowerUserAccess, which is everything but IAM,
and IAM back on roles carrying this project's name. `infra/service/` is applied by that role on every push to
`main`, and is free to declare any `aws_iam_*` resource. So a slice that adds an IAM user, a managed policy or
an instance profile passes every gate, merges, and the first place the two stacks meet is the production
apply — which is refused part-way, after it has changed whatever it reached first, on an action the
pipeline cannot grant itself. The person who reads that failure goes looking for the permission in the
console, when the answer is a statement in `infra/bootstrap/main.tf` and a `make bootstrap`.

This reads both stacks and holds each `aws_iam_*` resource under `infra/service/` to the policies the
bootstrap stack attaches to `aws_iam_role.deploy`: the action that creates it and the one that deletes it,
each granted on a resource of the same kind (`role/`, `user/`, `policy/`, …) or on `*`. It reads files, runs
no `tofu` and no `aws`, and needs nothing running.

What it does not see, said so a pass is not over-read: the name a resource is given against the name the
grant is scoped to (both are usually interpolated, and the answer is in the plan, not the text); the read,
tag and update actions an apply also calls (PowerUserAccess covers none of them, so the bootstrap policy
lists them beside each create); and IAM declared inside a module. A resource type it has no row for is a
failure, never a pass, and the message says where the row goes.
"""
from __future__ import annotations

import re
import sys
from fnmatch import fnmatchcase
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
BOOTSTRAP = ROOT / "infra/bootstrap"
SERVICE = ROOT / "infra/service"

# What tofu calls to create and to delete each IAM resource type, and the kind of IAM resource ARN the call
# is authorised against. The kind is the segment after the account in the ARN: `arn:aws:iam::<account>:<kind>/…`.
TYPES: dict[str, tuple[str, tuple[str, str]]] = {
    "aws_iam_role": ("role", ("iam:CreateRole", "iam:DeleteRole")),
    "aws_iam_role_policy": ("role", ("iam:PutRolePolicy", "iam:DeleteRolePolicy")),
    "aws_iam_role_policy_attachment": ("role", ("iam:AttachRolePolicy", "iam:DetachRolePolicy")),
    "aws_iam_service_linked_role": ("role", ("iam:CreateServiceLinkedRole", "iam:DeleteServiceLinkedRole")),
    "aws_iam_user": ("user", ("iam:CreateUser", "iam:DeleteUser")),
    "aws_iam_user_policy": ("user", ("iam:PutUserPolicy", "iam:DeleteUserPolicy")),
    "aws_iam_user_policy_attachment": ("user", ("iam:AttachUserPolicy", "iam:DetachUserPolicy")),
    "aws_iam_access_key": ("user", ("iam:CreateAccessKey", "iam:DeleteAccessKey")),
    "aws_iam_user_login_profile": ("user", ("iam:CreateLoginProfile", "iam:DeleteLoginProfile")),
    "aws_iam_user_group_membership": ("group", ("iam:AddUserToGroup", "iam:RemoveUserFromGroup")),
    "aws_iam_group": ("group", ("iam:CreateGroup", "iam:DeleteGroup")),
    "aws_iam_group_policy": ("group", ("iam:PutGroupPolicy", "iam:DeleteGroupPolicy")),
    "aws_iam_group_policy_attachment": ("group", ("iam:AttachGroupPolicy", "iam:DetachGroupPolicy")),
    "aws_iam_group_membership": ("group", ("iam:AddUserToGroup", "iam:RemoveUserFromGroup")),
    "aws_iam_policy": ("policy", ("iam:CreatePolicy", "iam:DeletePolicy")),
    "aws_iam_instance_profile": ("instance-profile", ("iam:CreateInstanceProfile", "iam:DeleteInstanceProfile")),
    "aws_iam_openid_connect_provider": ("oidc-provider",
                                        ("iam:CreateOpenIDConnectProvider", "iam:DeleteOpenIDConnectProvider")),
    "aws_iam_saml_provider": ("saml-provider", ("iam:CreateSAMLProvider", "iam:DeleteSAMLProvider")),
}
STRING = r'"(?:\\.|[^"\\])*"'
LITERAL = re.compile(STRING)
COMMENT = re.compile(rf"({STRING})|#[^\n]*|//[^\n]*|/\*.*?\*/", re.DOTALL)
RESOURCE = re.compile(r'\bresource\s+"(aws_iam_[a-z0-9_]+)"\s+"([^"]+)"')
ARN_KIND = re.compile(r"^arn:[^:]*:iam::[^:]*:([a-z-]+)/")


def uncommented(text: str) -> str:
    """HCL without its comments; a `#` inside a string is part of the string."""
    return COMMENT.sub(lambda match: match.group(1) or "", text)


def body(text: str, opening: int) -> str:
    """What is between the brace at `opening` and the one that closes it, stepping over strings — whose
    `${…}` interpolations carry braces of their own."""
    depth, index = 0, opening
    while index < len(text):
        character = text[index]
        if character == '"':
            literal = LITERAL.match(text, index)
            index = literal.end() if literal else len(text)  # an unterminated string runs to the end
            continue
        depth += {"{": 1, "}": -1}.get(character, 0)
        if depth == 0:
            return text[opening + 1:index]
        index += 1
    return text[opening + 1:]


def blocks(text: str, header: str) -> list[tuple[re.Match[str], str]]:
    return [(match, body(text, match.end() - 1)) for match in re.finditer(header + r"\s*\{", text)]


def strings(listing: str) -> list[str]:
    return [literal[1:-1] for literal in LITERAL.findall(listing)]


def deploy_grants(text: str) -> list[tuple[list[str], list[str]]]:
    """Every Allow statement of every policy document the bootstrap stack attaches to `aws_iam_role.deploy`."""
    attached = set()
    for _, inline in blocks(text, r'\bresource\s+"aws_iam_role_policy"\s+"[^"]+"'):
        if re.search(r"\brole\s*=\s*aws_iam_role\.deploy\.(?:id|name)\b", inline):
            attached |= set(re.findall(r"\bpolicy\s*=\s*data\.aws_iam_policy_document\.([A-Za-z0-9_-]+)\.json", inline))
    grants = []
    for match, document in blocks(text, r'\bdata\s+"aws_iam_policy_document"\s+"([^"]+)"'):
        if match.group(1) not in attached:
            continue
        for _, statement in blocks(document, r"\bstatement"):
            if re.search(r'\beffect\s*=\s*"Deny"', statement):
                continue
            actions = re.search(r"\bactions\s*=\s*\[(.*?)\]", statement, re.DOTALL)
            resources = re.search(r"\bresources\s*=\s*\[(.*?)\]", statement, re.DOTALL)
            if actions and resources:
                grants.append((strings(actions.group(1)), strings(resources.group(1))))
    return grants


def granted(action: str, kind: str, grants: list[tuple[list[str], list[str]]]) -> bool:
    for actions, resources in grants:
        if not any(fnmatchcase(action.lower(), pattern.lower()) for pattern in actions):
            continue
        for resource in resources:
            found = ARN_KIND.match(resource)
            if resource == "*" or (found and found.group(1) == kind):
                return True
    return False


def main() -> int:
    if not (BOOTSTRAP / "main.tf").is_file() or not SERVICE.is_dir():
        print("check-deploy-role: no infra/bootstrap/main.tf and infra/service/ here; nothing to compare")
        return 0
    grants = deploy_grants("\n".join(uncommented(path.read_text()) for path in sorted(BOOTSTRAP.glob("*.tf"))))
    problems, checked = [], 0
    for path in sorted(SERVICE.rglob("*.tf")):
        relative = path.relative_to(ROOT).as_posix()
        for match in RESOURCE.finditer(uncommented(path.read_text())):
            kind_actions = TYPES.get(match.group(1))
            address = f"{match.group(1)}.{match.group(2)}"
            if kind_actions is None:
                problems.append(f"{relative}: {address} is an IAM type this gate has no row for, so it cannot say "
                                "whether the deploy role may create it — add its create and delete actions to TYPES "
                                "in scripts/check-deploy-role.py, and to the bootstrap policy if they are missing")
                continue
            checked += 1
            kind, actions = kind_actions
            for action in actions:
                if not granted(action, kind, grants):
                    problems.append(f"{relative}: {address} needs {action} on {kind}/…, and the deploy role is "
                                    f"granted it on no {kind}")
    if problems:
        print("check-deploy-role: FAILED — the service stack declares IAM the deploy role cannot manage, so the "
              "production apply would be refused part-way\n  - " + "\n  - ".join(problems))
        print("The fix is not in infra/service/ and not in the pipeline: add the actions to a statement of "
              "`data.aws_iam_policy_document.deploy_iam` in infra/bootstrap/main.tf, scoped the way the role "
              "statement is (`arn:aws:iam::${local.account}:<kind>/${var.project}-*`), and have someone with "
              "admin AWS credentials run `make bootstrap`. The deploy role cannot grant itself what it lacks.")
        return 1
    print(f"check-deploy-role: {checked} IAM resource(s) in infra/service/, each within the deploy role's grants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
