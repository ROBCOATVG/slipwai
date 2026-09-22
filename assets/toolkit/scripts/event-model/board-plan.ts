/**
 * The canvas as geometry: every box, label and arrow with a centre, a size and a colour — and nothing
 * about how any of it is written down.
 *
 * Pure on purpose. This module reads no file, no clock and no network, and knows no output format; it
 * turns a parsed `Model` into a `BoardPlan`, and `drawio.ts` turns the plan into a file. The split is what
 * made the destination swappable: the layout here was first written for a different canvas, and when that
 * canvas was dropped not one line of geometry needed revisiting. Keep it strict and the next change costs
 * the same.
 *
 * Everything rests on the plan being a pure function of the model. Same model in, same plan out, so the
 * file serialised from it is byte-identical and `check-drawio` can compare it. So: no generated ids (every
 * key is built from the model's own frame numbers, slice ids and band names), and no collection ordered by
 * anything but the model — where an order is chosen, it is sorted here.
 *
 * ── Coordinates ──────────────────────────────────────────────────────────────────────────────────────
 * An item's `x`/`y` is its CENTRE, relative to the frame's top-left corner. The serialiser converts to a
 * top-left corner once, at the edge. Centres keep the arithmetic simple, and frame-relative positions are
 * exactly what mxGraph gives a container's child, so there is no offset to get wrong.
 *
 * ── The picture ──────────────────────────────────────────────────────────────────────────────────────
 * One column per box, left to right in frame-number order — the same order the Mermaid timeline reads in,
 * so a box that sits fourth here sits fourth in `model.svg`. Rows are the notation's bands, `ui` on top,
 * `data` in the middle, `events` underneath, and a lane within a band is its own row: the same lane the
 * SVG puts the box in, because both renderers ask `model.ts`'s `laneName` for it, and the same arrows,
 * because both ask `sliceInputs`. Neither renderer decides either; only the spelling is its own. A gutter
 * on the left holds the lane labels, a strip above the bands one caption per slice, and a legend above that.
 *
 * ── Arrows ───────────────────────────────────────────────────────────────────────────────────────────
 * A generated board is unreadable for one reason: a slice can read an event modelled thirty columns
 * earlier, and an arrow drawn straight between the two crosses every box in between at exactly the height
 * a reader is following. Three moves solve it:
 *
 *   1. A connector has a `kind`. `sequence` — step 4 follows step 3, always adjacent columns — and `reads` —
 *      this slice folds that event, at any distance — are different relationships and are drawn differently.
 *   2. A reads arrow spanning more than one column detours: it leaves its source underneath, runs along a
 *      corridor below the bands where there is nothing to cross, and rises into its target. Every box owns
 *      its column, so both vertical runs pass through empty space. A neighbouring read stays direct — a
 *      detour costs more than it saves when there is nothing in the gap to hit.
 *   3. One trunk per source event, not one corridor per arrow. Every read of one event shares that event's
 *      corridor, so the arrows lie on the same pixels from the event down and along it, and peel off upward
 *      at each reader's own column: a bus with a tap per reader, and no junction object needed. Corridors
 *      are packed by interval colouring — trunks sorted by left edge, each given the topmost corridor whose
 *      spans do not overlap it — which is optimal once the sort is by left edge.
 *
 * A reader also gets a caption under its own box naming every event it reads, sorted: one caption per
 * reader rather than one label per arrow, because twelve labels converging on one point are a smudge. It
 * lists every read, including the ones drawn directly — a caption that named only the detouring ones would
 * be finished and believed.
 */
import {
  BAND_OF,
  eventProducers,
  FRAME_TYPES,
  LANE_BANDS,
  laneName,
  laneSources,
  numberFrames,
  sliceInputs,
  type Attribute,
  type LaneBand,
  type LaneSources,
  type Model,
  type NumberedFrame,
  type Slice,
} from './model.ts';
import { SWATCHES } from './palette.ts';

