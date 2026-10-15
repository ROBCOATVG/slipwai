MINOR

**The interview asks who signs in to the product, once, instead of asking about internal and external
identity separately.** Two axes carry identity — `auth`, the people who run the product, and `users`, the
people it is for — and a product with a staff console behind one issuer and customers in front of another
genuinely has two answers. Both were nevertheless asked of everybody: two prompts a paragraph apart, worded
alike, each offering the same list of providers. Most projects have one login and one set of people, and
for them that was a question with no right answer — picking the same provider twice looked like a
formality and was in fact a request for two realms.

The question is now *Who signs in to this product?*, with three answers: **everyone**, through one identity
provider, which asks once and settles the external axis; **staff**, people who work here and nobody else,
which asks once and settles the internal one; and **separately**, which is the pair, asked exactly as
before. The provider question that follows is headed in the words the answer earned — "Authentication" for
one set of people, "Internal authentication" and "External authentication" for two. Both faces of the
interview ask it: the terminal and the board.

Nothing downstream learned a new word. `--auth` and `--users` are still the flags, still take the same
answers, and a scripted `slipwai generate` is unchanged; a quickstart still answers both axes and the
question shows which of its three shapes that pair is. What the answer settles, it settles for both — the
axis nobody was asked about is written down as having nobody on it rather than left to a default.

**Catch-up:** nothing. This is the interview only; an existing project's answers are untouched, and
`./init` changes either axis as it always did.
