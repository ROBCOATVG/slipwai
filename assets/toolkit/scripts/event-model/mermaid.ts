/**
 * Turns the model into Mermaid `eventmodeling` source.
 *
 * ── Four behaviours of the DSL this generator is built around ────────────────────────────────────────
 * Established by rendering probes against mermaid 11.16.1, because none of them are in the documentation
 * and each one is a silent failure rather than an error:
 *
 *   1. Arrows are *inferred* from adjacency in text order. Text order is causal order; the frame number
 *      only decides horizontal position. Two boxes next to each other in the file get an arrow whether
 *      or not you meant one.
 *   2. An explicit `->> n` list *replaces* inference for that box rather than adding to it. So a box with
 *      explicit inputs never also picks up a spurious arrow from whatever precedes it in the file.
 *   3. `rf` (reset frame) breaks inference — and **silently discards any `->>` list given to it**. It
 *      parses and renders with no arrows at all. So a box needing explicit inputs must be `tf`, never `rf`.
 *   4. `title` is a syntax error. The diagram carries no caption; the surrounding page provides it.
 *
 * Which gives the rule this file implements: a slice whose first box has inputs from an earlier slice
 * opens with `tf … ->> n`, and a slice that starts from nothing opens with `rf`. Everything after the
 * first box is `tf`, letting inference draw the chain.
 */
import { createHash } from 'node:crypto';

import {
  BAND_OF,
  eventProducers,
  laneSources,
  numberFrames,
  streamLaneName,
  type Attribute,
  type LaneBand,
  type LaneSource,
  type Model,
  type NumberedFrame,
  type Slice,
} from './model.ts';

type LaneSources = Readonly<Record<LaneBand, LaneSource>>;

export const HASH_MARKER = 'em-source-sha256';

/**
 * Mermaid's inline data is delimited by braces and cannot be escaped, so a brace or a newline in the
 * example data would end the box early and corrupt everything after it. Squashing them is preferable to
 * rejecting the model: the data is illustrative, and losing a brace costs nothing a reader needs.
 */
function inlineData(data: string): string {
  const flattened = data.replaceAll(/[{}]/g, '').replaceAll(/\s+/g, ' ').trim();
  return flattened.length > 0 ? ` { ${flattened} }` : '';
}

/**
 * An event's attributes as the box's data, with the identifying ones starred.
 *
 * `seatId*` rather than `seatId: seat` because the diagram has one line to spend and the reader's
 * question is "what does this event identify" — the kind is on `model.html`, where there is room. The
 * convention is the platform's own, which is worth keeping for anybody arriving from a drawing of the
 * same model.
 */
function inlineAttributes(attributes: readonly Attribute[]): string {
  return inlineData(
    attributes
      .map((attribute) => (attribute.identifies === undefined ? attribute.name : `${attribute.name}*`))
      .join(', '),
  );
}

/** Mermaid's namespace is one dot-separated segment, so anything that is not a letter or digit goes. */
function namespaced(namespace: string, name: string): string {
  const cleaned = namespace.replaceAll(/[^A-Za-z0-9]/g, '');
  return cleaned.length > 0 ? `${cleaned}.${name}` : name;
}

/**
 * The box's identifier, namespaced by whatever its own band groups by.
 *
 * Per band rather than per diagram, because that is how Mermaid resolves it — which is what lets the
 * actors run across the top and the streams across the bottom of the same picture, as the notation draws
 * it. A band whose source the slice cannot answer (no actor, no stream, no context) leaves its boxes
 * un-namespaced, so they fall into that band's default lane instead of inventing one.
 */
function entityIdentifier(frame: NumberedFrame, slice: Slice, lanes: LaneSources): string {
  const namespace = laneNamespace(frame, slice, lanes);
  return namespace === undefined ? frame.name : namespaced(namespace, frame.name);
}

function laneNamespace(frame: NumberedFrame, slice: Slice, lanes: LaneSources): string | undefined {
  switch (lanes[BAND_OF[frame.type]]) {
    case 'none':
      return undefined;
    case 'actor':
      return slice.actor;
    case 'context':
      return slice.context;
    case 'stream':
      // A slice guarding with a `guard` rather than a `stream` has no stream to name, and its context is
      // the next-coarsest true answer. Neither, and the event keeps the default lane.
      return slice.stream === undefined ? slice.context : (streamLaneName(slice.stream) ?? slice.context);
  }
}

function frameLine(
  frame: NumberedFrame,
  slice: Slice,
  lanes: LaneSources,
  relations: readonly number[],
  isFirst: boolean,
): string {
  // Behaviour 3: only `tf` honours a relation list, so a box with inputs must be `tf` even though it
  // opens a slice. `rf` is reserved for a slice that genuinely starts from nothing.
  const token = isFirst && relations.length === 0 ? 'rf' : 'tf';
  const identifier = entityIdentifier(frame, slice, lanes);
  const arrows = relations.map((n) => ` ->> ${String(n)}`).join('');
  const data =
    frame.attributes !== undefined
      ? inlineAttributes(frame.attributes)
      : frame.data === undefined
        ? ''
        : inlineData(frame.data);
  return `${token} ${String(frame.n)} ${frame.type} ${identifier}${arrows}${data}`;
}

