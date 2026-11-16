# Evals for the captain's decisions

The captain is becoming an agent, and the agent makes four decisions that a fixed rule makes today
(`docs/captain-agent-plan.md`, decisions 15–22). These are the decisions:

1. which cleared slice starts next;
2. after a failed gate, whether to retry and with what note, or to park and with what reason;
3. which slices a message from a person is for;
4. what to do about a stuck slice: nudge it, interrupt it, park it, or tell the person.

An **eval** puts a moment that really happened to the real agent, through the project's own harness, several
times. It then scores the order the agent gives against the orders a person would accept.

**An eval is not a test.** A test proves that code does what it must, and a test failing stops a merge. An
eval measures how often an agent's judgement matches a person's. An eval never gates anything. You run it
when you choose to, or nightly. **Its score is advice.** A low score is a reason to read what the agent wrote,
and maybe to change its brief. It is never a reason to refuse a merge.

## Where the evals live, and why

- `evals/captain/cases/<decision>/<name>.json` holds the cases, one file for each moment. `<decision>` is
  the kind of event that asks for the decision: `choose-next`, `gate-failed`, `message` or `stuck`.
- `scripts/evals.py` runs the evals. The modules beside it do the rest: `eval_cases.py` reads a case and
  lays it out, `eval_score.py` judges orders, and `eval_captains.py` starts the captain under test.
- `evals/captain/runs/<stamp>/` holds what a run wrote: every order, and the report. Git ignores this
  folder.

The evals sit at the root, beside `tests/`, and they are not inside `tests/`, because an eval is not a test
and the suite must never call an agent. They are not under `assets/` because nothing in a generated project
runs them. They judge the toolkit's captain from the keel's own repository, in the same way as `scripts/`
tooling.

## A case

A case is one JSON file that a person can read from top to bottom:

| Key | What it holds |
|---|---|
| `situation` | Two or three sentences about what was going on. Read this first. |
| `source` | Where the moment came from. It contains no names, paths or addresses. |
| `snapshot` | The stream at that moment. `feature` and `fairway`. `slices`: each slice's state, in a few words. `deck` and `harbour`: the log lines that matter, as the logs hold them. `activity`: the last lines of a slice's activity log. `gate`: the refusal text. `said`: what the person told the stream. `slots`: the free session slots. |
| `event` | What wakes the captain, in the shape that contract 2.2 gives. If `facts` is left out, it is the snapshot. If `may` is left out, it is the decision's usual list. |
| `label` | `accept`: the orders a person would accept. `wrong`: the orders that would be plainly wrong. `why`: one sentence. `signed_off`: who confirmed the label. `note`: anything else. |

An order in `accept` or `wrong` is a **pattern**. A pattern has a `verb`, or a list of verbs that each count,
and at most one of these four keys:

- `slice`: the one slice that is named.
- `slices`: exactly this set of slices. Routing is scored this way, so the order of the slices does not
  matter.
- `within`: at least one slice, and none from outside the list.
- `naming`: any answer that includes this slice. Use it for "starting LB4 at all is wrong".

A `message` order with `--interrupt` is scored as the verb `interrupt`, because a nudge and an interrupt are
different answers.

## How a run is scored

Each run is judged on its orders. Only the verb and the slices count. The note or reason that the agent wrote
is kept beside the score for a person to read, and is never scored. There are six outcomes:

| Outcome | What it means |
|---|---|
| **right** | The run matches a pattern in `accept` and no pattern in `wrong`. |
| **wrong** | The run matches a pattern in `wrong`. This outcome wins if the run also matches `accept`. |
| **unjudged** | The run matches neither list. The person who labelled the case did not foresee this order, so it is a question for them and not a failure. |
| **silent**, **malformed**, **refused** | No usable order: nothing came within the bound, the order file could not be read, or every order was one the event's `may` does not allow. Together these are the **fallback**, where the program applies today's fixed rule (decision 17). |

For each decision, the report gives these figures:

