"""`check-slice-scope` judging an events module's change, not its lines (issue 168).

manda's S115 needed one line of its context's events module changed —
`z.enum(['alert', 'reminder', 'digest'])` gaining `'invite'` — and the gate refused it, because by line a
widened enum is a removed line. Nothing on the board could land it, and the slice and its fairway's captain
parked for good. The rule is that the module may only grow; these hold what growing is, in each language
the keel generates, and that every way of shrinking or reshaping it is still refused, naming what it saw.

Each case is a module before and after, as a slice would write it, judged the way the gate judges a branch.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-slice-scope.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("scope_widening", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


SCOPE = load_gate()

#: manda's intake events module, around the line S115 needed (manda `ff6ad8b44`).
MANDA_BEFORE = """\
export const EMAIL_DELIVERED = 'EmailDelivered';
export const EMAIL_DELIVERY_FAILED = 'EmailDeliveryFailed';

const EmailKindShape = z.enum(['alert', 'reminder', 'digest']);
export type EmailDeliveryKind = z.infer<typeof EmailKindShape>;

/** The words a failure may be written with. A reader keeps any other string. */
const EmailDeliveredShape = z.object({
  to: z.string(),
  kind: EmailKindShape,
  sentAt: z.string(),
});
"""


def judged(before: str, after: str, path: str = "apps/app/src/domain/intake/events.ts") -> str | None:
    return SCOPE.events_violation(textwrap.dedent(before), textwrap.dedent(after), path)


class AcceptedTest(unittest.TestCase):
    """Each form a slice may write: the module grows, and the gate says nothing."""

    def assertGrows(self, before: str, after: str, path: str = "apps/app/src/domain/intake/events.ts") -> None:
        self.assertIsNone(judged(before, after, path))

    def test_manda_s115_a_member_added_to_a_zod_enum(self) -> None:
        self.assertGrows(MANDA_BEFORE, MANDA_BEFORE.replace("'digest']", "'digest', 'invite']"))

    def test_a_zod_enum_reflowed_over_several_lines_as_it_grows(self) -> None:
        self.assertGrows(MANDA_BEFORE, MANDA_BEFORE.replace(
            "z.enum(['alert', 'reminder', 'digest'])",
            "z.enum([\n  'alert',\n  'reminder',\n  'digest',\n  'invite',\n])"))

    def test_a_member_added_to_a_zod_union_of_literals(self) -> None:
        self.assertGrows("const Kind = z.union([z.literal('alert'), z.literal('digest')]);\n",
                         "const Kind = z.union([z.literal('alert'), z.literal('digest'), z.literal('invite')]);\n")

    def test_a_member_added_to_a_typescript_string_literal_union(self) -> None:
        self.assertGrows("export type Kind = 'alert' | 'digest';\n",
                         "export type Kind = 'alert' | 'digest' | 'invite';\n")

    def test_a_member_added_to_a_leading_pipe_union_over_lines(self) -> None:
        self.assertGrows("export type Kind =\n  | 'alert'\n  | 'digest';\n",
                         "export type Kind =\n  | 'alert'\n  | 'digest'\n  | 'invite';\n")

    def test_a_member_added_to_a_typescript_enum(self) -> None:
        self.assertGrows("export enum Kind { Alert = 'alert', Digest = 'digest' }\n",
                         "export enum Kind { Alert = 'alert', Digest = 'digest', Invite = 'invite' }\n")

    def test_an_optional_field_added_to_a_zod_object_on_one_line(self) -> None:
        self.assertGrows("const Sent = z.object({ to: z.string() });\n",
                         "const Sent = z.object({ to: z.string(), invitedBy: z.string().optional() });\n")

    def test_an_optional_field_added_to_a_typescript_type(self) -> None:
        self.assertGrows("export type Sent = { to: string };\n",
                         "export type Sent = { to: string; invitedBy?: string };\n")

    def test_an_optional_field_added_on_a_line_of_its_own_with_a_trailing_comma(self) -> None:
        self.assertGrows("const Sent = z.object({\n  to: z.string()\n});\n",
                         "const Sent = z.object({\n  to: z.string(),\n  invitedBy: z.string().optional(),\n});\n")

    def test_a_comment_reworded_is_no_change(self) -> None:
        self.assertGrows(MANDA_BEFORE, MANDA_BEFORE.replace("A reader keeps any other string.",
                                                            "Any other string is kept by a reader."))

    def test_a_member_added_to_a_python_literal(self) -> None:
        self.assertGrows('EmailKind = Literal["alert", "digest"]\n',
                         'EmailKind = Literal["alert", "digest", "invite"]\n', "src/app/domain/intake/events.py")

    def test_a_member_added_to_a_python_enum(self) -> None:
        before = 'class EmailKind(StrEnum):\n    ALERT = "alert"\n    DIGEST = "digest"\n'
        self.assertGrows(before, before + '    INVITE = "invite"\n', "src/app/domain/intake/events.py")

    def test_a_python_docstring_reworded_is_no_change(self) -> None:
        self.assertGrows('def kinds():\n    """The kinds."""\n    return KINDS\n',
                         'def kinds():\n    """Every kind an email may be."""\n    return KINDS\n',
                         "src/app/domain/intake/events.py")

    def test_a_member_added_to_a_go_slice_of_strings(self) -> None:
        self.assertGrows('var EmailKinds = []string{"alert", "digest"}\n',
                         'var EmailKinds = []string{"alert", "digest", "invite"}\n', "internal/domain/intake/events.go")

    def test_a_constant_added_to_a_go_const_block(self) -> None:
        self.assertGrows('const (\n\tKindAlert EmailKind = "alert"\n)\n',
                         'const (\n\tKindAlert EmailKind = "alert"\n\tKindInvite EmailKind = "invite"\n)\n',
                         "internal/domain/intake/events.go")

    def test_a_constant_added_to_a_java_enum(self) -> None:
        self.assertGrows("public enum EmailKind { ALERT, REMINDER, DIGEST }\n",
                         "public enum EmailKind { ALERT, REMINDER, DIGEST, INVITE }\n",
                         "src/main/java/app/domain/intake/IntakeEvents.java")

    def test_a_constant_with_a_value_added_to_a_java_enum(self) -> None:
        self.assertGrows('enum EmailKind {\n  ALERT("alert"),\n  DIGEST("digest");\n',
                         'enum EmailKind {\n  ALERT("alert"),\n  DIGEST("digest"),\n  INVITE("invite");\n',
                         "src/main/java/app/domain/intake/IntakeEvents.java")

    def test_a_record_added_to_a_java_sealed_interface(self) -> None:
        self.assertGrows("sealed interface IntakeEvent permits Sent, Failed {}\n",
                         "sealed interface IntakeEvent permits Sent, Failed, Invited {}\n",
                         "src/main/java/app/domain/intake/IntakeEvents.java")


class RefusedTest(unittest.TestCase):
    """Each form only trunk may take: refused, and the refusal names what the gate saw."""

    def assertRefused(self, before: str, after: str, saw: str,
                      path: str = "apps/app/src/domain/intake/events.ts") -> None:
        found = judged(before, after, path)
        assert found is not None, "refused"
        self.assertIn(saw, found)

    def test_a_member_removed(self) -> None:
        self.assertRefused(MANDA_BEFORE, MANDA_BEFORE.replace(", 'digest']", "]"), "a member removed")

    def test_a_member_renamed(self) -> None:
        self.assertRefused(MANDA_BEFORE, MANDA_BEFORE.replace("'digest'", "'digests'"),
                           "a member or a field renamed (`'digest'` became `'digests'`)")

    def test_a_field_removed(self) -> None:
        self.assertRefused(MANDA_BEFORE, MANDA_BEFORE.replace("  sentAt: z.string(),\n", ""), "a field removed")

    def test_a_field_renamed(self) -> None:
        self.assertRefused(MANDA_BEFORE, MANDA_BEFORE.replace("sentAt:", "deliveredAt:"),
                           "a member or a field renamed (`sentAt` became `deliveredAt`)")

    def test_a_zod_field_made_required(self) -> None:
        self.assertRefused("const Sent = z.object({ to: z.string().optional() });\n",
                           "const Sent = z.object({ to: z.string() });\n", "a field made required")

    def test_a_typescript_field_made_required(self) -> None:
        self.assertRefused("type Sent = { to?: string };\n", "type Sent = { to: string };\n", "a field made required")

    def test_a_python_field_made_required(self) -> None:
        self.assertRefused("    invited_by: str | None = None\n", "    invited_by: str\n", "a field made required",
                           "src/app/domain/intake/events.py")

    def test_a_type_changed(self) -> None:
        self.assertRefused(MANDA_BEFORE, MANDA_BEFORE.replace("sentAt: z.string()", "sentAt: z.number()"),
                           "a type changed")

    def test_a_required_field_added_inside_a_shape_on_one_line(self) -> None:
        self.assertRefused("const Sent = z.object({ to: z.string() });\n",
                           "const Sent = z.object({ to: z.string(), invitedBy: z.string() });\n",
                           "a required field added to a shape events already carry")

    def test_a_member_added_to_a_list_that_excludes(self) -> None:
        self.assertRefused("const Kind = Base.exclude(['alert']);\n",
                           "const Kind = Base.exclude(['alert', 'digest']);\n", "beside `exclude`")

    def test_a_field_made_optional_is_not_a_slice_s_either(self) -> None:
        self.assertRefused("type Sent = { to: string };\n", "type Sent = { to?: string };\n", "a field made optional")

    def test_a_java_record_component_added(self) -> None:
        self.assertRefused("record Sent(String to) implements IntakeEvent {}\n",
                           "record Sent(String to, String invitedBy) implements IntakeEvent {}\n",
                           "cannot read as a new member or an optional field",
                           "src/main/java/app/domain/intake/IntakeEvents.java")

    def test_a_go_struct_field_retyped(self) -> None:
        self.assertRefused("type Sent struct {\n\tAt string\n}\n", "type Sent struct {\n\tAt time.Time\n}\n",
                           "a type changed", "internal/domain/intake/events.go")

    def test_a_widening_beside_a_removal_is_still_refused(self) -> None:
        after = MANDA_BEFORE.replace("'digest']", "'digest', 'invite']").replace("  sentAt: z.string(),\n", "")
        self.assertRefused(MANDA_BEFORE, after, "a field removed")


if __name__ == "__main__":
    unittest.main()
