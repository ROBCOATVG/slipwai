# Strategy playbook: leave-it

Leave-it means deliberately not modernising: the system is kept as it is, and only what security and the business
strictly require is done. It is a decision with an owner, an expiry date and a list of accepted risks, not the
absence of a decision. The rule it imposes on a new feature: under retain, a feature lands only if it clears the
leave-it bar (additive, one slice, no new dependency, ingress or schema change, risk acknowledged); under the
sunset variants, features are declined.

---

## 1. What it is

Leave-it covers three variants. They share one rule: **the architecture is not changed**. They differ in where
the system is heading.

| Variant | Industry names | Where it is heading | Feature work |
|---|---|---|---|
| **retain** | AWS *Retain* ("not ready to migrate… might migrate in the future"); Gartner TIME *Tolerate* ("accept the application in its current state for the time being") | Nowhere yet. Re-decided at each review. | Allowed if it is small; see section 4 |
| **sunset-by-date** | AWS *Retire*, TIME *Eliminate* | Switched off on a date. Data is archived or exported first. | Only what is needed to keep running or to get the data out |
| **sunset-to-product** | AWS *Repurchase* ("drop and shop"), TIME *Migrate* to a bought product | Replaced by a SaaS or COTS product. The legacy code is frozen until the cut-over. | None. Requests go to the product's backlog. |

LeanIX calls Tolerate "a stay of execution pending appeal". The status is temporary and is meant to be
re-evaluated. The NCSC says the same about obsolete products: "You should revisit this decision regularly." That
review is the main thing the method adds to leave-it.

### When it is right

- **Low business value, or value that is falling** (TIME: low functional fit). Few users, internal only, a
  shrinking user base.
- **Low change rate.** The backlog is empty or nearly empty, and no change trigger is recorded. slipwai's
  recommender already returns `leave-it` when `why` names no problem.
- **A replacement is coming.** A vendor SaaS release, an org-wide platform programme, or a merger. AWS lists
  "plans to migrate to SaaS" and "dependencies — migrate other apps first" as reasons to retain.
- **The cost of modernising is higher than the cost of the risk** for the review period, and the risk has been
  written down and accepted by someone with authority to accept it (NIST SP 800-37: the authorizing official
  "explicitly accepts the risk").
- **Its exposure can be cut.** The system can be isolated or virtually patched, so the risk that is left is
  actually tolerable.

### When it is wrong (warning signs)

- **The system is internet-facing on an end-of-life runtime and has known remote-code-execution CVEs, and
  nothing can stand in front of it.** CISA lists unsupported software as its first *Bad Practice* and calls it
  "especially egregious in technologies accessible from the Internet". Leave-it with no security floor is the
  reckless/deliberate quadrant of Fowler's technical-debt model.
- **Feature requests keep arriving.** If the backlog is growing, the system has high business value. That puts it
  in TIME *Invest* or *Migrate*, not *Tolerate*. Three or more feature requests in a review period is a trigger.
- **Only one person knows how it works**, and that person is leaving.
- **Regulated data** (PII, financial, health) with no compensating control for the out-of-support stack.
- **"We'll decide later"** with no review date. That is not leave-it. It is forgetting.

---

## 2. What the ADR records

The strategy ADR (`Strategy: leave-it`, accepted by a human) must carry these lines before work starts. slipwai
already parses `Freeze:` this way: "both are answers; only silence is not". The leave-it equivalents are:

```
Strategy: leave-it
Variant: retain | sunset-by-date 2027-06-30 | sunset-to-product <product>
Why: <the business reason: low value / replacement coming / cost of change > cost of risk>
Risk-owner: <a named person with authority to accept risk, not "the team">
Review: 2027-04-30 (at most 6 months out; 3 if internet-facing on an EOL stack)
Review-triggers: new CVE scored 9.0+ in a pinned component; incident; 3rd feature request in a period;
                 owner or last maintainer leaves; host/OS/DB support ends; audit finding; sunset date slips
Accepts: <each accepted risk on its own line, e.g. "end-of-life runtime, no vendor patches">
Compensating: <one control per accepted risk, e.g. "WAF rule set blocking the known exploit shapes in front of the app">
Target: as-is — the shape is not changed while the system is left (target-shape.md)
Features: minimal — <the bar, see section 4> | none (sunset)
```

Why each line matters:

- **Variant** decides what feature requests do and whether a sunset plan exists at all.
- **Why** is the business reason a later review tests: if it no longer holds, the strategy changes.
- **Risk-owner** is NIST's authorizing official in plain words. If the person is not named, nobody has accepted
  the risk.
