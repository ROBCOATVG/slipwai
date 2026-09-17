/**
 * The rules that make the model worth keeping.
 *
 * A diagram nobody checks becomes decoration within about two slices — it says `OrderPlaced` while the
 * code says `OrderConfirmed`, and from then on people read the code instead. Everything here is a property
 * a machine can check, so drift fails a build rather than being noticed by whoever happens to look.
 *
 * Every rule is either the shape of one of the four patterns, a naming commitment that is permanent once
 * an event is written, or an agreement between the model and the repository. Nothing here is style.
 *
 * Pure: filesystem questions arrive through `Workspace` so the whole rule set is testable without a
 * fixture tree, the same reason the domain takes a `Clock` rather than reading one.
 */
import {
  eventProducers,
  FRAME_TYPE_LABELS,
  isExternalMockup,
  MODEL_DIR_POSIX,
  numberFrames,
  STATUS_ORDER,
  type FrameType,
  type Model,
  type Slice,
} from './model.ts';

export interface Workspace {
  /** Does this repository-relative path exist? */
  exists(path: string): boolean;
  /** Does this identifier appear anywhere in tracked source? Used to catch model/code divergence. */
  sourceMentions(identifier: string): boolean;
  /** The services `project.json` lists, in order — what a slice's `service` may name. */
  services(): readonly string[];
  /** The bounded contexts one service holds — what a slice placed in it may name as its `context`. */
  contextsOf(service: string): readonly string[];
}

export interface Violation {
  slice?: string;
  rule: string;
  message: string;
}

/** One element of a pattern's frame grammar. `optional` and `repeat` are the only quantifiers needed. */
interface Expectation {
  types: readonly FrameType[];
  quantifier: 'one' | 'optional' | 'oneOrMore';
  describe: string;
}

const GRAMMARS: Readonly<Record<Model['slices'][number]['pattern'], readonly Expectation[]>> = {
  // Command → Event. The only way state changes.
  //
  // A UI issues the command, and only a UI. A processor issuing one is an automation — that is the whole
  // distinction between the two patterns, and allowing `pcr` here erased it: a five-step process manager
  // modelled as five unrelated state-change slices passed every gate, forced a human actor onto commands
  // no human issues, and left the causal chain recorded nowhere but prose inside a label.
  'state-change': [
    { types: ['ui'], quantifier: 'one', describe: 'the UI that issues the command' },
    { types: ['cmd'], quantifier: 'one', describe: 'exactly one command' },
    { types: ['evt'], quantifier: 'oneOrMore', describe: 'the event(s) it appends' },
  ],
  // Events → Read Model. How the system answers a question.
  'state-view': [
    { types: ['rmo'], quantifier: 'one', describe: 'the read model folded from the events it reads' },
    { types: ['ui'], quantifier: 'optional', describe: 'optionally the screen that renders it' },
  ],
  // Event → Read Model → Processor → Command → Event. All four parts, or it is not an automation.
  automation: [
    { types: ['rmo'], quantifier: 'one', describe: 'the read model the processor consults (its todo list)' },
    { types: ['pcr'], quantifier: 'one', describe: 'the processor holding the conditional logic' },
    { types: ['cmd'], quantifier: 'one', describe: 'the command it issues' },
    { types: ['evt'], quantifier: 'oneOrMore', describe: 'the resulting event(s)' },
  ],
  // External data → internal event. The anti-corruption layer.
  translation: [
    { types: ['evt'], quantifier: 'one', describe: 'the external event, marked `external: true`' },
    { types: ['pcr'], quantifier: 'one', describe: 'the processor that maps it' },
    { types: ['cmd'], quantifier: 'one', describe: 'the internal command' },
    { types: ['evt'], quantifier: 'oneOrMore', describe: 'the internal event(s)' },
  ],
};

function describeGrammar(pattern: keyof typeof GRAMMARS): string {
  return GRAMMARS[pattern]
    .map((e) => {
      const types = e.types.join('|');
      const suffix = e.quantifier === 'oneOrMore' ? '+' : e.quantifier === 'optional' ? '?' : '';
      return `${types}${suffix}`;
    })
    .join(' → ');
}

