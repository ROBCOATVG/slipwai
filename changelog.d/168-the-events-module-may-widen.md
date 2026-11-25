MINOR

**A slice may widen its context's events module: a new enum member, a new member of a union of literals or
an optional field is no longer refused as a removed line.** `check-slice-scope` held the events module to
"a line may be added, none removed", counted by line, so `z.enum(['alert', 'reminder', 'digest'])` gaining
`'invite'` read as a removed line. manda's S115 was refused for exactly that, could land it no other way,
and parked for good with its fairway's captain. The gate now reads the module as tokens, with comments and
layout dropped, and lets a slice add lines, members of an enum or a union of literals, and optional fields.
That covers TypeScript and zod (`z.enum`, `z.union([z.literal(…)])`, string-literal unions, `enum`,
`field?:`, `.optional()` and `.nullish()`), Python (`Literal[…]`, enum members, unions), Go (literal slices,
`const` blocks) and Java (enum constants, with or without a value, and `permits` lists). A reworded comment
or a reflowed list is no change at all. A member removed or renamed, a field removed, renamed or made
required, a type changed, a required field put inside an existing shape on its line, a member added beside
`exclude`, `omit`, `pick` or `required`, and anything else the gate cannot read as growth are still refused.
The refusal now names which of these it saw, quotes the tokens, and says the rule plainly: *the events
module may only grow on a slice branch*.

A slice parked on that rule now gets its own card on the board. The card names the rule and what the gate
saw, says the change lands on trunk as a commit of its own, and offers **I have landed it, carry on**,
which tells the slice to merge trunk and carry on. It no longer says *a person or the host*. The board has
no button that lands the change itself yet.

**Catch-up:** `slipwai migrate` carries the new `scripts/check-slice-scope.py`. Nothing else changes in a
project: the board's card is the keel's.