- **Review** is a date. **Review-triggers** are events that bring that date forward.
- **Accepts / Compensating** come in pairs. This mirrors a NIST risk response: accept the residual risk,
  mitigate with compensating controls, and track the weaknesses in a POA&M-like register (section 5, Ledgers).
  An `Accepts:` line with no `Compensating:` line is allowed only if it says `none — <why tolerable>`.
- **Target** is `as-is`: there is no target shape to move toward while the system is left.
- **Features** names the bar a feature request is classified against (section 4), or `none` for a sunset.

### Choosing the variant

Pick **retain** when there is no date or product yet and the decision will be re-made at each review. Pick
**sunset-by-date** when the system is to be switched off and its data archived. Pick **sunset-to-product** when a
bought product will replace it; the legacy code is then frozen until the cut-over.

### Review date and triggers

The review date is at most six months out, three if the system is internet-facing on an end-of-life stack. The
output of a review is an ADR edit (a new `Review:` date plus a review-log entry) or a new ADR that supersedes this
one with a different strategy. Any trigger in `Review-triggers:` brings the review forward, and a redirected
feature request (section 4) is itself a trigger, because it is evidence of rising business value.

---

## 3. Phases

### Phase 0: make the old system safe

**0.1 Survey and characterise the system's exposure.** `slipwai adopt` and `/survey` build the convergence map.
They also record exposure: whether the app is internet-facing, who uses it, what data classes it holds, and which
components are end-of-life with which CVEs.
- Who: agent drafts it. A human confirms the exposure facts, because only a human knows the network.
- Evidence: `survey/` holds the platform record (products, versions, end-of-life status) and an `exposure` note
  covering ingress, users and data classes.
- Unblocks: the risk lines in the ADR (Phase 1). Nobody can accept a risk that has not been named.

**0.2 Quick win: secrets out of the tree.** Done now, whatever the strategy. Rotate every committed credential
first, then move each one to the environment or a secret store, then purge or accept the git history. Rotating
first matters: purging history does not un-leak a secret.
- Who: agent writes the slice. A human rotates the real credentials (database password, mail, API keys).
- Evidence: the secret scan in `make verify` is clean on HEAD. Each rotation is recorded in the risk register with
  a date. Config reads each credential from the environment or the secret store, never a literal.
- Unblocks: everything else. A repo with live secrets in it is not "left", it is leaking.

**0.3 Build floor, pinned** (`build-floor.md`). The build meets the floor's eight criteria with the target unchanged; the toolset is brought current only where that does not change what is produced. The build declares its dependencies: every library is pinned by name and version in a
manifest or lock file, with the same runtime target as today. A build that copies unversioned libraries from a
folder is moved to the ecosystem's declarative build tool without changing what it produces. This is the least
the method holds any repository to, because without it no CVE audit is possible.
- Who: agent.
- Evidence: the dependency manifest exists. The new build produces an artifact whose contents match the old one
  (a diffed file list). `make verify` builds through the new build.
- Unblocks: the dependency audit in Phase 2, and any later strategy change.

**0.4 Minimal safety net.** No test suite for the whole app; just enough net to make a small change safely. A
boot check (the `run` pacing: the app starts and the home page returns 200), plus `/characterise` pins on whatever
a given change touches. Characterisation tests capture current behaviour, including any bugs.
- Who: agent; the pins are written per change.
- Evidence: a smoke target in `make verify` starts the container, GETs `/`, and asserts 200 and a known marker.
  Characterisation tests sit next to the touched code.
- Unblocks: any change in Phase 3. No feature slice merges without a boot check and pins on the touched code.

### Phase 1: decide and record the risk

**1.1 Decide and accept the ADR.** `/ground` proposes the strategy. A human edits it to `leave-it`, fills in the
section 2 lines, and accepts it. An agent never accepts it.
- Who: human (the risk owner, or someone acting for them).
- Evidence: the ADR has `## Status Accepted`, `Strategy: leave-it`, and non-empty `Risk-owner:`, `Review:` and
  `Variant:` lines.
- Unblocks: programme pacing switches to leave-it. Platform and rungs are recorded, not scheduled.

**1.2 Open the risk register.** One row per `Accepts:` line, each linked to its `Compensating:` control (see
section 5, Ledgers).
- Who: agent drafts the rows from the ADR and the survey; the risk owner confirms them.
- Evidence: `adopt/risk-register.md` (or `docs/risks.md`) exists with a row for every `Accepts:` line.
- Unblocks: the security-floor slices in Phase 2, which are generated from these rows.

