PATCH

**`/ground`'s long form says what being an application commits you to, before it asks about the first one.**
The question was "is this an application?", and the natural reading of the word is "something that gets
deployed" — so a person could agree to put a directory's lint and tests in front of every change without knowing
that was what they were agreeing to. In the long form the agent now says, once and in this repository's terms,
that an application here is a directory whose build the gate holds: its commands join `make verify`, which every
change has to pass, the person's and `/drive`'s and `/cruise`'s; the gate's CI runs it on every pull request;
`/drive` can change it once somebody has recorded how it starts. It says what declining leaves behind, that
leaving a directory a candidate is *not yet decided*, and that neither answer can be taken back by a command yet —
so an unsure answer is best left open.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.