/** Walks a slice's frame types against its pattern's grammar. */
function checkGrammar(slice: Slice): Violation[] {
  const grammar = GRAMMARS[slice.pattern];
  const actual = slice.frames.map((f) => f.type);
  let cursor = 0;

  // Answered before the grammar walk, because "frame 1 should be a UI, but it is pcr" is a true statement
  // that teaches nobody anything. This is the misclassification that survives longest — it validates, it
  // renders, and the only thing missing is every arrow between the steps.
  const processor = slice.frames.find((frame) => frame.type === 'pcr');
  if (slice.pattern === 'state-change' && processor !== undefined) {
    return [
      {
        slice: slice.id,
        rule: 'processor-means-automation',
        message:
          `${processor.name} is a processor, so this is an \`automation\`, not a \`state-change\`: a ` +
          'state-change slice is a command issued by a UI. Reclassify it, and put in `reads` the events ' +
          "its **todo list** folds — what tells the processor there is work to do, which is an earlier " +
          "slice's events. Do not put the events the *Decider* folds to decide; those are `folds`, they " +
          'live on this slice\'s own stream, and listing them here fails `reads-earlier-slice` and makes ' +
          'the automation pattern look impossible',
      },
    ];
  }

  for (const expectation of grammar) {
    const matches = (index: number): boolean => {
      const type = actual[index];
      return type !== undefined && expectation.types.includes(type);
    };

    if (expectation.quantifier === 'optional') {
      if (matches(cursor)) {
        cursor += 1;
      }
      continue;
    }

    if (!matches(cursor)) {
      return [
        {
          slice: slice.id,
          rule: 'pattern-shape',
          message:
            `a ${slice.pattern} slice reads ${describeGrammar(slice.pattern)}; ` +
            `frame ${String(cursor + 1)} should be ${expectation.describe}, but it is ` +
            `${actual[cursor] ?? 'missing'}`,
        },
      ];
    }
    cursor += 1;

    if (expectation.quantifier === 'oneOrMore') {
      while (matches(cursor)) {
        cursor += 1;
      }
    }
  }

  if (cursor !== actual.length) {
    return [
      {
        slice: slice.id,
        rule: 'pattern-shape',
        message:
          `a ${slice.pattern} slice reads ${describeGrammar(slice.pattern)}, so frame ` +
          `${String(cursor + 1)} (${actual[cursor] ?? 'unknown'}) does not belong. ` +
          `Extra work after the event usually means this is two slices`,
      },
    ];
  }

  return [];
}

