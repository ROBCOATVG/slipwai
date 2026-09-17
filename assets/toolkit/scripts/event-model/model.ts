/**
 * The schema for `docs/event-model/model.yaml` — the one global event model.
 *
 * Why YAML with a schema rather than hand-written Mermaid: the diagram is only one of the things the
 * model has to produce. The same source also has to answer "which slice is implemented", "where are its
 * GWT scenarios", "which code realises it", and "does every read model trace back to an event someone
 * emits" — and none of that survives in a picture. Mermaid is the *rendering*, not the model.
 *
 * Frame numbers are derived, never authored. Mermaid needs a unique number per box, and hand-maintaining
 * them across a model that grows for the life of the project is exactly the bookkeeping that makes people
 * stop updating the diagram. Slice order in this file is timeline order; position within a slice is
 * causal order. That is enough to derive every number.
 */
import { readFileSync } from 'node:fs';
import { posix } from 'node:path';

import { z } from 'zod';

/** The five entity types Mermaid's event modeling diagram draws, in its own vocabulary. */
export const FRAME_TYPES = ['ui', 'pcr', 'cmd', 'rmo', 'evt'] as const;
export type FrameType = (typeof FRAME_TYPES)[number];

/** How each type reads in prose, for error messages that name what a person sees on the diagram. */
export const FRAME_TYPE_LABELS: Readonly<Record<FrameType, string>> = {
  ui: 'UI / wireframe',
  pcr: 'processor (automation)',
  cmd: 'command',
  rmo: 'read model',
  evt: 'event',
};

/**
 * The four patterns. Every slice is exactly one of them — that is the claim the `event-modeling` skill
 * makes, and `validate.ts` holds the model to it.
 */
export const PATTERNS = ['state-change', 'state-view', 'automation', 'translation'] as const;
export type Pattern = (typeof PATTERNS)[number];

/**
 * Lifecycle, in the order the Spec Kit flow walks it. Each step tightens what the model must contain:
 * `planned` demands stream identity, `implemented` demands code that exists and events that appear in it.
 *
 * `proposed` exists so a slice discovered mid-conversation can be recorded before anyone has decided it
 * is real. Without it the honest options are "leave it out of the model" or "lie about its status".
 */
export const STATUSES = ['proposed', 'modelled', 'planned', 'implemented'] as const;
export type Status = (typeof STATUSES)[number];

/**
 * The three bands Mermaid lays boxes out in, and which frame types land in each.
 *
 * A namespace is resolved **per band**, not per diagram: `Guest.` on a `ui` box and `Inventory.` on an
 * `evt` box are independent, so the notation's own picture — actors across the top, streams across the
 * bottom — is one diagram rather than two. `render.lanes` is one setting per band for that reason.
 */
export const LANE_BANDS = ['ui', 'data', 'events'] as const;
export type LaneBand = (typeof LANE_BANDS)[number];

export const BAND_OF: Readonly<Record<FrameType, LaneBand>> = {
  ui: 'ui',
  pcr: 'ui',
  cmd: 'data',
  rmo: 'data',
  evt: 'events',
};

/** What each band may group its lanes by. `none` is the notation's single default lane for that band. */
export const UI_LANE_SOURCES = ['actor', 'context', 'none'] as const;
export const DATA_LANE_SOURCES = ['context', 'none'] as const;
export const EVENT_LANE_SOURCES = ['stream', 'context', 'none'] as const;
export type LaneSource = 'actor' | 'context' | 'stream' | 'none';

export const STATUS_ORDER: Readonly<Record<Status, number>> = {
  proposed: 0,
  modelled: 1,
  planned: 2,
  implemented: 3,
};

const identifier = z
  .string()
  .regex(/^[A-Za-z][A-Za-z0-9]*$/, 'must be a PascalCase name with no spaces or punctuation');

/**
 * The directory the model's own artifacts live in, forward-slashed.
 *
 * It sits here rather than in `workspace.ts` because `validate.ts` needs it — the publish workflow serves
 * this directory and nothing else, so a mockup outside it is a link the published page cannot resolve —
 * and `validate.ts` must not import the module that reads the repository. `workspace.ts` derives its own
 * platform-joined `MODEL_DIR` from this, so the two cannot drift apart. The one file read here is the
 * manifest, once, for where the directory is (`deliveryRoot` below); the model itself is `workspace.ts`'s.
 */
export const MODEL_DIR_POSIX = posix.join(deliveryRoot(), 'docs', 'event-model');

