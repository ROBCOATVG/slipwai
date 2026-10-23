# Story split — 001-audiobook-recap

Written by `/launch` (`commands/launch.md`) with nobody at the wheel, from `spec.md` as clarified on
2026-10-21 and the model in `docs/event-model/model.yaml`. On this profile the slices *are* the model's:
every row below is a modelled slice, its id is the model's, and `specs/001-audiobook-recap/chart.yaml` is
rendered from the model by `make chart` — fairway from `context`, marks from the events a slice raises,
`steers_by` from its `reads`. The order of the table is the order of the model's `slices` list, which is
the decision D19 records.

## Parent

A listener who returns to an audiobook after days or weeks away presses play and, in two taps, hears a
spoken "previously on" that covers everything up to their exact position and nothing after it; mid-chapter
they can ask who someone is and get a spoiler-safe spoken answer; while not listening they can browse who's
who so far. Books are added from files or an Audiobookshelf server, prepared in the background into
timestamped text and a who's-who index, and the listener's position is tracked wherever they listen.

## Recommended First Slice

LB3 — Import audio files: a listener imports M4B files and the book appears in their library with its
chapters detected, so preparation (PR1) has something to start on.

Why this first: it is the first step of the walking skeleton import → prepare → request → generate → hear,
which is User Story 1 and 2 (both P1) end to end; `BookImported` is the mark nine other slices steer by, so
preparing it first clears the most siblings; and the phase 1 gate (SC-009) needs no server, no player and no
offer — only a prepared book and a request.

## Split Candidates

Release constraint on every row: `.specify/cruise.json` says `release: flagged`, so every slice merges
behind a flag seeded off and nothing reaches a real listener until a person flips it. *Acceptance Examples*
quotes the worked example the model carries (The Cartographer's Silence, Chapter 14 at 32:10, nine days
away); the example map writes the rest.