/** The frame numbers a slice's first box draws its arrows from, ascending and deduplicated. */
function inputsFor(slice: Slice, producers: Map<string, NumberedFrame>): number[] {
  const resolved = (slice.reads ?? [])
    .map((name) => producers.get(name)?.n)
    .filter((n): n is number => n !== undefined);
  return [...new Set(resolved)].sort((a, b) => a - b);
}

function sliceComment(slice: Slice): string {
  const actor = slice.actor === undefined ? '' : ` · ${slice.actor}`;
  return `%% ${slice.id} — ${slice.name} [${slice.pattern}${actor} · ${slice.status}]`;
}

function stamp(body: string): string {
  const hash = createHash('sha256').update(body).digest('hex');
  return `%% ${HASH_MARKER}: ${hash}\n%% Generated from docs/event-model/model.yaml by \`make model\`. Do not edit.\n${body}`;
}

/**
 * Any view of the model: the whole timeline, one segment of it, or one slice.
 *
 * The three differ only in which slices are in scope, so they are one function. What falls out of that is
 * the property that makes the views comparable: **frame numbers are global**, so a box has the same number
 * in the segment image, the slice image, and the whole timeline. A reader moving between them is looking
 * at the same model rather than three drawings of it.
 *
 * An input produced by a slice *outside* the scope is drawn as a source box, keeping its global number.
 * Those are `rf` because nothing in view produces them, and behaviour 3 costs nothing here: the arrows are
 * declared on the consuming box, not on the source.
 */
function renderScoped(model: Model, sliceIds: readonly string[]): string {
  const inScope = new Set(sliceIds);
  const frames = numberFrames(model);
  const producers = eventProducers(frames);
  const lanes = laneSources(model);
  const slices = model.slices.filter((slice) => inScope.has(slice.id));

  const consumedNumbers: number[] = [];

  const blocks = slices.map((slice) => {
    const inputs = inputsFor(slice, producers);
    for (const n of inputs) {
      const producer = frames.find((frame) => frame.n === n);
      if (producer !== undefined && !inScope.has(producer.sliceId)) {
        consumedNumbers.push(n);
      }
    }
    const lines = frames
      .filter((frame) => frame.sliceId === slice.id)
      .map((frame, index) => frameLine(frame, slice, lanes, index === 0 ? inputs : [], index === 0));
    return [sliceComment(slice), ...lines].join('\n');
  });

  const sources = [...new Set(consumedNumbers)]
    .sort((a, b) => a - b)
    .map((n) => {
      const source = frames.find((frame) => frame.n === n);
      /* c8 ignore next -- these numbers came out of these same frames */
      if (source === undefined) {
        throw new Error(`unresolved input frame ${String(n)}`);
      }
      // Namespaced by the slice that *produces* it, not the one consuming it: an event belongs to the
      // stream it was appended to, and drawing it in the consumer's lane would put the same event in two
      // places depending on which view you opened.
      const producer = model.slices.find((slice) => slice.id === source.sliceId);
      /* c8 ignore next -- a frame's sliceId always names a slice of this model */
      if (producer === undefined) {
        throw new Error(`frame ${String(n)} names no slice`);
      }
      return `rf ${String(n)} ${source.type} ${entityIdentifier(source, producer, lanes)}`;
    });

  const consumed = sources.length > 0 ? `%% consumed from earlier slices\n${sources.join('\n')}\n\n` : '';
  return stamp(`eventmodeling\n\n${consumed}${blocks.join('\n\n')}\n`);
}

/** The one global diagram: every slice, in timeline order. Nothing is consumed from outside it. */
export function renderGlobalMermaid(model: Model): string {
  return renderScoped(model, model.slices.map((slice) => slice.id));
}

/**
 * One segment of the timeline — the unit the README embeds, because one image of everything is illegible
 * by about the fourth slice. Slices earlier in the timeline appear as consumed sources where this segment
 * reads their events, so a segment is still honest about where its inputs come from.
 */
export function renderSegmentMermaid(model: Model, sliceIds: readonly string[]): string {
  if (sliceIds.length === 0) {
    throw new Error('a segment with no slices cannot be rendered');
  }
  return renderScoped(model, sliceIds);
}

/** One slice on its own, with the events it consumes drawn in as sources. */
export function renderSliceMermaid(model: Model, sliceId: string): string {
  if (!model.slices.some((slice) => slice.id === sliceId)) {
    throw new Error(`no slice ${sliceId} in the model`);
  }
  return renderScoped(model, [sliceId]);
}

/** Reads the stamp back out of generated Mermaid or of an SVG rendered from it. */
export function extractHash(text: string): string | undefined {
  return new RegExp(`${HASH_MARKER}: ([0-9a-f]{64})`).exec(text)?.[1];
}