/**
 * Where the factory's delivery material lives, from `project.json`'s `layout.delivery`: `''` for the root —
 * every generated project, and every manifest written before the key — or a directory such as `delivery`
 * where the method was installed beside an existing codebase. Read from the working directory, which is
 * the repository root for every `make` target that reaches this pipeline.
 */
function deliveryRoot(): string {
  try {
    const layout = (JSON.parse(readFileSync('project.json', 'utf8')) as { layout?: { delivery?: unknown } }).layout;
    const delivery = layout?.delivery;
    return typeof delivery === 'string' && delivery !== '' && delivery !== '.' ? delivery : '';
  } catch {
    return '';
  }
}

/**
 * A mock that lives in a design tool rather than in the repository.
 *
 * Recognised by shape and never fetched: `check-model` does no network, so a URL is the author's word that
 * it resolves. That is the same trade `render.page` makes, and for the same reason — a gate that answers
 * differently depending on what the network did is not a gate.
 */
export function isExternalMockup(at: string): boolean {
  return /^https?:\/\//i.test(at);
}

/**
 * One state of a screen, and where its mock lives.
 *
 * A white box is a screen, and a screen is almost never one picture: empty, populated, error and
 * mid-flight are different designs, and the differences between them are exactly where the unmodelled
 * states hide. So this is a list of *labelled* states rather than a single link — `/gaps` and
 * `/example-map` both ask which states exist, and a model that can only name one has nowhere to put the
 * answer.
 */
const mockupSchema = z.strictObject({
  /**
   * Which state this mock shows — `empty`, `populated`, `error`, `submitting`. Free text for the same
   * reason `actor` is: which states are worth drawing is a modelling output, not something a starter can
   * enumerate ahead of a domain.
   */
  state: z.string().min(1),
  /**
   * Repository-relative path, or an absolute URL for a mock held in a design tool.
   *
   * Repository-relative like `gwt`, `spec` and `code` — one convention for every path in this file — and
   * never relative to whatever happens to link it. The page rewrites them for its own location.
   */
  at: z.string().min(1),
});

export type Mockup = z.infer<typeof mockupSchema>;

/**
 * One attribute of an event, and whether it identifies something.
 *
 * The structured form of `data`, and it exists for one reason: `identifies` is what the tag index is
 * generated from. A conditional append is guarded by a query over tags, and a tag is
 * `<kind>:<value>` — so an event that says which of its attributes identify a course, a seat or a
 * student is an event whose `tagsOf` can be *derived* rather than hand-written. Tags themselves stay
 * out of the model: they are a technical index, not a fact about the business.
 *
 * `identifies` names the **kind** rather than being a flag, and that is deliberate. Two attributes may
 * identify the same kind — `fromAccount` and `toAccount` are both an `account` — and a flag cannot
 * express that: the event carries two `account:` tags, and a query for either finds it. A flag would
 * also leave "identifies *what*" to be guessed from the attribute's name, which is how `customerId`
 * on one event and `buyer` on another end up as two kinds nobody meant.
 */
const attributeSchema = z.strictObject({
  /** The attribute's name, as the payload spells it. */
  name: identifier,
  /**
   * What it is, when the type is worth saying. Free text: a model is not a schema, and the moment this
   * becomes one somebody will start generating the wrong half of the system from it.
   */
  type: z.string().min(1).optional(),
  /**
   * The kind of thing this attribute identifies — `course`, `seat`, `student` — or absent when it
   * identifies nothing. Lower case, because it becomes the tag's key.
   */
  identifies: z
    .string()
    .regex(/^[a-z][a-z0-9-]*$/, 'must be a lower-case kind like `course` or `seat`')
    .optional(),
});

export type Attribute = z.infer<typeof attributeSchema>;