// Geometry, in board pixels. A box is wide rather than tall because it holds an identifier plus a line of
// worked example data.
export const BOX_WIDTH = 240;
export const BOX_HEIGHT = 120;
export const COLUMN_GAP = 60;
export const ROW_GAP = 48;
/** The strip on the left holding the lane labels, inside the frame. */
export const GUTTER = 260;
/** The strip above the bands, one caption per slice. */
export const SLICE_HEADER_HEIGHT = 44;
/** The strip above that. */
export const LEGEND_HEIGHT = 48;
/** The frame's margin. */
export const PADDING = 80;
/** Characters of example data before a line stops being readable and starts being noise. */
export const DETAIL_LIMIT = 150;
/** Bands' bottom edge to the first corridor. */
export const CORRIDOR_TOP_GAP = 56;
/** Between corridors. */
export const CORRIDOR_GAP = 26;
export const CAPTION_FONT = 11;
/** Box bottom to caption top. */
export const CAPTION_DROP = 14;
/** For counting the lines a caption wraps to, there being no renderer to measure text with. */
export const CAPTION_CHAR_WIDTH = CAPTION_FONT * 0.52;

export const BOX_FONT = 12;
export const LANE_LABEL_FONT = 14;
export const SLICE_CAPTION_FONT = 14;
export const LEGEND_TITLE_FONT = 16;
export const LEGEND_FONT = 12;

const LEGEND_SWATCH_WIDTH = 200;
const LEGEND_SWATCH_HEIGHT = 32;
const LEGEND_GAP = 20;
const LEGEND_NOTE_WIDTH = 600;

export interface PlannedItem {
  /** Unique within the plan; the serialiser derives the cell id from it. */
  readonly key: string;
  readonly kind: 'box' | 'text';
  /** Centre, relative to the frame's top-left. */
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  /** Inline HTML. Model text inside it is already HTML-escaped, so nothing here can close a tag. */
  readonly content: string;
  readonly fontSize: number;
  readonly align: 'left' | 'center';
  /** A box's swatch; a text item has neither fill nor stroke. */
  readonly fill?: string;
  readonly stroke?: string;
  /** A wireframe is square; everything else is rounded. */
  readonly rounded?: boolean;
}