### Phase 2: security floor

This is where leave-it differs from neglect.

**2.1 Close each accepted risk with the cheapest control that works.** Per accepted risk, choose the cheapest of
the following that actually closes the exposure:
- *Patch within the line.* A dependency bump that does not change the architecture, such as a security release
  within the same framework major version, or a newer database driver. This counts as security work, not
  modernisation: "platform: only what security requires" can still mean a bump.
- *Virtual patch.* OWASP: "a policy enforcement layer that blocks and logs attempts to exploit a known
  vulnerability" without touching code. For a web framework with a published RCE history, this is a WAF or
  ModSecurity rule matching the exploit shape on the vulnerable headers or parameters named in each advisory.
  Patch "only known issues… focus on the affected page or parameter".
- *Reduce exposure* (NCSC obsolete-products guidance): take it off the internet (VPN or an SSO-fronted reverse
  proxy), zone the network, strip non-essential services, and treat the host as untrusted.
- *Detect and respond.* Access logs shipped off the host, alerts on 5xx spikes and WAF blocks, and a tested
  restore from backup.
- Who: agent writes the config slices (proxy, WAF rules, dependency pins). A human or the infra owner applies
  network changes.
- Evidence: the register has, per CVE: ID, component, status (`patched` / `virtual-patch` / `isolated` /
  `accepted`), control reference, and date verified.
- Unblocks: the risk owner can honestly sign each `Accepts:` line.