const frameSchema = z.strictObject({
  type: z.enum(FRAME_TYPES),
  name: identifier,
  /**
   * Example data, rendered inside the box. Prose or `field: type` pairs both work — Mermaid does not
   * interpret it. Concrete values beat type names here; the point of a model is a worked example.
   *
   * An `evt` frame may carry `attributes` instead, which is the same list with somewhere to say which
   * of them identify something. Never both: two places for one list is two places to disagree.
   */
  data: z.string().min(1).optional(),
  /**
   * This event's attributes, one entry each, with the identifying ones marked.
   *
   * Only an `evt` frame has them, and `check-model` says so. A command's payload is what a caller
   * sends and a read model's is what a query returns; neither is what the tag index is derived from,
   * and marking identity on one would imply a guard that does not exist.
   *
   * Optional, and asked for at `planned` rather than at `modelled`: which attributes identify
   * something is a technical detail, and a discovery session is the wrong place for it. A slice whose
   * events name them gets a generated `tagsOf`; one that does not keeps the default, which tags every
   * event by its own stream.
   */
  attributes: z.array(attributeSchema).min(1).optional(),
  /**
   * Marks an event that arrives from outside this system. Only a Translation slice may open with one,
   * and only such an event is exempt from "every event has a producer".
   */
  external: z.boolean().optional(),
  /**
   * The mocks for this screen, one entry per state it can be in.
   *
   * Only a `ui` frame has them, and `check-model` says so: a command, an event and a read model are data,
   * so a picture of one is really a picture of the screen that shows it — which is a different box.
   *
   * Nothing here reaches the Mermaid diagram. The DSL has no link and no `click`, so the mocks surface on
   * the browsable page instead, which means adding one changes no rendered SVG and needs no re-render.
   */
  mockups: z.array(mockupSchema).min(1).optional(),
});

export type Frame = z.infer<typeof frameSchema>;