export interface PlannedFrame {
  readonly key: 'frame';
  readonly title: string;
  /** Centre, on the canvas. */
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface PlannedConnector {
  /** Plan key of the source box. */
  readonly from: string;
  /** Plan key of the target box. */
  readonly to: string;
  readonly kind: 'sequence' | 'reads';
  /** Set only when this arrow detours through a corridor. */
  readonly corridorY?: number;
  /** The event's name; set on `reads` arrows only. The captions are built from it. */
  readonly sourceName?: string;
}

export interface BoardPlan {
  readonly frame: PlannedFrame;
  readonly items: readonly PlannedItem[];
  readonly connectors: readonly PlannedConnector[];
}

const BAND_TITLES: Readonly<Record<LaneBand, string>> = {
  ui: 'UI / Automation',
  data: 'Command / Read model',
  events: 'Events',
};

export function frameKey(n: number): string {
  return `frame-${String(n)}`;
}

/** Model text on its way into a label: nothing a person typed into `data` may close a tag. */
export function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function truncate(value: string): string {
  return value.length > DETAIL_LIMIT ? `${value.slice(0, DETAIL_LIMIT - 1)}…` : value;
}

/** An identifying attribute is starred, exactly as the Mermaid diagram stars it. */
function attributeLine(attributes: readonly Attribute[]): string {
  return attributes.map((attribute) => (attribute.identifies === undefined ? attribute.name : `${attribute.name}*`)).join(', ');
}

function boxContent(frame: NumberedFrame): string {
  const detail =
    frame.attributes !== undefined
      ? attributeLine(frame.attributes)
      : (frame.data ?? '').replaceAll(/\s+/g, ' ').trim();
  const head = `<p><b>${escapeHtml(frame.name)}</b></p>`;
  return detail === '' ? head : `${head}<p>${escapeHtml(truncate(detail))}</p>`;
}

interface Row {
  readonly band: LaneBand;
  /** The lane's own name; `undefined` for a band's default lane. */
  readonly lane: string | undefined;
  /** What the gutter says; `undefined` for a band that groups by nothing. */
  readonly label: string | undefined;
}

/**
 * The rows, band by band, lanes within a band in order of first appearance on the timeline — and which row
 * each box is in.
 */
function planRows(
  model: Model,
  frames: readonly NumberedFrame[],
  lanes: LaneSources,
): { rows: Row[]; rowOf: Map<number, number> } {
  const sliceById = new Map(model.slices.map((slice) => [slice.id, slice]));
  const perBand = new Map<LaneBand, Map<string | undefined, Row>>(LANE_BANDS.map((band) => [band, new Map()]));
  const laneOf = new Map<number, string | undefined>();

  for (const frame of frames) {
    const band = BAND_OF[frame.type];
    const slice = sliceById.get(frame.sliceId);
    /* c8 ignore next -- a frame's sliceId always names a slice of this model */
    if (slice === undefined) throw new Error(`frame ${String(frame.n)} names no slice`);
    // The model's own answer to which lane a box is in — the same one the Mermaid diagram namespaces by.
    const lane = laneName(frame, slice, lanes);
    laneOf.set(frame.n, lane);
    const bandRows = perBand.get(band);
    /* c8 ignore next -- every band was seeded above */
    if (bandRows === undefined) throw new Error(`no band ${band}`);
    if (!bandRows.has(lane)) {
      const label =
        lanes[band] === 'none' ? undefined : lane === undefined ? BAND_TITLES[band] : `${BAND_TITLES[band]} · ${lane}`;
      bandRows.set(lane, { band, lane, label });
    }
  }

  const rows: Row[] = LANE_BANDS.flatMap((band) => [...(perBand.get(band)?.values() ?? [])]);
  const rowOf = new Map<number, number>();
  for (const frame of frames) {
    const band = BAND_OF[frame.type];
    const lane = laneOf.get(frame.n);
    rowOf.set(
      frame.n,
      rows.findIndex((row) => row.band === band && row.lane === lane),
    );
  }
  return { rows, rowOf };
}

function laneLabelContent(row: Row): string {
  /* c8 ignore next -- only called for a labelled row */
  if (row.label === undefined) return '';
  return row.lane === undefined
    ? `<p><b>${escapeHtml(BAND_TITLES[row.band])}</b></p>`
    : `<p><b>${escapeHtml(BAND_TITLES[row.band])}</b></p><p>${escapeHtml(row.lane)}</p>`;
}

function sliceCaptionContent(slice: Slice): string {
  const actor = slice.actor === undefined ? '' : ` · ${escapeHtml(slice.actor)}`;
  return (
    `<p><b>${escapeHtml(slice.id)}</b> — ${escapeHtml(slice.name)}</p>` +
    `<p>${slice.pattern}${actor} · ${slice.status}</p>`
  );
}

/** How many lines a caption wraps to inside a box's width, over-estimated rather than under. */
function captionHeight(text: string): number {
  const perLine = Math.floor(BOX_WIDTH / CAPTION_CHAR_WIDTH);
  const lines = Math.max(1, Math.ceil(text.length / perLine));
  return lines * (CAPTION_FONT + 4) + 8;
}

/** Same column apart means neighbours, and a direct arrow between neighbours crosses nothing. */
function isLong(sourceX: number, targetX: number): boolean {
  return Math.abs(targetX - sourceX) > BOX_WIDTH + COLUMN_GAP;
}

interface Trunk {
  readonly from: string;
  left: number;
  right: number;
  readonly members: number[];
}

/**
 * Corridor assignment: one trunk per source event, packed by interval colouring. Returns the corridor
 * index of every detouring connector, by its position in `connectors`, and how many corridors there are.
 */
function routeCorridors(
  connectors: readonly PlannedConnector[],
  centreX: (key: string) => number,
): { corridorOf: Map<number, number>; corridors: number } {
  const trunks = new Map<string, Trunk>();
  connectors.forEach((connector, index) => {
    if (connector.kind !== 'reads') return;
    const sourceX = centreX(connector.from);
    const targetX = centreX(connector.to);
    if (!isLong(sourceX, targetX)) return;
    const trunk = trunks.get(connector.from) ?? { from: connector.from, left: sourceX, right: sourceX, members: [] };
    trunk.left = Math.min(trunk.left, targetX);
    trunk.right = Math.max(trunk.right, targetX);
    trunk.members.push(index);
    trunks.set(connector.from, trunk);
  });

  // Left edge first is what makes the greedy choice optimal; the rest of the order only has to be stable.
  const sorted = [...trunks.values()].sort(
    (a, b) => a.left - b.left || a.right - b.right || (a.from < b.from ? -1 : a.from > b.from ? 1 : 0),
  );
  const rightEdges: number[] = [];
  const corridorOf = new Map<number, number>();
  for (const trunk of sorted) {
    // Strictly clear of the corridor's last span: two trunks meeting at one column would put two risers on
    // the same pixels, and a reader could not tell whose tap it was.
    let corridor = rightEdges.findIndex((right) => right < trunk.left);
    if (corridor === -1) {
      rightEdges.push(trunk.right);
      corridor = rightEdges.length - 1;
    } else {
      rightEdges[corridor] = trunk.right;
    }
    for (const member of trunk.members) corridorOf.set(member, corridor);
  }
  return { corridorOf, corridors: rightEdges.length };
}

function plural(count: number, noun: string): string {
  return `${String(count)} ${noun}${count === 1 ? '' : 's'}`;
}

/** The whole model as one canvas. Pure: same model, same plan. */
export function planBoard(model: Model): BoardPlan {
  const frames = numberFrames(model);
  const producers = eventProducers(frames);
  const lanes = laneSources(model);
  const { rows, rowOf } = planRows(model, frames, lanes);

  const legendTop = PADDING;
  const headerTop = legendTop + LEGEND_HEIGHT + ROW_GAP;
  const bandsTop = headerTop + SLICE_HEADER_HEIGHT + ROW_GAP;
  const rowCentreY = (row: number): number => bandsTop + row * (BOX_HEIGHT + ROW_GAP) + BOX_HEIGHT / 2;
  const bandsBottom = rows.length === 0 ? bandsTop : bandsTop + rows.length * (BOX_HEIGHT + ROW_GAP) - ROW_GAP;
  const columnCentreX = (column: number): number => PADDING + GUTTER + column * (BOX_WIDTH + COLUMN_GAP) + BOX_WIDTH / 2;
  const columnsRight =
    frames.length === 0 ? PADDING + GUTTER : PADDING + GUTTER + frames.length * (BOX_WIDTH + COLUMN_GAP) - COLUMN_GAP;

  const items: PlannedItem[] = [];

  // The legend: a title in the gutter, one swatch per kind of box, and what the two arrows mean.
  items.push({
    key: 'legend-title',
    kind: 'text',
    x: PADDING + GUTTER / 2,
    y: legendTop + LEGEND_HEIGHT / 2,
    width: GUTTER,
    height: LEGEND_HEIGHT,
    content: '<p><b>Legend</b></p>',
    fontSize: LEGEND_TITLE_FONT,
    align: 'left',
  });
  let legendX = PADDING + GUTTER;
  for (const type of FRAME_TYPES) {
    const swatch = SWATCHES[type];
    items.push({
      key: `legend-${type}`,
      kind: 'box',
      x: legendX + LEGEND_SWATCH_WIDTH / 2,
      y: legendTop + LEGEND_HEIGHT / 2,
      width: LEGEND_SWATCH_WIDTH,
      height: LEGEND_SWATCH_HEIGHT,
      content: `<p><b>${escapeHtml(swatch.label)}</b></p>`,
      fontSize: LEGEND_FONT,
      align: 'center',
      fill: swatch.fill,
      stroke: swatch.stroke,
      rounded: type !== 'ui',
    });
    legendX += LEGEND_SWATCH_WIDTH + LEGEND_GAP;
  }
  items.push({
    key: 'legend-arrows',
    kind: 'text',
    x: legendX + LEGEND_NOTE_WIDTH / 2,
    y: legendTop + LEGEND_HEIGHT / 2,
    width: LEGEND_NOTE_WIDTH,
    height: LEGEND_HEIGHT,
    content: '<p>solid arrow: the next step · dashed arrow: reads an earlier event, named under the reader</p>',
    fontSize: LEGEND_FONT,
    align: 'left',
  });
  const legendRight = legendX + LEGEND_NOTE_WIDTH;

  // Lane labels, in the gutter, one per row that has something to say.
  rows.forEach((row, index) => {
    if (row.label === undefined) return;
    items.push({
      key: `lane-${row.band}-${String(index)}`,
      kind: 'text',
      x: PADDING + GUTTER / 2,
      y: rowCentreY(index),
      width: GUTTER - LEGEND_GAP,
      height: BOX_HEIGHT,
      content: laneLabelContent(row),
      fontSize: LANE_LABEL_FONT,
      align: 'left',
    });
  });

  // One caption per slice, centred over the columns its boxes occupy.
  let column = 0;
  for (const slice of model.slices) {
    const first = column;
    const last = column + slice.frames.length - 1;
    items.push({
      key: `slice-${slice.id}`,
      kind: 'text',
      x: (columnCentreX(first) + columnCentreX(last)) / 2,
      y: headerTop + SLICE_HEADER_HEIGHT / 2,
      width: (last - first) * (BOX_WIDTH + COLUMN_GAP) + BOX_WIDTH,
      height: SLICE_HEADER_HEIGHT,
      content: sliceCaptionContent(slice),
      fontSize: SLICE_CAPTION_FONT,
      align: 'center',
    });
    column = last + 1;
  }

  // The boxes: one column each, in the row its band and lane give it.
  const boxes = new Map<string, PlannedItem>();
  frames.forEach((frame, index) => {
    const swatch = SWATCHES[frame.type];
    const box: PlannedItem = {
      key: frameKey(frame.n),
      kind: 'box',
      x: columnCentreX(index),
      y: rowCentreY(rowOf.get(frame.n) ?? 0),
      width: BOX_WIDTH,
      height: BOX_HEIGHT,
      content: boxContent(frame),
      fontSize: BOX_FONT,
      align: 'center',
      fill: swatch.fill,
      stroke: swatch.stroke,
      rounded: frame.type !== 'ui',
    };
    boxes.set(box.key, box);
    items.push(box);
  });

  // Arrows. Causal order within a slice first, then what each slice reads from earlier ones — into its
  // first box, as the Mermaid diagram draws it. The first writer of a pair keeps it: a step that happens
  // also to be a read stays one arrow rather than two drawn along the same line.
  const connectors: PlannedConnector[] = [];
  const drawn = new Set<string>();
  const connect = (connector: PlannedConnector): void => {
    const pair = `${connector.from}>${connector.to}`;
    if (drawn.has(pair)) return;
    drawn.add(pair);
    connectors.push(connector);
  };
  for (const slice of model.slices) {
    const own = frames.filter((frame) => frame.sliceId === slice.id);
    own.slice(1).forEach((frame, index) => {
      const previous = own[index];
      /* c8 ignore next -- `slice(1)` guarantees a predecessor */
      if (previous === undefined) return;
      connect({ from: frameKey(previous.n), to: frameKey(frame.n), kind: 'sequence' });
    });
    const target = own[0];
    if (target === undefined) continue;
    // Exactly the arrows the Mermaid diagram draws: `sliceInputs` is the model's own resolution of `reads`.
    // A read nothing produces is `check-model`'s to report; a canvas with one arrow fewer is still a canvas.
    for (const n of sliceInputs(slice, producers)) {
      const producer = frames.find((frame) => frame.n === n);
      /* c8 ignore next -- these numbers came out of these same frames */
      if (producer === undefined) continue;
      connect({ from: frameKey(n), to: frameKey(target.n), kind: 'reads', sourceName: producer.name });
    }
  }

  // Captions: under every reader, every event it reads, sorted — before the corridors, which must clear them.
  let deepestCaptionBottom = bandsBottom;
  for (const slice of model.slices) {
    const reads = [...new Set(slice.reads ?? [])].sort();
    const target = frames.find((frame) => frame.sliceId === slice.id);
    if (reads.length === 0 || target === undefined) continue;
    const box = boxes.get(frameKey(target.n));
    /* c8 ignore next -- every frame became a box above */
    if (box === undefined) continue;
    const text = `reads ${reads.join(', ')}`;
    const height = captionHeight(text);
    const y = box.y + box.height / 2 + CAPTION_DROP + height / 2;
    deepestCaptionBottom = Math.max(deepestCaptionBottom, y + height / 2);
    items.push({
      key: `reads-${box.key}`,
      kind: 'text',
      x: box.x,
      y,
      width: BOX_WIDTH,
      height,
      content: `<p>${escapeHtml(text)}</p>`,
      fontSize: CAPTION_FONT,
      align: 'center',
    });
  }

  // Routing, before the frame's height: the frame has to contain its own wiring.
  const centreX = (key: string): number => boxes.get(key)?.x ?? 0;
  const { corridorOf, corridors } = routeCorridors(connectors, centreX);
  const corridorBase = deepestCaptionBottom + CORRIDOR_TOP_GAP;
  const routed = connectors.map((connector, index) => {
    const corridor = corridorOf.get(index);
    return corridor === undefined ? connector : { ...connector, corridorY: corridorBase + corridor * CORRIDOR_GAP };
  });
  const wiringBottom = corridors === 0 ? deepestCaptionBottom : corridorBase + corridors * CORRIDOR_GAP;

  const width = Math.max(columnsRight, legendRight) + PADDING;
  const height = wiringBottom + PADDING;
  return {
    frame: {
      key: 'frame',
      title: `Event model · ${plural(model.slices.length, 'slice')}`,
      x: width / 2,
      y: height / 2,
      width,
      height,
    },
    items,
    connectors: routed,
  };
}