export function validate(model: Model, workspace: Workspace): Violation[] {
  const violations: Violation[] = [];
  const frames = numberFrames(model);
  const producers = eventProducers(frames);

  const seenIds = new Set<string>();
  for (const slice of model.slices) {
    if (seenIds.has(slice.id)) {
      violations.push({
        slice: slice.id,
        rule: 'unique-slice-id',
        message: 'two slices share this id; ids are referenced by plans and tasks, so they must be unique',
      });
    }
    seenIds.add(slice.id);
  }

  const commandNames = new Set(
    frames.filter((f) => f.type === 'cmd').map((f) => f.name),
  );

  for (const [index, slice] of model.slices.entries()) {
    violations.push(...checkGrammar(slice));

    // ── Read-model-to-command is the one edge event modelling forbids outright ──────────────────────
    // The reason is consistency, not shape. A command may decide only from what its own append can hold
    // still: the events it folded under the same guard it appends with — its stream's expected version, or
    // the tag query a conditional append is guarded by. A projection maintained by a subscription is
    // neither; it lags by design, and no guard covers it, which is how you sell the last ticket twice.
    // Under a Dynamic Consistency Boundary the rule reads the same and the model is unchanged: what a
    // command loads is specified by its Given/When/Then's GIVEN, never by a view.
    for (const [position, frame] of slice.frames.entries()) {
      const next = slice.frames[position + 1];
      if (frame.type === 'rmo' && next?.type === 'cmd') {
        violations.push({
          slice: slice.id,
          rule: 'no-readmodel-to-command',
          message:
            `${frame.name} (read model) feeds ${next.name} (command) directly. A command decides from ` +
            'events it folded under the same guard it appends with, never from a view something else ' +
            'maintains — put the processor that decides between them, or this is a state-change slice ' +
            'whose command takes its input from the caller',
        });
      }
    }

    // ── Where a slice's inputs come from ───────────────────────────────────────────────────────────
    const reads = slice.reads ?? [];

    if (slice.pattern === 'state-change' && reads.length > 0) {
      violations.push({
        slice: slice.id,
        rule: 'state-change-reads-nothing',
        message:
          'a state-change slice declares no `reads`: its command takes user input and consults the event ' +
          'stream. If it genuinely needs a projection first, that projection is its own state-view slice',
      });
    }

    if ((slice.pattern === 'state-view' || slice.pattern === 'automation') && reads.length === 0) {
      violations.push({
        slice: slice.id,
        rule: 'reads-required',
        message:
          `a ${slice.pattern} slice must declare the events it folds in \`reads\`; without them the read ` +
          'model has no source and every field is unaccounted for',
      });
    }

    if (slice.pattern === 'translation' && reads.length > 0) {
      violations.push({
        slice: slice.id,
        rule: 'translation-reads-nothing',
        message:
          'a translation slice starts from the external event in its own frames, not from `reads` — ' +
          '`reads` names events this system already produced',
      });
    }

    for (const name of reads) {
      const producer = producers.get(name);
      if (producer === undefined) {
        violations.push({
          slice: slice.id,
          rule: 'reads-resolve',
          message:
            `reads \`${name}\`, which no slice produces. Every read model field must trace to an event ` +
            'somebody appends — either add the slice that emits it, or correct the name',
        });
        continue;
      }
      const producerIndex = model.slices.findIndex((s) => s.id === producer.sliceId);
      if (producerIndex >= index) {
        violations.push({
          slice: slice.id,
          rule: 'reads-earlier-slice',
          message:
            `reads \`${name}\`, produced by ${producer.sliceId}, which is not earlier on the timeline. ` +
            'A projection cannot fold an event that has not happened yet, and Mermaid drops the arrow',
        });
      }
    }

    // ── Where the read model lives ─────────────────────────────────────────────────────────────────
    // The read side's counterpart to `stream`, and required from the same status for the same reason.
    // Left unasked, the answer is decided by whichever read path already exists: the skeleton ships
    // `read` and `readAll` and no projection store, so a fold over the log on every query is free to
    // write and everything else is greenfield. That is a decision about what every query costs, taken by
    // gravity, in a slice nobody revisits — so the model records it, and `check.py` mirrors these rules
    // because it is what `make check-model` runs.
    const materialisation = slice.materialisation;
    const budget = slice.liveBudget;
    const holdsAReadModel = slice.pattern === 'state-view' || slice.pattern === 'automation';

    if (!holdsAReadModel && materialisation !== undefined) {
      violations.push({
        slice: slice.id,
        rule: 'materialisation-needs-a-read-model',
        message:
          `\`materialisation\` says where a read model lives, and a ${slice.pattern} slice has none. A ` +
          'command decides from events it folded under the same guard it appends with, never from a ' +
            'view something else maintains',
      });
    }

    if (slice.pattern === 'automation' && materialisation === 'live') {
      violations.push({
        slice: slice.id,
        rule: 'todo-list-is-persisted',
        message:
          "an automation's read model is a todo list, not a view: losing it loses work nothing else " +
          'records. `live` folds it per request, so the processor cannot be spawned standalone — and a ' +
          'standalone run is how it discovers work it did not create and recovers what a dead request ' +
          'abandoned. Name `inline` or `async`',
      });
    }

    if (slice.pattern === 'state-view' && materialisation === 'live' && budget === undefined) {
      violations.push({
        slice: slice.id,
        rule: 'live-fold-is-bounded',
        message:
          '`materialisation: live` folds the log on every query, which holds only while the fold stays ' +
          'small — so it names `liveBudget.events`, the ceiling one query may fold, and ' +
          '`liveBudget.because`, why that ceiling holds in terms of the stream\'s own lifetime. Unwritten, ' +
          '"the streams are short" is an assumption nothing measures and no gate can fail',
      });
    }

    if (budget !== undefined && !(slice.pattern === 'state-view' && materialisation === 'live')) {
      violations.push({
        slice: slice.id,
        rule: 'live-budget-bounds-a-live-fold',
        message:
          '`liveBudget` bounds the fold a `live` state-view does on every query. ' +
          (materialisation === 'inline' || materialisation === 'async'
            ? `this read model is materialised, so its cost belongs to the subscription that maintains ` +
              `it — cap the projection's lag instead`
            : 'this slice declares no such fold'),
      });
    }

    // ── What the Decider folds, as opposed to what the projection reads ────────────────────────────
    // The distinction these rules exist for: `reads` is a todo list over *earlier* slices' events, and
    // `folds` is the history a Decider rehydrates from. A state specified outside the guard the append is
    // checked against is unbuildable and nothing else notices — not the linters, not the imports check,
    // and not the Decider's own unit test, which hand-feeds it events that could never have been loaded
    // under that guard.
    //
    // Which guard is the slice's own declaration: `stream` (the version of one stream) or `guard` (a tag
    // query). The rule is the same sentence either way — *what a decision folds must be what its append is
    // guarded by* — and only the check differs.
    const folds = slice.folds ?? [];

    if (slice.pattern === 'state-view' && folds.length > 0) {
      violations.push({
        slice: slice.id,
        rule: 'state-view-folds-nothing',
        message:
          'a state-view slice has no Decider, so it declares no `folds`. The events it folds into its ' +
          'projection are `reads`',
      });
    }

    for (const name of folds) {
      const producer = producers.get(name);
      if (producer === undefined) {
        violations.push({
          slice: slice.id,
          rule: 'folds-resolve',
          message:
            `folds \`${name}\`, which no slice produces. A Decider rehydrates from events somebody ` +
            'appends — either add the slice that emits it, or correct the name',
        });
        continue;
      }

      const producingSlice = model.slices.find((s) => s.id === producer.sliceId);

      if (slice.guard !== undefined) {
        // A tag boundary: the folded event has to be findable by one of the kinds the guard queries by,
        // which is what its producing frame's identifying attributes say.
        const kinds = new Set(
          (producer.attributes ?? [])
            .map((attribute) => attribute.identifies)
            .filter((kind): kind is string => kind !== undefined),
        );
        if (!slice.guard.by.some((kind) => kinds.has(kind))) {
          violations.push({
            slice: slice.id,
            rule: 'folds-match-the-guard',
            message:
              `folds \`${name}\`, which identifies ${kinds.size === 0 ? 'nothing' : [...kinds].join(', ')} — ` +
              `none of the kinds this slice's boundary is drawn by (${slice.guard.by.join(', ')}). A ` +
              'conditional append is refused only by events the query covers, so a decision folding this ' +
              'one is guarded against something it did not read. Either mark the attribute that ' +
              'identifies one of those kinds on the event, or widen the boundary and say why',
          });
        }
        continue;
      }

      const producerStream = producingSlice?.stream;
      if (slice.stream === undefined || producerStream === undefined) {
        continue; // A guard is not required until `planned`; the status rules cover that.
      }
      if (producerStream !== slice.stream) {
        violations.push({
          slice: slice.id,
          rule: 'folds-own-stream',
          message:
            `folds \`${name}\`, which ${producer.sliceId} appends to \`${producerStream}\` — a different ` +
            `stream from this slice's \`${slice.stream}\`. A Decider can only rehydrate from its own ` +
            'stream, so this state is unreachable and the command will decide from nothing. Either the ' +
            'two slices share a stream, or the fact this needs belongs in the command as an input the ' +
            'use case supplies',
        });
      }
    }

    // ── External events ────────────────────────────────────────────────────────────────────────────
    for (const [position, frame] of slice.frames.entries()) {
      if (frame.external !== true) {
        continue;
      }
      if (frame.type !== 'evt') {
        violations.push({
          slice: slice.id,
          rule: 'external-is-an-event',
          message: `${frame.name} is marked external but is a ${frame.type}; only an event arrives from outside`,
        });
      } else if (slice.pattern !== 'translation' || position !== 0) {
        violations.push({
          slice: slice.id,
          rule: 'external-opens-a-translation',
          message:
            `${frame.name} is external, so this slice is a translation and must open with it. An external ` +
            'event reached any other way has no anti-corruption boundary',
        });
      }
    }

    // ── Attributes: what an event carries, and which of it identifies something ────────────────────
    // The structured form of `data`, and the only place the tag index can be derived from: a tag is
    // `<kind>:<value>`, so an event that marks which attributes identify a course or a seat is an event
    // whose `tagsOf` is generated rather than typed. Tags stay out of the model; identity does not.
    for (const frame of slice.frames) {
      const attributes = frame.attributes ?? [];
      if (attributes.length === 0) {
        continue;
      }

      if (frame.type !== 'evt') {
        violations.push({
          slice: slice.id,
          rule: 'attributes-belong-to-an-event',
          message:
            `${frame.name} is a ${frame.type} box and carries \`attributes\`, which only an event has. A ` +
            "command's payload is what a caller sends and a read model's is what a query returns; neither " +
            'is what the tag index is derived from, and marking identity on one implies a guard that does ' +
            'not exist',
        });
      }

      if (frame.data !== undefined) {
        violations.push({
          slice: slice.id,
          rule: 'attributes-or-data',
          message:
            `${frame.name} carries both \`data\` and \`attributes\`, which are two places for one list. ` +
            'Keep the attributes — they say which of them identify something, and the diagram is rendered ' +
            'from them',
        });
      }

      const named = new Set<string>();
      for (const attribute of attributes) {
        if (named.has(attribute.name)) {
          violations.push({
            slice: slice.id,
            rule: 'attribute-names-are-unique',
            message:
              `${frame.name} names the attribute \`${attribute.name}\` twice. One entry per attribute: an ` +
              'event carrying two of the same kind names them differently and marks both, which is how ' +
              '`fromAccount` and `toAccount` both identify an account',
          });
        }
        named.add(attribute.name);
      }
    }

    // ── Mockups: which states of a screen somebody has actually designed ───────────────────────────
    // The white box is the only frame that is a screen, and a screen has states. Recording them here is
    // what lets `/gaps` ask "you have designed populated and error — what does empty look like?" against
    // something rather than against memory.
    for (const frame of slice.frames) {
      const mockups = frame.mockups ?? [];
      if (mockups.length === 0) {
        continue;
      }

      if (frame.type !== 'ui') {
        violations.push({
          slice: slice.id,
          rule: 'mockup-is-a-screen',
          message:
            `${frame.name} names mockups but is a ${FRAME_TYPE_LABELS[frame.type]}. Only the white box is a ` +
            'screen — a command, an event and a read model are data, so a picture of one is really a ' +
            'picture of the screen that shows it, and that is a different box',
        });
        continue;
      }

      const seenStates = new Set<string>();
      for (const mockup of mockups) {
        if (seenStates.has(mockup.state)) {
          violations.push({
            slice: slice.id,
            rule: 'mockup-state-is-unique',
            message:
              `${frame.name} has two mockups for the \`${mockup.state}\` state. One of them is the current ` +
              'design and one is not, and nothing here can tell which — name the states apart, or delete ' +
              'the stale mock',
          });
        }
        seenStates.add(mockup.state);

        // A URL is the author's word, checked by shape and never fetched: this gate does no network.
        if (isExternalMockup(mockup.at)) {
          continue;
        }

        if (!workspace.exists(mockup.at)) {
          violations.push({
            slice: slice.id,
            rule: 'mockup-exists',
            message:
              `${frame.name}'s \`${mockup.state}\` mockup points at ${mockup.at}, which does not exist. ` +
              'Paths here are repository-relative, like `gwt` and `code`',
          });
        }

        // Only once the model has an address. Without `render.page` the browsable page is opened from a
        // clone, where a repository-relative path resolves wherever the mock happens to live.
        if (model.render.page !== undefined && !mockup.at.startsWith(`${MODEL_DIR_POSIX}/`)) {
          violations.push({
            slice: slice.id,
            rule: 'mockup-publishes-with-the-page',
            message:
              `${frame.name}'s \`${mockup.state}\` mockup is ${mockup.at}, outside ${MODEL_DIR_POSIX}/. ` +
              '`render.page` is set, and the workflow publishes that directory and nothing else — so this ' +
              'link works in a clone and 404s on the page people are actually sent to. Move the mock under ' +
              `${MODEL_DIR_POSIX}/mockups/, or give it an absolute URL if it lives in a design tool`,
          });
        }
      }
    }

    // ── Naming, because an event schema is permanent ────────────────────────────────────────────────
    for (const frame of slice.frames) {
      if (frame.type === 'cmd' && /ed$/.test(frame.name)) {
        violations.push({
          slice: slice.id,
          rule: 'command-is-imperative',
          message:
            `command \`${frame.name}\` is named in the past tense. Commands ask (\`PlaceOrder\`); events ` +
            'record (`OrderPlaced`). A command named as a fact is usually an event in the wrong lane',
        });
      }
      if (frame.type === 'evt' && commandNames.has(frame.name)) {
        violations.push({
          slice: slice.id,
          rule: 'event-is-not-its-command',
          message:
            `\`${frame.name}\` is used as both a command and an event. The request and the fact are ` +
            'different things and outlive each other differently — name them differently',
        });
      }
    }

    // ── What each status commits to ─────────────────────────────────────────────────────────────────
    const rank = STATUS_ORDER[slice.status];

    if (slice.stream !== undefined && slice.guard !== undefined) {
      violations.push({
        slice: slice.id,
        rule: 'one-guard-not-two',
        message:
          'declares both `stream` and `guard`, which are two answers to one question. An append is ' +
          "checked against the version of one stream *or* against a query over tags — never both, and a " +
          'slice that names both has not decided which of them a conflict means',
      });
    }

    if (
      rank >= STATUS_ORDER.planned &&
      slice.pattern === 'state-change' &&
      slice.stream === undefined &&
      slice.guard === undefined
    ) {
      violations.push({
        slice: slice.id,
        rule: 'guard-before-planning',
        message:
          'a state-change slice cannot be planned without naming what its append is guarded by: `stream`, ' +
          'whose version the append carries, or `guard`, a boundary drawn over tags. Both are consistency ' +
          'boundaries and therefore concurrency ceilings; changing either later migrates the one thing ' +
          'that cannot be migrated, which is why the answer is owed here and not at the first conflict',
      });
    }

    // Its read-side sibling, at the same status and for the same reason: `stream` decides what a write
    // costs to keep consistent, `materialisation` decides what a query costs to answer, and both are
    // answered once and lived with. Unasked, the second one answers itself — the skeleton has `read` and
    // `readAll` and no projection store, so folding the log per query is the only read path that is free
    // to write, and the slice ships with every query paying for the whole log.
    if (holdsAReadModel && materialisation === undefined && rank >= STATUS_ORDER.planned) {
      violations.push({
        slice: slice.id,
        rule: 'materialisation-before-planning',
        message:
          `a planned ${slice.pattern} names where its read model lives in \`materialisation\`: \`live\` ` +
          '(folded per query, nothing stored), `inline` (written in the append\'s own transaction) or ' +
          '`async` (a catch-up subscription with a checkpoint). It decides what every query on this view ' +
          'costs, and a slice planned without it gets the per-query fold by default rather than by choice',
      });
    }

    // Examples come before the plan, not after it. `/example-map` turns the slice's rules into concrete
    // examples and those examples into the Given/When/Then it is built against; a plan written first is a
    // plan against a guess, and the acceptance tests then get reverse-engineered from the implementation —
    // which is the failure Principle V's "tests written after the code they cover MUST be sent back" names.
    //
    // Deliberately checked from `planned` rather than `implemented`: by the time a slice claims to be
    // implemented, missing scenarios are a finding about work already done.
    if (rank >= STATUS_ORDER.planned) {
      if (slice.gwt === undefined) {
        violations.push({
          slice: slice.id,
          rule: 'examples-before-planning',
          message:
            'a slice cannot be planned without `gwt`. Run `/example-map` first: its rules and concrete ' +
            'examples become the Given/When/Then this slice is built against, and `gwt` names the file ' +
            'holding them',
        });
      } else if (!workspace.exists(slice.gwt)) {
        violations.push({
          slice: slice.id,
          rule: 'gwt-recorded',
          message: `\`gwt\` points at ${slice.gwt}, which does not exist`,
        });
      }
    }

    if (
      rank >= STATUS_ORDER.modelled &&
      slice.actor === undefined &&
      (slice.pattern === 'state-change' || slice.pattern === 'state-view')
    ) {
      violations.push({
        slice: slice.id,
        rule: 'actor-named',
        message:
          `a ${slice.pattern} slice needs an \`actor\` — who issues this command, or who reads this view. ` +
          '"The system" is an automation, which is a different pattern',
      });
    }

    // Which service owns the slice. With one service there is nothing to decide, so the field is optional;
    // with two or more, a modelled slice that names none lands in the first service by gravity rather than
    // by decision — which is exactly the placement this rule exists to turn into a question. The name is
    // checked against the manifest whenever present, so a renamed service fails here, not in a build.
    const services = workspace.services();
    if (slice.service !== undefined && !services.includes(slice.service)) {
      violations.push({
        slice: slice.id,
        rule: 'service-exists',
        message:
          `\`service\` names ${slice.service}, which project.json does not list` +
          (services.length > 0 ? ` (it has ${services.join(', ')})` : ''),
      });
    } else if (slice.service === undefined && services.length > 1 && rank >= STATUS_ORDER.modelled) {
      violations.push({
        slice: slice.id,
        rule: 'service-named',
        message:
          `this project has ${String(services.length)} services (${services.join(', ')}); a modelled slice ` +
          'names the one that owns it in `service`, chosen against each service\'s `purpose` in ' +
          'project.json. A slice no purpose covers is a product decision, not a default',
      });
    }

    // Which bounded context inside that service. A service holding one context has nothing to decide; one
    // holding several is the modular monolith a project starts as, and a slice placed in the service but in
    // no context is placed by gravity again — into whichever `src/<context>/` the implementer reaches for.
    const owner = slice.service !== undefined && services.includes(slice.service)
      ? slice.service
      : services.length === 1 ? services[0] : undefined;
    const held = owner === undefined ? [] : workspace.contextsOf(owner);
    if (slice.context !== undefined && owner !== undefined && !held.includes(slice.context)) {
      violations.push({
        slice: slice.id,
        rule: 'context-exists',
        message: `\`context\` names ${slice.context}, which service ${owner} does not hold (it holds ${held.join(', ')})`,
      });
    } else if (slice.context === undefined && held.length > 1 && rank >= STATUS_ORDER.modelled) {
      violations.push({
        slice: slice.id,
        rule: 'context-named',
        message:
          `service ${String(owner)} holds ${String(held.length)} bounded contexts (${held.join(', ')}); a modelled ` +
          'slice names the one it belongs to in `context`',
      });
    }

    if (rank >= STATUS_ORDER.implemented) {
      // `gwt` is already required and existence-checked from `planned` above.
      const code = slice.code ?? [];
      if (code.length === 0) {
        violations.push({
          slice: slice.id,
          rule: 'code-recorded',
          message: 'an implemented slice must list the files that realise it in `code`',
        });
      }
      for (const path of code) {
        if (!workspace.exists(path)) {
          violations.push({
            slice: slice.id,
            rule: 'code-recorded',
            message: `\`code\` lists ${path}, which does not exist. Either the model or the tree moved on`,
          });
        }
      }

      // The check that actually catches drift: the model says this event exists, so the code should
      // contain it. A rename that stops here is a rename the diagram would otherwise survive silently.
      for (const frame of slice.frames) {
        if ((frame.type === 'evt' || frame.type === 'cmd') && !workspace.sourceMentions(frame.name)) {
          violations.push({
            slice: slice.id,
            rule: 'model-matches-code',
            message:
              `${frame.name} appears in the model but nowhere in the source. If it was renamed, rename it ` +
              'here too; if it was never built, this slice is not implemented',
          });
        }
      }

      // ── The white box is a deliverable, not a caption ────────────────────────────────────────────────
      //
      // Everything above this line is a backend obligation, and for a long time so was everything the
      // templates and the one-page map said a `ui` frame becomes. A slice would model a screen, build the
      // route beneath it, ship with no frontend at all, and pass every gate — because `model-matches-code`
      // asked about `evt` and `cmd` and nothing asked about the surface the actor was supposed to use.
      //
      // So a white box is held to exactly the standard an event is: the model named it, therefore it exists
      // in the source. The frontend is part of the slice that models it, in the same PR — a screen whose
      // submit currently reaches nothing is still that slice's deliverable, not a later slice's.
      for (const frame of slice.frames) {
        if (frame.type !== 'ui') {
          continue;
        }

        if (!workspace.sourceMentions(frame.name)) {
          violations.push({
            slice: slice.id,
            rule: 'screen-is-built',
            message:
              `${frame.name} is a white box — the surface this slice's actor uses — and it appears nowhere ` +
              'in the source. A white box is a deliverable of the slice that models it, built in the same ' +
              'change as its command, even if what it submits to is not wired up yet. If the screen was ' +
              'named differently in code, make the two names one name; if it was never built, this slice ' +
              'is not implemented',
          });
        }

        // Which states got built is the other half, and it is the half that rots. `mockups` is where a
        // screen's states are recorded, and a screen built without designs is the *commonest* case rather
        // than the exception — nobody drew it, so the agent designed as it went. Recording what it settled
        // on is what stops `model.html` saying "no mockups yet" about a screen that has shipped, and it is
        // the only place the states somebody chose are written down at all.
        if ((frame.mockups ?? []).length === 0) {
          violations.push({
            slice: slice.id,
            rule: 'screen-states-recorded',
            message:
              `${frame.name} has shipped with no \`mockups\`, so nothing records which states of it were ` +
              'built. If it was designed from mocks, point at them; if it was designed while being built, ' +
              `write those states down — one entry per state (empty, populated, error, submitting) under ` +
              `${MODEL_DIR_POSIX}/mockups/. A screen whose states live only in the code is a screen whose ` +
              'unhandled states are invisible to `/gaps` and to the next person',
          });
        }
      }
    }
  }


  // Build-order deps (depends_on) — separate from timeline reads.
  const byId = new Map(model.slices.map((s) => [s.id, s]));
  const eventProducer = new Map<string, string>();
  for (const slice of model.slices) {
    for (const frame of slice.frames) {
      if (frame.type === 'evt' && !eventProducer.has(frame.name)) {
        eventProducer.set(frame.name, slice.id);
      }
    }
  }
  const graph = new Map<string, string[]>();
  for (const slice of model.slices) {
    const deps = slice.depends_on ?? [];
    graph.set(slice.id, []);
    for (const dep of deps) {
      if (dep === slice.id) {
        violations.push({
          slice: slice.id,
          rule: 'depends-on-self',
          message: 'depends_on cannot include this slice itself',
        });
        continue;
      }
      if (!byId.has(dep)) {
        violations.push({
          slice: slice.id,
          rule: 'depends-on-unknown',
          message: `depends_on names \`${dep}\`, which is not a slice id`,
        });
        continue;
      }
      graph.get(slice.id)!.push(dep);
    }
    const reads = slice.reads ?? [];
    if (deps.length > 0 && reads.length > 0) {
      const readProducers = new Set(
        reads.map((name) => eventProducer.get(name)).filter((id): id is string => id !== undefined),
      );
      if (readProducers.size > 0 && deps.length === readProducers.size && deps.every((d) => readProducers.has(d))) {
        violations.push({
          slice: slice.id,
          rule: 'depends-on-is-reads',
          message:
            `depends_on [${deps.join(', ')}] is exactly the producers of its reads — that is a timeline ` +
            'fact, not a build dependency. Seed from synthetic events (Principle V) and leave depends_on ' +
            'empty, or name a genuine code/contract dependency that is not only those producers',
        });
      }
    }
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const walk = (node: string, stack: string[]): void => {
    if (visiting.has(node)) {
      const cycle = stack.slice(stack.indexOf(node)).concat(node);
      violations.push({
        slice: node,
        rule: 'depends-on-cycle',
        message: `depends_on cycle ${cycle.join(' → ')}`,
      });
      return;
    }
    if (visited.has(node)) return;
    visiting.add(node);
    for (const next of graph.get(node) ?? []) walk(next, stack.concat(node));
    visiting.delete(node);
    visited.add(node);
  };
  for (const id of graph.keys()) walk(id, []);

  return violations;
}