const sliceSchema = z.strictObject({
  id: z
    .string()
    .regex(/^[A-Za-z][A-Za-z0-9-]*$/, 'must start with a letter and contain only letters, digits, or -'),
  /** The capability, as one observable outcome. If it needs "and", it is two slices. */
  name: z.string().min(1),
  pattern: z.enum(PATTERNS),
  status: z.enum(STATUSES),
  /**
   * Who acts, or who sees. Free text because actors are a modelling output, not something a starter can
   * enumerate — the same reason `event-envelope.ts` ships only `{ kind }`.
   */
  actor: z.string().min(1).optional(),
  /**
   * The service that owns this slice — a key of `project.json`'s `deployables`. Optional while the project
   * has one service, because then there is nothing to decide; required from `modelled` once it has two,
   * because a slice that names no owner lands in the first service by gravity rather than by decision.
   * Checked against the manifest, so a renamed service fails here rather than in a build.
   */
  service: z.string().min(1).optional(),
  /**
   * The bounded context this slice belongs to, inside that service — one of the service's `contexts` in
   * `project.json`. Optional while the service holds one context; required from `modelled` once it holds
   * several, for the same reason `service` is: a slice placed in no context lands in whichever
   * `src/<context>/` the implementer reaches for first. Checked against the manifest.
   */
  context: z.string().min(1).optional(),
  /**
   * Stream identity, and therefore the consistency boundary and the concurrency ceiling. One of the two
   * guards a state-change slice may declare, and the default: an append carries the version the decision
   * was made at, and the store refuses it if the stream moved.
   *
   * Required before a state-change slice can be planned — unless it declares a `guard` instead, which is
   * the same question answered the other way. Changing either later migrates the one thing that cannot be
   * migrated, which is why the answer is owed at `planned` and not later.
   */
  stream: z.string().min(1).optional(),
  /**
   * The other guard: a Dynamic Consistency Boundary, drawn per decision out of tags rather than inherited
   * from how streams were laid out.
   *
   * A conditional append is refused if anything matching a tag query arrived since the decision was made,
   * so what this declares is that query's shape — the kinds of thing the boundary is drawn over, and the
   * invariant it protects. The events the decision loads are `folds`, and `check-model` holds the two
   * together: every folded event must be findable by one of these kinds, because a boundary that does not
   * cover the facts a decision used is a guard with a hole in it.
   *
   *     guard:
   *       by: [seat, hold]
   *       because: a seat may be claimed once, and a hold may not exceed its cap
   *
   * A slice declares this **or** `stream`, never both: the boundary is one thing. Use it for the
   * constraint stream-per-aggregate cannot express — capacity and a member's own count, checked together,
   * where either can change under you — and `stream` for everything else, which is most things.
   */
  guard: z
    .strictObject({
      /**
       * The kinds the boundary is drawn over — the `identifies:` values of the attributes it queries by.
       * Each becomes a tag key in the query the append is guarded with.
       */
      by: z
        .array(z.string().regex(/^[a-z][a-z0-9-]*$/, 'must be a lower-case kind like `seat` or `hold`'))
        .min(1),
      /**
       * The invariant this boundary protects, in one sentence. Asked for the same reason
       * `liveBudget.because` is: a boundary with no stated invariant is a query somebody widened until
       * the tests passed.
       */
      because: z.string().min(1),
    })
    .optional(),
  /** Where the feature specification lives, if it has one yet. */
  spec: z.string().min(1).optional(),
  /** Where this slice's Given/When/Then scenarios live. Required once implemented. */
  gwt: z.string().min(1).optional(),
  /** The files that realise this slice. Required once implemented, and checked to exist. */
  code: z.array(z.string().min(1)).optional(),
  /**
   * Slices that must be archived before this one may start — genuine *build* dependencies only.
   *
   * Separate from `reads`: needing another slice's events is solved with synthetic fixtures (Principle V),
   * not by waiting for that slice to ship. `check-model` refuses a `depends_on` set that is exactly the
   * producers of this slice's `reads`, and refuses cycles.
   */
  depends_on: z.array(z.string().min(1)).optional(),
  /**
   * Events this slice consumes that some earlier slice produces. These become the explicit arrows into
   * the slice's first box; without them a read model or processor would appear to come from nowhere.
   */
  reads: z.array(identifier).optional(),
  /**
   * Events this slice's **Decider** folds to reach the state it decides from.
   *
   * A different question from `reads`, and confusing the two is expensive enough to be worth the extra
   * field. `reads` is a *todo list*: it answers "is there work?", it belongs to a projection, and every
   * event in it must come from an earlier slice. `folds` is a Decider's own history: it answers "is this
   * allowed?", it may include events this very slice appends, and every event in it must be **on this
   * slice's own stream** — because that is the only history a Decider can rehydrate from.
   *
   * Optional, because requiring it would invalidate every slice already planned. Checked whenever present.
   */
  folds: z.array(identifier).optional(),
  /**
   * Where this slice's read model lives, and therefore what a query costs.
   *
   * The read side's counterpart to `stream`: one decides the consistency boundary, the other decides
   * whether a query folds the log or reads a row, and both are answered once and paid for afterwards.
   * Required from `planned`, because a slice that reaches a plan with no answer gets whichever one is
   * nearest to hand, and nothing downstream asks the question again. All three are built out of what the
   * skeleton ships — a unit of work for `inline`, a checkpoint store and a catch-up runner for `async` —
   * so what the field buys is the decision, not the machinery.
   *
   *   `live`    folded in memory per query, nothing stored. Strongly consistent and free of
   *             infrastructure, and viable only while the fold stays small — which is what `liveBudget`
   *             is for.
   *   `inline`  written in the same transaction as the append, through the store's `unitOfWork` seam.
   *             The view never lags a write, at the cost of putting projection work on the write path.
   *   `async`   a catch-up subscription with a checkpoint. Scales and isolates failure; the view lags,
   *             and the lag is an operational metric to cap.
   *
   * An `automation`'s read model is its todo list rather than a view, and losing it loses work nothing
   * else records — so `live` is refused there: a fold that only knows the streams the current request
   * wrote cannot be spawned standalone to sweep up what a dead request abandoned.
   */
  materialisation: z.enum(['live', 'inline', 'async']).optional(),
  /**
   * What bounds a `live` fold, and required whenever one is declared.
   *
   * `events` is the ceiling one query may fold and `because` is why that ceiling holds, argued from the
   * stream's own lifetime — a start event and an end event, or a closing-the-books summary. Both exist
   * because "the streams are short" is the assumption every per-query fold rests on, and left unwritten
   * it is an assumption nothing measures, no gate can fail, and no reviewer can dispute.
   */
  liveBudget: z
    .strictObject({
      events: z.number().int().positive(),
      because: z.string().min(1),
    })
    .optional(),
  /** The boxes, in causal order. Nine at most — a tenth is a sign the slice is really two. */
  frames: z.array(frameSchema).min(1).max(9),
});

export type Slice = z.infer<typeof sliceSchema>;