**2.2 Ratcheted dependency audit in the gate.** The dependency audit (for example OWASP Dependency-Check, or the
ecosystem's own audit tool) runs in `make verify` with a ratchet baseline: known CVEs are listed, and new ones
fail the gate.
- Who: agent.
- Evidence: the audit step in `make verify` and its baseline file.
- Unblocks: detection of the "new critical CVE" review trigger.

**2.3 Prove each virtual patch.** A test or `curl` probe sends the exploit shape and expects it to be blocked.
- Who: agent.
- Evidence: the probe in the gate or in a scheduled job; the register row's `last-verified` date.
- Unblocks: catching virtual-patch rot (section 6).

### Phase 3: keep the lights on (review cadence)

**3.1 Handle changes within the bar.** Feature requests are classified and handled as section 4 describes.
- Who: draft agent classifies; a human accepts the spec.
- Evidence: each spec carries a `Strategy-fit:` line.
- Unblocks: small changes ship without changing the strategy.

**3.2 Keep the register current.** New CVEs from the audit, feature risk acknowledgements and rotation dates are
added as they happen.
- Who: agent.
- Evidence: register rows dated within the current review period.
- Unblocks: an honest review.

**3.3 Hold the review.** On the `Review:` date, or earlier on a trigger, the risk owner reviews the strategy and
records the decision: keep, move to a sunset variant, or change strategy.
- Who: the risk owner holds it; the agent prepares the triggers seen and the register state.
- Evidence: a review-log entry (date, attendees, triggers seen, decision) and either a new `Review:` date in the
  ADR or a superseding ADR.
- Unblocks: continued leave-it. An overdue review turns the adoption back to *unfinished*.

### Phase 4: sunset (sunset variants only)

**4.1 Inventory the data.** List each business object, its owner, retention period and the regulation behind it
(IBM decommissioning practice).
- Who: agent drafts from the schema; the data owner confirms.
- Evidence: the data inventory in `docs/sunset.md`.
- Unblocks: the export.

**4.2 Export and archive.** Use an open format (CSV/JSON plus a schema description, or a database backup plus a
read-only restore runbook). Verify the archive: row counts reconcile and a sample is read back before anything is
deleted ("export and archive first… delete only after confirming").
- Who: agent writes the export; a human verifies the sample.
- Evidence: archive location and checksum, and a reconciliation report, in `docs/sunset.md`.
- Unblocks: switch-off. Nothing is deleted before this is ticked.

**4.3 Communicate.** Announce to users at T-90, T-30 and T-7 days. Put a banner in the app. Name where the data
went. Remove user access on a recorded date.
- Who: human (the risk owner or the business owner); the agent writes the banner slice.
- Evidence: the comms log in `docs/sunset.md`.
- Unblocks: decommissioning.

**4.4 Decommission.** Freeze writes (read-only mode), then switch off, revoke credentials, delete hosts and DNS,
archive the repo, and record legal retention of the archive.
- Who: human or infra owner; the agent writes the read-only slice and the final ADR.
- Evidence: the switch-off date in `docs/sunset.md`, an archived repo, and a final ADR (`Superseded:
  decommissioned <date>`).
- Unblocks: the finish line.

### Finish line

- **retain:** the review is in date and every accepted risk has a control (no register row is `open` without
  one). This is never permanent: it stops being true the day the review lapses.
- **sunset variants:** the system is switched off and the data archived, with a verified archive and a final ADR.

---

## 4. How a feature request is handled

Every feature request is first classified against the ADR's `Features:` line.

**retain (minimal): allowed if it meets every criterion of the bar.**
- It is additive: a new handler, view or query, with no change to shared code paths beyond one wiring line.
- It adds no new dependency and no framework or runtime bump.
- It adds no new ingress: no new public endpoint, file upload, or form that passes free text into the parts of
  the framework with known flaws.
- It changes no schema, or only adds something that can be reverted (a view or a nullable column).
- It is roughly 1-3 days of work or under ~300 changed lines, and fits in one slice. A plan that needs a second
  slice fails the bar.
- It ships behind the same gate: the boot check plus pins on touched code.
- It states its own risk, and the risk owner acknowledges it with one line in the register.

**What the spec must state.**
- `Strategy-fit: within leave-it bar` with each criterion ticked, or `Strategy-fit: redirected — review
  triggered`.
- `Risk:` what it adds: new surface, new data, new dependency, each "none" or named.
- `Pins:` the code paths `/characterise` must cover before the slice changes them.

**Redirected, not silently enlarged.** A request that fails the bar is not quietly shrunk or grown to fit. The
spec is written as "out of scope under leave-it", and the request counts as a review trigger. The board posts a
question to the risk owner: change strategy, or decline the request.

**Sunset variants: declined.** Except for what is needed to export data or tell users about the switch-off. The
request is logged against the replacement (for sunset-to-product, the product's backlog).

**Who:** the draft agent classifies, the spec records it, and a human accepts the spec.

**Visibility rule:** not applicable. Leave-it has no new system for a feature to land in, so there is no page,
seam or cut-over choice to make.

---

## 5. How the method carries it (proposed — not built yet)

### Adoption sequence on the board

1. `adopt`, then survey, then the map, then the gate (with the ratchet). Unchanged.
2. `/ground` writes the ADR at Proposed. The human sets `Strategy: leave-it`, fills in the section 2 lines, and
   accepts. The board should **refuse "accepted" while `Risk-owner:`, `Review:` or `Variant:` is empty**, just as
   `Freeze:` is required under a strangler.
3. Programme: quick wins (secrets), then build floor (declared dependencies), then the security-floor slices (one
   per accepted CVE cluster: audit in gate, virtual patch, isolation), then the boot check. Platform and rungs show
   as *recorded, not scheduled*, each linked to the `Accepts:` line that covers it.
4. Only then does the first feature spec get drafted.

### Draft, spec and mock-ups

- `draft` classifies the request against the bar and writes `Strategy-fit:` into the spec. If the request fails
  the bar, the draft does not shrink it quietly. It writes the redirect and raises the review trigger.
- The spec carries the `Risk:` and `Pins:` sections described in section 4.
- Slices are capped at one for a leave-it feature.
- Mock-ups: leave-it adds no rule of its own. A feature within the bar changes at most one view of the existing
  app, so any mock-up is of that view as it is today.

### Constitution

The constitution gets a *Strategy* clause copied from the ADR (variant, feature bar, review date), with these
lines:
- "This system is left: its architecture, runtime and framework major version do not change except where the risk
  register says security requires it."
- "No new dependency, endpoint type or schema change without the risk owner's line in the register."
- "Every change ships with the boot check green and pins on touched code."
- "The strategy is reviewed by <date> or on <triggers>. An overdue review blocks feature slices but not security
  slices."

### Gates

- `make verify` = build + ratcheted lint + **ratcheted dependency audit** (new CVEs fail) + secret scan + boot
  check + characterisation tests (+ the virtual-patch probes).
- `check-convergence` (or the strategy record) treats leave-it as **finished only while the review is in date and
  the register has no `open` row without a control**. Today `strategy.py` marks leave-it `finished` as soon as it
  is decided (`decided == "leave-it"`), which is exactly how a leave-it gets forgotten.
- The review date: the board shows a countdown and opens a review task at T-14 days.
- Trigger events the agent can detect: the audit finds a new critical CVE; a third feature request in the period
  (or any redirected request); the `Variant:` sunset date passes; the map shows the last committer to touched
  code is gone (from git log); a host or database product reaches end-of-life in the platform record.
- A diff check: a dependency-manifest version change in a slice whose spec says `Strategy-fit: within bar` fails
  review.

### Programme pacing

- quick-win: now. Build: first. Run/boot check: before any slice touches code.
- platform: "only what security requires", made concrete as *security-floor slices generated from the
  `Accepts:`/CVE rows*, which are scheduled. The rest of the platform stays recorded.
- rungs: not scheduled; recorded.

### Ledgers

- **Risk register** (`adopt/risk-register.md` or `docs/risks.md`): one row per accepted risk with risk,
  likelihood/impact, control, owner, last-verified date and status; per CVE, also ID, component and control
  reference. It is modelled on a NIST POA&M: "tracked weaknesses with owners and remediation dates". Credential
  rotations and feature risk acknowledgements are recorded here too.
- **Review log**: each review records date, attendees, triggers seen, and decision (keep / move to sunset / change
  strategy). A log entry dated within the last cycle supersedes an older `Review:` date.
- **Sunset ledger** (sunset variants only): inventory, archive, verify, communicate, switch off, kept in
  `docs/sunset.md`. It is the counterpart of the strangler's retirement ledger, and the `switch-off` row cannot be
  ticked before the reconciliation report exists.

---

## 6. Anti-patterns and how the method detects each

| Anti-pattern | Detection |
|---|---|
| **Leave-it as neglect**: no owner, no date | ADR acceptance refused without `Risk-owner:`/`Review:`; strategy record is unfinished when the review is overdue |
| **Leaving live secrets** | Secret scan in gate; quick-win slice is first in the programme whatever the strategy |
| **Accepting a CVE with no control** | Register row `accepted` without `Compensating:`/`none — why`, so convergence is unfinished |
| **Feature creep**: leave-it in name, invest in practice | Count of feature specs per review period; `Strategy-fit:` redirects; more than one slice per feature fails the bar |
| **Stealth modernisation**: "while we're here" framework bumps inside a feature slice | Diff check: a dependency-manifest version change in a slice whose spec is `Strategy-fit: within bar` fails review |
| **Virtual patch rot**: WAF rule removed or the proxy bypassed | Probe test in the gate or a scheduled job proving the exploit shape is blocked; register has a `last-verified` date |
| **Unverified archive** before switch-off | Sunset ledger requires a reconciliation report before the `switch-off` row can be ticked |
| **Sunset date slips silently** | Date passed with the system still live is a review trigger; the board flags it |
| **Knowledge loss** | Pins plus `survey/structure.md` stand in for tribal knowledge; a "last maintainer leaves" trigger |

---

## 7. Worked example: an internal booking app

**Facts.** An internal room-and-equipment booking web app, a few thousand lines, on an end-of-life runtime and a
web framework major version that no longer gets security releases. The scanner lists several known CVEs in the
framework, two of them unauthenticated remote code execution. Database and mail credentials are committed in
config files. There are no tests. About 200 staff use it; it changes once or twice a year; the organisation plans
to move booking to a bought workplace product within 18 months.

**Will the recommender pick leave-it?** Probably not. An end-of-life runtime matches the "platform behind" path,
so `/ground` proposes `in-place`. Leave-it is a deliberate human override, and that is the point: the ADR must say
why.

**ADR (example)**
```
Strategy: leave-it
Variant: retain
Why: internal only, ~200 users, ~2 changes a year; a bought booking product is planned within 18 months
Risk-owner: <named head of facilities>
Review: 2027-04-30   (6 months: internal only, behind SSO)
Review-triggers: new CVE scored 9.0+ in the framework or runtime; any incident; 3rd feature request this period;
                 database or host OS support ends; product decision made
Accepts: end-of-life runtime unpatched — Compensating: reachable only via the SSO reverse proxy; outbound egress denied
Accepts: framework RCE CVEs (per scanner) — Compensating: last security release in the same major version if it
         builds on the current runtime [security-floor slice]; until then WAF rules on each advisory's exploit
         shape; probe test in gate
Accepts: no automated tests — Compensating: boot check + /characterise pins on touched code
Target: as-is
Features: minimal — additive, one slice, no new dependency/ingress/schema change, risk line acknowledged
```

**Programme on the board**
1. *Quick win:* rotate the database and mail credentials, move them to the environment, and add a secret scan to
   the gate. Evidence: clean scan, rotation dates in the register.
2. *Build floor:* declare and pin every dependency, same runtime target. Evidence: the artifact file-list diff is
   empty.
3. *Security floor:* a dependency audit in the gate with today's CVEs baselined. Then a decision slice: does the
   framework's last security release in this major version run on the current runtime with the app unchanged? If
   yes, bump (a within-line patch, not modernisation). If no, apply the WAF rules and keep anonymous traffic out
   with the SSO proxy. Add a probe test: a request carrying the exploit shape gets 403.
4. *Run:* a smoke target that boots the app in a container and asserts that `/` returns 200 with the login marker.
5. Platform (supported runtime, current framework) and rungs (pipeline, packaging) are **recorded, not
   scheduled**, each pointing at its `Accepts:` line.

**A request that passes the bar: "a reminders panel on the home page"**
- *Classification:* additive (one read-only query over existing bookings for the signed-in user, one view
  fragment, one handler change). No new dependency, no new ingress (no form input), no schema change. **Within the
  bar.**
- *Spec carries:*
  - `Strategy-fit: within leave-it bar` with each criterion ticked.
  - `Risk:` no new surface. It shows users only their own bookings, behind the existing login, and the risk owner
    acknowledges this. Edge cases (cancelled bookings, time zones) are decided, and a `QUESTION` is posted if one
    is unknown.
  - `Pins:` characterise the current home page output before the change. A unit test covers the date window (next
    7 days, across a month and year end).
  - One slice, gate green (build + audit ratchet + secret scan + boot + pins).

**A request that fails it: "a new file-upload endpoint for floor plans"**
- New ingress: a multipart upload handled by a framework with a published RCE history in exactly that path. It
  fails the bar. The spec is written as a redirect, the review is brought forward, and the risk owner is asked
  whether this is now an *Invest* system (in-place upgrade) or a request for the bought product.

---

## 8. Sources

- AWS Prescriptive Guidance, migration strategies (Retain, Retire, Repurchase):
  https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html
- AWS, assessing applications to retire:
  https://docs.aws.amazon.com/prescriptive-guidance/latest/migration-retiring-applications/
- LeanIX, Gartner TIME "Tolerate": https://www.leanix.net/en/blog/gartner-time-tolerate
- LeanIX, Gartner TIME model overview: https://www.leanix.net/en/wiki/ea/gartner-time-model
- Xebia, TIME and application portfolio quality:
  https://xebia.com/articles/how-to-assess-and-improve-the-quality-of-your-application-portfolio/
- NCSC (UK), managing obsolete products:
  https://www.ncsc.gov.uk/collection/device-security-guidance/managing-deployed-devices/obsolete-products
- NCSC (NL), "Software has an expiry date":
  https://english.ncsc.nl/publications/factsheets/2019/juni/01/factsheet-software-has-an-expiry-date
- NCSC (NZ), Use of Supported Products:
  https://www.ncsc.govt.nz/assets/NCSC-Documents/Advisory-Use-of-Supported-Products.pdf
- CISA, Bad Practices (unsupported/EOL software): https://www.cisa.gov/stopransomware/bad-practices
- NIST SP 800-37 Rev. 2 (RMF; authorization as explicit risk acceptance): https://csrc.nist.gov/pubs/sp/800/37/r2/final
- NIST glossary, authorization: https://csrc.nist.gov/glossary/term/authorization_to_use
- SC World, writing a risk acceptance record:
  https://www.scworld.com/tech-explainer/writing-a-risk-acceptance-record-the-accepting-executive-can-sign
- OWASP Virtual Patching Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Virtual_Patching_Cheat_Sheet.html
- OWASP Virtual Patching Best Practices: https://wiki.owasp.org/index.php/Virtual_Patching_Best_Practices
- Martin Fowler, Technical Debt Quadrant: https://martinfowler.com/bliki/TechnicalDebtQuadrant.html
- Decommissioning practice: HUD decommissioning guide https://www.hud.gov/sites/documents/decomv3.pdf ;
  Alberta, information handling when decommissioning
  https://imtpolicy.sp.alberta.ca:443/procedures/pdf/Information%20Handling%20When%20Decommissioning%20Systems%20and%20Applications-REVISED.pdf ;
  IBM application decommissioning https://public.dhe.ibm.com/software/de/virtual_shopping/Teaser_Application_Decommissioning.pdf ;
  Victoria FFM formal EOL plan https://opendocs.ffm.vic.gov.au/main/emap/05.4