| Slice | Value | Includes | Defers | Surfaces and states | Acceptance Examples | Release Constraint |
|---|---|---|---|---|---|---|
| LB3 Import audio files | the listener's own files become a book in their library | M4B/MP3/M4A from the device or a synced folder, chapters from metadata (FR-022), `BookImported` with the content hash | share-sheet and folder-watch (A1), ebook (LB11) | | three M4B files → Nine Winters at Halvard, 31 chapters, 14h 20m, in the library (US2 #1) | flag off |
| LB6 Resume listening | pressing play — or opening a connected book — records the return and starts the gap clock | `ListeningResumed` with the position and days since last listened; the companion-mode return gesture (D7) | the player's controls (FR-032, A1) | | play at Chapter 14 · 32:10 after 9 days → `ListeningResumed` 4:03:17, 9 days (US3 #1) | flag off |
| LB7 Stop listening | the position is kept to the second and the last-listened time recorded | `ListeningStopped` from the player; later-timed position wins (FR-028) | sleep timer, background playback (A1) | | stop at 2h 14m 09s, kill and relaunch → position 2h 14m 09s (US7 #3) | flag off |
| LB8 Enter a position by hand | a book played elsewhere gets a position for recaps | chapter plus minutes (FR-030); refused beyond the chapter's length | | | "Chapter 14, 32 minutes" → position 4:03:17 (US7 #6) | flag off |
| LB1 Connect to an Audiobookshelf server | a self-hoster's library is reachable | URL and token, one connection at a time, renew on rejection (FR-029) | | | connect → library listed; rejected token → "connection needs renewing" (US6 #1, #5) | flag off |
| LB4 Pick a book from the server | a server book is in the listener's library | `ServerBookAdded` with the server item | | | pick The Cartographer's Silence → in the library, preparing (US6 #1) | flag off |
| LB5 Fetch a server book's audio | the audio reaches preparation once | automation: `AudioFetched` with the content hash | | | server book added → audio fetched once, hash sha256:… (US6 #1) | flag off |
| LB9 Adopt the server's progress | the position follows the Audiobookshelf app | translation of server progress; later-timed wins | | | server at 5h 10m → Recap at 5h 10m, gap from the server's last-listened time (US6 #2) | flag off |
| LB10 Push progress to the server | the server follows Recap | automation after stop or manual entry; `ServerSyncFailed` when unreachable (US6 #4) | | | position changes in Recap → server updated; unreachable → last synced position used, said so (US6 #3, #4) | flag off |
| LB2 Change settings | default tier, threshold, voice, data policy are the listener's | `SettingsChanged` (crud) with every value (FR-035) | | | threshold 7 days or off → the offer behaves accordingly (US8 #3) | flag off |
| LB11 Attach an EPUB | better recap text where the listener has the book | align by title and ordinal, unmatched chapters fall back (FR-021); aligning changes the recap cache key (D6) | | | 31-chapter EPUB → 29 aligned, 7 and 22 left to the transcript, told so (US2 #4, edge case) | flag off |
| LB15 Remove a book | the listener can take a book, and everything of theirs about it, out | `BookRemoved`; per-listener erasure, shared transcript stays (FR-043, D11) | account closure (no v1 screen) | | remove → gone from the library, position and caches gone, hash-keyed transcript kept (US9 #3) | flag off |
| PR1 Start preparation | one preparation per content hash | automation on `BookImported` or `AudioFetched`; second identical import joins the first (FR-023) | | | two listeners, identical files → one transcription; the second's recap within a minute (US2 #6) | flag off |
| PR2 Transcribe the next chapter | the book becomes timestamped text, in order, resumably | word-level timestamps, chapter order, lazy up to a little past the furthest position (FR-020, FR-027); failed chapter with reason, English only (D10, D15) | | | chapters 1–4 done → recap works at chapter 3, refused at chapter 9 (US2 #2); chapter 9 fails → "couldn't prepare past Ch. 8", retry (US2 #9) | flag off |
| PR3 Index a chapter's who's who | entries exist the moment a chapter is transcribed | characters, places, terms per chapter; name canonicalisation (FR-018, FR-026) | | | chapter transcribed → its entries indexed to it (US2 #5) | flag off |
| PR4 Discard the audio | nothing of the listener's audio stays server-side | automation on completion, or 7 days after a failure (FR-024, D10) | | | transcription complete → audio gone when inspected (US2 #7) | flag off |
| LB12 See the library | the listener sees their books, how far each is prepared, where they are | fold of books, preparation, positions, server state, failures and removals (FR-025, D10, D11) | | | 3 books; continue listening Chapter 14 of 31, 9 days ago, recap ready; Nine Winters preparing, recap ready up to Ch. 8 | flag off |
| LB14 Watch preparation progress | a listener can tell a slow book from a stuck one | chapter N of M, time left, recap works up to Ch. N, EPUB alignment, failure with retry | | | transcribing chapter 9 of 31, about 25 min left, you can start listening now (US2 Independent Test) | flag off |
| LB13 See now playing | the player screen knows the book, chapter and position | fold of book, chapters, position, alignment | the player's controls (A1) | | The Cartographer's Silence · Chapter 14 · The Harbourmaster · 32:10 | flag off |
| CU1 Choose a voice for a book | recaps and answers speak in the voice the listener picked for this book | `VoiceChosen` per book; cached text re-spoken, never redrafted (FR-034, D3); the picker at `/books/{bookId}/voice` (D24) | the play-sample button, until the speech provider arrives with CU5 (D25); the link from the player (LB13) | | voice Tomas for one book → that book's recaps and answers in Tomas, another book unchanged (US8 #1) | flag off |
| CU4 Request a recap | the listener asks for a recap at their position, from the button or the offer | `RecapRequested` per book, tier and position; a generated key is served from the cache (FR-008, FR-012) | | | Standard at 4:03:17 twice without moving → one generation, the cache the second time (US1 #7) | flag off |
| CU5 Generate the recap | a spoiler-free recap exists for the position, or an honest refusal, or an honest failure | the window (FR-002), draft without title or author (FR-003), gradient and tier within ±15% (FR-005, FR-006, D12), the two-pass check (FR-004, D5), ending sentence (FR-007), refusal (FR-009), failure (FR-042), cache key with content (D6), spoken in the book's voice | the digest for long books (FR-010) where the plan does not need it | | 4:03:17 Standard → 448 words, bands Early · Middle · Recent · Just now, 2 sentences stripped, ends at the Harbourmaster's door (US1 #1–#4); transcript to 2h → refused with why (US1 #8) | flag off |
| CU6 Hear the recap | the listener hears it, sees the band bar and the text, and is handed back to the book | playback state, refusal and failure states, the current voice (D3), Back to Audiobookshelf for a connected book (D18), "Catching you up…" while drafting (D16) | | Recap mock-up · shown | Catching you up — band bar, 1:42 of 3:00, ends at Chapter 14, 32:10, then the book resumes | flag off |
| CU7 Finish the recap | the book resumes exactly where the listener left off | `RecapHeard` on end or Skip; resume where Recap owns playback, else the return prompt (FR-007, D18) | | | recap ends → playback at 4:03:17 (US1 #5); connected book → Back to Audiobookshelf (US6 #7) | flag off |
| CU2 Offer a recap on return | after a gap, the recap is one tap away | automation on the return: gap at or over the threshold in whole days (D13), coverage reached (D2), once per return (D4), default tier recommended (A3) | | | 9 days, threshold 3 → "It's been 9 days. Catch you up?" with three tiers (US3 #1); 2 days → no offer (US3 #4); not prepared to the position → no offer (US3 #8) | flag off |
| CU3 Decline the offer | the listener can say no and just play | `RecapOfferDeclined`; dismissal is a decline (D14); answered once | | | "No thanks" → playback, no recap, no second offer on the next play (US3 #3, #9) | flag off |
| CU8 Rate the recap | the listener says whether it helped | thumbs up or down per recap (FR-037) | | | thumbs up → counted (SC-005) | flag off |
| CU9 Read the recap as text | the words that were spoken, readable | the transcript of a generated recap (FR-039) | | | open transcript → the text as spoken, word for word (US10 #1) | flag off |
| CU10 Ask a question | the listener asks who or what something is, by voice or by typing | `QuestionAsked` at the position; the book pauses (FR-014) | | | "Who is Marcus again?" by voice at 4:03:17 → asked (US4 #1) | flag off |
| CU11 Answer the question | a spoken answer from the window, or an honest not yet | the same window and two-pass check (FR-016), partial answers (edge case), "has not come up" (US4 #4), refusal with no hint (FR-015), failure (FR-042) | | | Marcus introduced before → answer from Ch. 3, 9, 13, spoken; answer lies ahead → "not yet" (US4 #1, #2) | flag off |
| CU12 Hear the answer | the answer plays, the conversation is visible, the book resumes | playback of the answer, refusal and failure states | | | playing answer; "Does Ines ever find the real map?" → Not yet | flag off |
| CU13 Browse who's who | characters, places and terms so far, nothing later | fold of the per-chapter index filtered to the position (FR-017, FR-018) | | | position in chapter 5 → entries from chapters 1–5 only; advance to 7 → 6–7 appear (US5 #1, #2) | flag off |
| CU14 Open a who's-who entry | a longer spoiler-free description and the first appearance | the entry's detail filtered to the position (FR-019) | | | tap Father Oren → longer description, first appeared Ch. 3 (US5 #4) | flag off |
| CU15 Report a spoiler | a listener can say something gave the future away, and someone hears it | `SpoilerReported` against a recap, answer or entry; an alert to the on-call owner within 5 minutes (FR-038, D17) | an operator screen | | report on a recap → recorded, alert raised (SC-002) | flag off |

## Chart

Rendered: `make chart` wrote `specs/001-audiobook-recap/chart.yaml` from the model — three fairways
(`library`, `preparation`, `catch-up`, from D1), 34 marks (one per event the model raises, each pointing at
`docs/event-model/model.yaml` as its typed contract), and these 34 slices with `capability`, `sets` and
`steers_by`. `make check-chart` passes: every mark has one setter, nothing steers by a mark nobody sets,
every slice names its capability.

Capabilities, which are what a person's demo is of: `prepare-a-book` (LB3, LB11, LB15, PR1–PR4, LB12,
LB14), `track-position` (LB6, LB7, LB8, LB13), `audiobookshelf-companion` (LB1, LB4, LB5, LB9, LB10),
`voice-and-settings` (LB2, CU1), `catch-me-up` (CU2–CU9), `ask-about-the-book` (CU10–CU12), `whos-who`
(CU13, CU14), `report-a-spoiler` (CU15).

## Order

D19. Read off `python3 scripts/agents/clearance.py --order`, the story priorities in `spec.md` and the
story-splitting rules (*Order*, *Red flags*). Nothing is above what sets the marks it steers by: `make
check-model` holds that through `reads`, which must name events an earlier slice raises.

| Row | Why here |
|---|---|
| LB3 | the walking skeleton's first step; `BookImported` is steered by 9 slices, more than any other library mark; the import is the product's door, not the server connection (the *infrastructure first* red flag argued against LB1 here) |
| LB6, LB7, LB8 | track-position next: `ListeningResumed` (6 steerers) is what the offer and the lazy transcription read, and a position is what every recap is at; LB7 and LB8 after LB6 by the capability's own order |
| LB1, LB4, LB5, LB9, LB10 | audiobookshelf-companion together, after the position slices because LB10 steers by LB7 and LB8; LB5 after LB1 and LB4 (it steers by both); LB9 before LB10 as the inbound sync before the outbound |
| LB2 | settings after the things it tunes (US8: "every default works without them"); before PR1 only because PR2 reads `SettingsChanged` |
| LB11, LB15 | the rest of prepare-a-book in the library: the EPUB (a PRD P1 follow-on) and removal (a gap the review found) are the two that nothing in the skeleton waits on |
| PR1–PR4 | preparation in its own order: start, transcribe, index, discard; PR3 and PR4 steer by PR2 |
| LB12, LB14, LB13 | the three views, after the writes they fold; LB12 and LB14 are prepare-a-book and stay together; **unsure** — nothing but the capability distinguishes LB13's place |
| CU1 | voice first in catch-up only because CU5 reads `VoiceChosen`; it is a small slice and nothing else of voice-and-settings is in this fairway |
| CU4, CU5, CU6, CU7 | the engine: request → generate → hear → finish is User Story 1 (P1) and the phase 1 gate; it comes before the offer (US3, P2), which sits on top of it |
| CU2, CU3 | the offer and its decline, the rest of catch-me-up |
| CU8, CU9 | rating and the transcript; **unsure** — the order between them is arbitrary |
| CU10–CU12 | ask-about-the-book, after the engine it reuses (FR-016) |
| CU13, CU14 | who's who, which steers by `ChapterIndexed` and the positions and nothing in catch-up |
| CU15 | the report, last: it names any of the three and steers by nothing |

## Fairways

Read from `specs/001-audiobook-recap/chart.yaml`'s `fairways` block (rendered from the model's `context`
and `service`), one bounded context each per D1. `held_by` is rendered from `refs/slipwai/claims/<fairway>`
by `make decisions` and is never typed; this checkout has no `origin`, so every row reads `—`.

| Fairway | Context | Slices, in split order | held_by | Notes |
|---|---|---|---|---|
| library | library | LB3, LB6, LB7, LB8, LB1, LB4, LB5, LB9, LB10, LB2, LB11, LB15, LB12, LB14, LB13 | — | 15 slices, serial behind one captain; D1 says why it is not split (FR-029 cascades across connection, server book and position) |
| preparation | preparation | PR1, PR2, PR3, PR4 | — | its own actor and schedule; steers by the library's import and position marks |
| catch-up | catch-up | CU1, CU4, CU5, CU6, CU7, CU2, CU3, CU8, CU9, CU10, CU11, CU12, CU13, CU14, CU15 | — | 15 slices; D1 says why it is one context (one window, one check, one refusal, one report) |

## Slice graph

Genuine build dependencies only. The model declares no `depends_on` on any slice: every cross-slice need is
an event another slice raises, and Principle V seeds those from synthetic events in tests. So the ready set
is the whole split from the start, and what actually sequences the work is clearance — a slice starts
preparing when the marks it steers by have been set by a sibling that planned (`python3
scripts/agents/clearance.py`), which the chart's `steers_by` carries row by row.

| Slice | depends_on | parallel_ok_with | Notes |
|---|---|---|---|
| LB3, LB6, LB7, LB8, LB1, LB4, LB5, LB9, LB10, LB2, LB11, LB15, LB12, LB14, LB13 | — | each other | share the library's streams by id and the events module additively; one fairway, so they merge in split order |
| PR1, PR2, PR3, PR4 | — | each other | one stream `preparation-{audioHash}`; steer by the library's marks, which clearance reads |
| CU1, CU4, CU5, CU6, CU7, CU2, CU3, CU8, CU9, CU10, CU11, CU12, CU13, CU14, CU15 | — | each other | steer by the library's and preparation's marks; CU5, CU11, CU13 wait on `ChapterIndexed`/`ChapterTranscribed` being planned, not merged |

## Parking Lot

- The nice-to-have gaps the review parked, each to the slice that first meets it: the position at which
  SC-006's ten minutes is measured (PR2); a same-listener re-import of an identical hash (LB3, PR1 —
  closed by D22: a new `bookId` is a new book); the
  "recap off" cohort SC-004 compares against (CU2 — a product question for a person); a spoken question
  that cannot be recognised (CU10); manual minutes beyond the chapter (LB8 already refuses it).
- Who the on-call owner is for spoiler alerts (D17): `unavailable`; the plan for CU15 wires the alert to a
  destination a person names.
- The three entries awaiting human confirmation: D1 (the contexts), D8 (recaps per book, not per hash),
  D15 (English only), D19 (this order) — posted as `question` lines on the library deck log.
- FR-010's running digest for long books is modelled inside CU5 and deferred until a plan finds the window
  too large for one draft.
- The standalone player's controls, the share sheet and folder watching (US7, FR-032, FR-033) are A1's
  phase 3 packaging and have no slice; `LB6`/`LB7` carry the position events the browser player raises.

## Warnings

- `mockups/mock-states.md` was approved by the board (`upstream: advance`) as one surface, `Recap mock-up`,
  seven times, rather than the seven screens the storyboard draws. `make check-surfaces` therefore reads
  one approved state, `Recap mock-up · shown`, which exactly one slice must deliver: it is on CU6, the
  storyboard's hero screen. The model carries the real screen-to-slice mapping on each ui frame's
  `mockups:` (`add-book`, `library`, `player`, `catch-up-offer`, `recap-playing`, `ask`, `whos-who`), which
  `make check-model` holds. A person who wants the seven states approved by name should rewrite
  `mock-states.md` with a heading per surface; this split then needs its *Surfaces and states* column
  redistributed, and nothing else changes.
- No slice is a component: every row names the Listener, Preparation or the Audiobookshelf server, a
  trigger and an observable outcome. The views (LB12, LB13, LB14, CU6, CU9, CU12, CU13, CU14) are
  state-view slices with a screen, not "build the frontend".
- Two fairways of fifteen are long for one captain each; D1's *Why not split* carries the reason, and
  nothing here changes it.

## Next Step

Clearance: `python3 scripts/agents/clearance.py` names the first ready set. Every slice steering by nothing
is *preparation-ready* at once — LB3, LB6, LB7, LB8, LB1, LB4, LB9, LB2, LB11, LB15, CU1, CU4, CU7, CU3,
CU8, CU10, CU15 — and the rest clear as their setters plan. `/launch` enables `/cruise` and casts off; the
captains claim from here. No slice is claimed by the launch.