- how often the agent was right, wrong or unjudged;
- how often it fell back;
- how often it **agreed with itself** across runs, as the share of runs that gave the commonest answer;
- the wall time of each run;
- the tokens used, where the harness reports them in its output.

The report also says how many labels a person has signed off.

## Running it

A real run calls the agent, which spends a person's tokens. Only a person starts one:

    make evals PROJECT=<a project whose harness is initialised> [DECISION=gate-failed] [N=3] [BOUND=60]

The command is the same as `python3 scripts/evals.py run --project <path> --runs 3 --bound 60`. Each run
lays its case out as a throwaway project under a temporary directory. It is never inside a real project. Of
the project you name, only its `.specify/integration.json` is read, to find which harness to start.
`CAPTAIN="<command>"` puts a command under test instead. The command is run in the throwaway project, and the
event file's path is passed after the command's own arguments.

To score a saved run again after labels have changed, use this command. It calls no agent:

    make evals-rescore RUN=evals/captain/runs/<stamp>

`python3 scripts/evals.py check` reads every case and reports anything that is wrong with one.

### What the captain under test must do

The captain under test is one callable, `(project, event, bound) -> Ran`, made in `eval_captains.py`:

- It reads the event file and the project state laid out around it.
- It answers by running `python3 scripts/agents/orders.py <verb> …`, which writes order files under
  `.slipwai/run/orders/<fairway>/`.
- It returns once it has finished, or once the bound has passed.

The run reads the order files and never asks the callable what it decided. The default callable,
`harness_captain`, starts one headless session of the project's harness through
`scripts/agents/harness.py`. The session gets the captain's brief and the event. This is decision 18's path.
When the captain agent lands, its entry point replaces that one function. Until `scripts/agents/orders.py`
exists in the toolkit, a real run stops and says why.

## Adding a case

Copy a case of the same decision, and change the `situation`, the `snapshot`, the `event` and the `label`.
Then run `python3 scripts/evals.py check`.

Before you add a case, remove everything personal from the copied lines. That means people's names, email
addresses, tokens and absolute home paths. A test fails any case that has a home path, an email address or a
harness's name in it. A case cut from a run is labelled from **what happened next**. For example, a slice
that was re-dispatched twenty-four times for the same reason should have been parked on the second failure.
Say what happened next in `note`.

## Signing a label off

Every label that was drafted from a recorded run has `"signed_off": ""`, and its note says that it is a draft.
To sign a label off:

1. Read the case.
2. Correct `accept`, `wrong` and `why` until they are what you would accept.
3. Put your name or role in `signed_off`.
4. If the note's draft sentence no longer applies, edit the note.

A score against an unsigned label is a draft too. The report counts signed and unsigned labels separately.

## The cases there are

The drafts were cut from two recorded fleets:

| Decision | Cases | Notes |
|---|---|---|
| `gate-failed` | 9 | Six where parking was right: the same refusal again, a session saying another run ends the same way, a file only a person may change, or every stream failing in the same minute. Three where a retry was right, because the work was done and the gate missed it. |
| `message` | 11 | Messages to a stream about two slices, about three or four, about one, and about none. Two answer a park without naming the slice. |
| `choose-next` | 6 | More cleared slices than slots. Each is labelled from the order the slices finished in. |
| `stuck` | 8 | Long and quiet warnings. Every one resolved by itself. |

The `stuck` cases are where the data is thinnest. Neither fleet recorded a *circles* warning: no agent failed
the same command three times running. Every long or quiet warning that was recorded either resolved by itself
or came from a session that had already ended. So every `stuck` label accepts leaving the slice alone, and
there is no recorded moment where stepping in was the right answer. Cases where a nudge or an interrupt is
right are still owed.

## Running nightly

Nothing runs the evals nightly yet. A nightly run would be a scheduled CI job on a machine with an initialised
harness and its credentials. The job would run `make evals PROJECT=<that project>` and keep
`evals/captain/runs/<stamp>/` as an artifact. The job would never be a required check, and it would never fail
because of a score. It would fail only when the evals could not run at all.