export const modelSchema = z.strictObject({
  version: z.literal(1),
  render: z
    .strictObject({
      /**
       * What each band's swimlanes group by — one setting per band, because Mermaid resolves a namespace
       * within a band and not across the diagram. The defaults are the notation's own picture: actors
       * across the top, one command/read-model lane, streams across the bottom.
       *
       *   ui      actor | context | none     the `ui` and `pcr` boxes. `actor` answers who drives which
       *                                      part of the timeline, and gives a processor its own lane.
       *   data    context | none             the `cmd` and `rmo` boxes. `none` by default: splitting the
       *                                      middle band rarely earns the height it costs.
       *   events  stream | context | none    the `evt` boxes. `stream` is the notation's bottom lanes —
       *                                      the stream an event is appended to, which is also the
       *                                      consistency boundary it was guarded by.
       *
       * `stream` takes the lane name from the slice's `stream` with its placeholder removed, so
       * `order-{orderId}` is the `order` lane and every order stream shares it. A slice that guards with
       * a `guard` instead of a `stream` has no such name and falls back to its `context`; with neither,
       * its events stay in the default lane, which makes an unplaced slice visible rather than guessed at.
       *
       * Mermaid itself still allocates a lane per namespaced box, in every band (mermaid-js/mermaid#7925);
       * `make model` applies the unmerged fix (mermaid-js/mermaid#7986) to the mermaid-cli install it
       * fetches, so the committed SVG groups correctly. Pasting `model.mmd` into mermaid.live will not,
       * until that PR ships. `patch-mermaid-swimlanes.ts` is the local half; delete it when the pin no
       * longer needs it.
       *
       * Two lines still reproduce the upstream bug, without the patch:
       *
       *     eventmodeling
       *
       *     rf 01 ui Sales.A
       *     tf 02 ui Sales.B
       */
      lanes: z
        .strictObject({
          ui: z.enum(UI_LANE_SOURCES).default('actor'),
          data: z.enum(DATA_LANE_SOURCES).default('none'),
          events: z.enum(EVENT_LANE_SOURCES).default('stream'),
        })
        .optional(),
      /**
       * What `lanes` replaced, still read so a model written before it renders what it always rendered:
       * `true` is the UI band grouped by actor and nothing else, `false` is no grouping at all. Naming it
       * beside `lanes` is a contradiction rather than a precedence puzzle — `laneSources` refuses it.
       */
      actorLanes: z.boolean().optional(),
      /**
       * How wide a README segment may get, in frames. The README embeds the timeline in segments of whole
       * slices under this budget, because one image of everything is illegible by about the fourth slice.
       *
       * Measured against mermaid-cli 11.16.0 with realistic identifier lengths, scaled into a ~830px
       * README column:
       *
       *     3 frames (1 slice)     909px    91%   10px type
       *     6 frames (2 slices)   1371px    61%    7px type      ← the default
       *     9 frames (3 slices)   1844px    45%    5px type
       *    12 frames (4 slices)   2269px    37%    4px type
       *
       * Six is the largest that stays readable without clicking through. Raise it if your slices are
       * narrow or your readers always click; lower it to 3 for one slice per image.
       *
       * A slice whose own frame count exceeds the budget still gets a segment to itself — the unit is a
       * whole slice, because half a slice is not a thing anyone can read.
       */
      framesPerSegment: z.number().int().min(3).max(60).default(6),
      /**
       * Where `event-model.yml` publishes the browsable page, if it does.
       *
       * Set it and the README's block becomes a link and stops embedding the segment SVGs entirely. A
       * timeline scaled into a README column is the worse of the two by a wide margin — no zoom, no slice
       * register, no per-slice view — so once the better one has an address, embedding the worse one just
       * adds the part of the section nobody reads. Thirteen slices came out as nine such images stacked
       * above a link to the page that showed all of it properly. `framesPerSegment` above is only
       * consulted while this is unset.
       *
       * Unset is the default and stays the default: most projects publish nothing, and a generator that
       * assumed otherwise would produce a README full of dead links.
       *
       * Declared rather than derived, which is why nothing in the workflow writes it.
       * `https://<org>.github.io/<repo>/` is a guess that is wrong for a custom domain, and wrong for every
       * project that took the workflow's advice and deleted the `deploy` job because its plan would have
       * made the site public. Deriving it from `origin` would also make `check-model` depend on which
       * remote a clone happens to have, and a gate that answers differently in a fork is not a gate. The
       * deploy job prints the URL as its environment URL, which is where to read it from after the first
       * successful run.
       */
      page: z.url().optional(),
    })
    .default({ framesPerSegment: 6 }),
  slices: z.array(sliceSchema),
});

export type Model = z.infer<typeof modelSchema>;

const DEFAULT_LANES: Readonly<Record<LaneBand, LaneSource>> = {
  ui: 'actor',
  data: 'none',
  events: 'stream',
};

/**
 * What each band groups by, from `lanes` or from the `actorLanes` it replaced.
 *
 * `actorLanes` pins every band rather than only the one it named: it meant "actor lanes and nothing
 * else", so a model carrying it must keep rendering that and not silently gain the stream lanes the
 * current defaults would give it.
 */
export function laneSources(model: Model): Readonly<Record<LaneBand, LaneSource>> {
  const { lanes, actorLanes } = model.render;
  if (lanes !== undefined && actorLanes !== undefined) {
    throw new Error(
      'render.lanes and render.actorLanes both set — actorLanes is what lanes replaced. Keep lanes and ' +
        'delete actorLanes.',
    );
  }
  if (lanes !== undefined) return lanes;
  if (actorLanes !== undefined) {
    return { ui: actorLanes ? 'actor' : 'none', data: 'none', events: 'none' };
  }
  return DEFAULT_LANES;
}

/**
 * The lane name a stream identity gives, which is the identity with its placeholder taken out:
 * `order-{orderId}` is the `order` lane, so every order stream is one lane rather than one per order.
 */
export function streamLaneName(stream: string): string | undefined {
  const withoutPlaceholders = stream.replaceAll(/\{[^}]*\}/g, ' ');
  const name = withoutPlaceholders.replaceAll(/[^A-Za-z0-9]+/g, ' ').trim();
  return name.length > 0 ? name : undefined;
}

/** Frame numbers are spaced ten apart per slice, so a slice can gain a box without renumbering the rest. */
export const FRAMES_PER_SLICE = 10;

export type NumberedFrame = Frame & {
  /** The Mermaid time-frame number. Derived: slice position and frame position. */
  n: number;
  sliceId: string;
};

/** Flattens the model into the boxes the renderer draws, in timeline order, with their numbers assigned. */
export function numberFrames(model: Model): NumberedFrame[] {
  return model.slices.flatMap((slice, sliceIndex) =>
    slice.frames.map((frame, frameIndex) => ({
      ...frame,
      n: (sliceIndex + 1) * FRAMES_PER_SLICE + frameIndex,
      sliceId: slice.id,
    })),
  );
}

/**
 * Where each event is first produced, by name.
 *
 * "First" matters: an event legitimately has more than one producer, and a reader that resolved to the
 * last one would draw its arrow from a box further right than the consumer, which Mermaid silently drops.
 */
export function eventProducers(frames: readonly NumberedFrame[]): Map<string, NumberedFrame> {
  const producers = new Map<string, NumberedFrame>();
  for (const frame of frames) {
    if (frame.type === 'evt' && frame.external !== true && !producers.has(frame.name)) {
      producers.set(frame.name, frame);
    }
  }
  return producers;
}

/** A contiguous run of whole slices, rendered as one image small enough to read. */
export interface Segment {
  /** 1-based, and part of the artifact filename. */
  readonly index: number;
  readonly sliceIds: readonly string[];
}

/**
 * Split the timeline into segments of whole slices, each under `render.framesPerSegment`.
 *
 * Greedy and order-preserving, so a segment is always a contiguous run and the segments in sequence are
 * the timeline. Splitting on any other axis — by actor, by status, by context — would produce images that
 * are each readable and together no longer a timeline, which is the one thing the global model is for.
 */
export function segmentModel(model: Model): Segment[] {
  const budget = model.render.framesPerSegment;
  const segments: { sliceIds: string[]; frames: number }[] = [];

  for (const slice of model.slices) {
    const current = segments.at(-1);
    // A slice bigger than the whole budget still travels alone rather than being cut in half.
    if (current === undefined || current.frames + slice.frames.length > budget) {
      segments.push({ sliceIds: [slice.id], frames: slice.frames.length });
    } else {
      current.sliceIds.push(slice.id);
      current.frames += slice.frames.length;
    }
  }

  return segments.map((segment, index) => ({ index: index + 1, sliceIds: segment.sliceIds }));
}

/**
 * `S1 – S4`, or just `S1` where a segment holds one slice.
 *
 * Shared by the README block and the browsable page on purpose: a segment labelled two different ways in
 * two views is two segments as far as a reader is concerned.
 */
export function segmentRange(segment: Segment): string {
  const first = segment.sliceIds.at(0) ?? '';
  const last = segment.sliceIds.at(-1) ?? '';
  return first === last ? first : `${first} – ${last}`;
}

export function parseModel(raw: unknown): Model {
  return modelSchema.parse(raw);
}
