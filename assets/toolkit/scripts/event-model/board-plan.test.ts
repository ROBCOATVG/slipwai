/**
 * The layout, over the worked example. No file, no browser, no network: `planBoard` is pure, and these
 * tests hold it to that by never giving it anything but a parsed model.
 *
 * Run with: make model-drawio-test
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  BOX_HEIGHT,
  BOX_WIDTH,
  COLUMN_GAP,
  DETAIL_LIMIT,
  frameKey,
  planBoard,
  type BoardPlan,
  type PlannedItem,
} from './board-plan.ts';
import { exampleModel, hubModel, LONG_DATA } from './example-model.ts';
import { FRAME_TYPES, numberFrames, type FrameType, type Model } from './model.ts';
import { SWATCHES } from './palette.ts';

const model = exampleModel();
const plan = planBoard(model);
const frames = numberFrames(model);

function item(of: BoardPlan, key: string): PlannedItem {
  const found = of.items.find((candidate) => candidate.key === key);
  assert.ok(found !== undefined, `no item ${key}`);
  return found;
}

function boxes(of: BoardPlan): PlannedItem[] {
  return of.items.filter((candidate) => candidate.key.startsWith('frame-'));
}

function typeOf(key: string): FrameType {
  const n = Number(key.slice('frame-'.length));
  const frame = frames.find((candidate) => candidate.n === n);
  assert.ok(frame !== undefined, `${key} is no frame of the example`);
  return frame.type;
}

const bottomOf = (box: PlannedItem): number => box.y + box.height / 2;

// ── Boxes and rows ───────────────────────────────────────────────────────────────────────────────────

test('every box becomes one item keyed by its frame number', () => {
  const keys = boxes(plan).map((box) => box.key);
  assert.deepEqual(keys, frames.map((frame) => frameKey(frame.n)));
  assert.ok(boxes(plan).every((box) => box.kind === 'box'));
});

test('the timeline runs left to right in frame order, one column per box — the order the SVG reads in', () => {
  const xs = boxes(plan).map((box) => box.x);
  xs.slice(1).forEach((x, index) => {
    assert.equal(x - (xs[index] ?? 0), BOX_WIDTH + COLUMN_GAP);
  });
});

test('bands stack ui, data, events from the top', () => {
  const rowsOf = (types: FrameType[]): number[] =>
    boxes(plan)
      .filter((box) => types.includes(typeOf(box.key)))
      .map((box) => box.y);
  const ui = rowsOf(['ui', 'pcr']);
  const data = rowsOf(['cmd', 'rmo']);
  const events = rowsOf(['evt']);
  assert.ok(Math.max(...ui) < Math.min(...data));
  assert.ok(Math.max(...data) < Math.min(...events));
});

test('lanes within a band are distinct rows', () => {
  // Guest and PaymentProcessor in the ui band; the `order` stream and the `billing` context underneath.
  assert.notEqual(item(plan, 'frame-10').y, item(plan, 'frame-31').y);
  assert.notEqual(item(plan, 'frame-12').y, item(plan, 'frame-33').y);
  // The same lane is the same row, across slices.
  assert.equal(item(plan, 'frame-10').y, item(plan, 'frame-21').y);
  assert.equal(item(plan, 'frame-12').y, item(plan, 'frame-43').y);
});

test('a lane label exists for every lane, and none for a band that groups by nothing', () => {
  const labels = plan.items.filter((candidate) => candidate.key.startsWith('lane-'));
  // Guest, PaymentProcessor and the unplaced processor's default lane; the order and billing streams.
  assert.equal(labels.length, 5);
  const text = labels.map((label) => label.content).join('\n');
  for (const name of ['Guest', 'PaymentProcessor', 'order', 'billing']) assert.ok(text.includes(name), name);
  // The data band groups by nothing, so the row its commands and read models share says nothing.
  const dataRow = item(plan, 'frame-11').y;
  assert.ok(labels.every((label) => label.y !== dataRow));
});

// ── Arrows ───────────────────────────────────────────────────────────────────────────────────────────

test('arrows follow causal order within a slice, and `reads` between slices', () => {
  const sequence = plan.connectors.filter((connector) => connector.kind === 'sequence');
  assert.deepEqual(
    sequence.filter((connector) => connector.from.startsWith('frame-1')).map((c) => [c.from, c.to]),
    [
      ['frame-10', 'frame-11'],
      ['frame-11', 'frame-12'],
    ],
  );
  const reads = plan.connectors.filter((connector) => connector.kind === 'reads');
  assert.ok(reads.some((connector) => connector.from === 'frame-12' && connector.to === 'frame-20'));
  assert.ok(reads.every((connector) => connector.sourceName !== undefined));
});

test('an unresolvable `reads` draws no arrow rather than failing', () => {
  const broken = exampleModel();
  const second = broken.slices[1];
  assert.ok(second !== undefined);
  second.reads = ['NothingProducesThis'];
  const planned = planBoard(broken);
  assert.ok(planned.connectors.every((connector) => connector.to !== 'frame-20' || connector.kind === 'sequence'));
});

test('a slice caption names the slice, its pattern, its actor and its status', () => {
  const caption = item(plan, 'slice-S3').content;
  for (const part of ['S3', 'Take payment', 'automation', 'PaymentProcessor', 'planned']) {
    assert.ok(caption.includes(part), part);
  }
});

// ── Colour ───────────────────────────────────────────────────────────────────────────────────────────

test('the legend carries one swatch per frame type', () => {
  for (const type of FRAME_TYPES) {
    const swatch = item(plan, `legend-${type}`);
    assert.equal(swatch.fill, SWATCHES[type].fill);
    assert.ok(swatch.content.includes(SWATCHES[type].label));
  }
});

test('every fill is the same swatch the other renderer uses', () => {
  for (const box of boxes(plan)) {
    const swatch = SWATCHES[typeOf(box.key)];
    assert.equal(box.fill, swatch.fill);
    assert.equal(box.stroke, swatch.stroke);
  }
  // And a wireframe is the one square box.
  assert.equal(item(plan, 'frame-10').rounded, false);
  assert.equal(item(plan, 'frame-11').rounded, true);
});

// ── The frame ────────────────────────────────────────────────────────────────────────────────────────

test('the frame is big enough to hold everything planned inside it', () => {
  for (const planned of plan.items) {
    assert.ok(planned.x - planned.width / 2 >= 0, planned.key);
    assert.ok(planned.y - planned.height / 2 >= 0, planned.key);
    assert.ok(planned.x + planned.width / 2 <= plan.frame.width, planned.key);
    assert.ok(planned.y + planned.height / 2 <= plan.frame.height, planned.key);
  }
  for (const connector of plan.connectors) {
    if (connector.corridorY !== undefined) assert.ok(connector.corridorY < plan.frame.height);
  }
});

test('the frame is positioned by its centre', () => {
  assert.equal(plan.frame.x, plan.frame.width / 2);
  assert.equal(plan.frame.y, plan.frame.height / 2);
});

// ── Box content ──────────────────────────────────────────────────────────────────────────────────────

test('box content stars an identifying attribute, as the diagram does', () => {
  const content = item(plan, 'frame-12').content;
  assert.ok(content.includes('<p><b>OrderPlaced</b></p>'));
  assert.ok(content.includes('orderId*'));
  assert.ok(content.includes('total'));
  assert.ok(!content.includes('total*'));
});

test('model text cannot close a tag', () => {
  const content = item(plan, 'frame-50').content;
  assert.ok(content.includes('&lt;b&gt;last 30 days&lt;/b&gt; &amp; &quot;everything&quot;'));
  assert.ok(!content.includes('<b>last'));
});

test('long example data is truncated', () => {
  const content = item(plan, 'frame-50').content;
  const detail = /<p>(?!<b>)(.*)<\/p>$/.exec(content)?.[1] ?? '';
  assert.ok(detail.endsWith('…'));
  assert.ok(LONG_DATA.length > DETAIL_LIMIT);
  assert.ok(!content.includes('until this line is well past'));
});

// ── Routing ──────────────────────────────────────────────────────────────────────────────────────────

test('a reads arrow is told apart from a sequence step', () => {
  const kinds = new Set(plan.connectors.map((connector) => connector.kind));
  assert.deepEqual([...kinds].sort(), ['reads', 'sequence']);
  assert.ok(plan.connectors.filter((c) => c.kind === 'sequence').every((c) => c.corridorY === undefined));
});

test('a long reads arrow detours below every box, inside the frame', () => {
  const detour = plan.connectors.find((connector) => connector.from === 'frame-12' && connector.to === 'frame-30');
  assert.ok(detour?.corridorY !== undefined);
  const deepestBox = Math.max(...boxes(plan).map(bottomOf));
  assert.ok(detour.corridorY > deepestBox);
  assert.ok(detour.corridorY < plan.frame.height);
});

test('a neighbouring read is left direct', () => {
  const neighbour = plan.connectors.find((connector) => connector.from === 'frame-12' && connector.to === 'frame-20');
  assert.ok(neighbour !== undefined);
  assert.equal(neighbour.corridorY, undefined);
  const paid = plan.connectors.find((connector) => connector.from === 'frame-43' && connector.to === 'frame-50');
  assert.equal(paid?.corridorY, undefined);
});

test("one event's readers share one corridor", () => {
  const hub = planBoard(hubModel(6));
  const detours = hub.connectors.filter((connector) => connector.kind === 'reads' && connector.corridorY !== undefined);
  assert.equal(detours.length, 5, 'every reader but the neighbour detours');
  assert.equal(new Set(detours.map((connector) => connector.corridorY)).size, 1);
});

test('two trunks that overlap take two corridors, packed from the top', () => {
  const corridors = new Set(
    plan.connectors.map((connector) => connector.corridorY).filter((y): y is number => y !== undefined),
  );
  // OrderPlaced's trunk spans columns 2–13 and Charged's 8–13: they overlap, so neither can share.
  assert.equal(corridors.size, 2);
});

// ── Captions ─────────────────────────────────────────────────────────────────────────────────────────

test('a reader is captioned under its own box', () => {
  const box = item(plan, 'frame-20');
  const caption = item(plan, 'reads-frame-20');
  assert.equal(caption.x, box.x);
  assert.ok(caption.y - caption.height / 2 > bottomOf(box));
  assert.equal(caption.content, '<p>reads OrderPlaced</p>');
});

test('several reads on one box make one caption, in sorted order', () => {
  const captions = plan.items.filter((candidate) => candidate.key === 'reads-frame-50');
  assert.equal(captions.length, 1);
  assert.equal(captions[0]?.content, '<p>reads Charged, OrderPaid, OrderPlaced</p>');
});

test('the caption names every read, not only the detouring ones', () => {
  // OrderPaid sits in the neighbouring column and is drawn directly; it is still listed.
  const direct = plan.connectors.find((connector) => connector.from === 'frame-43' && connector.to === 'frame-50');
  assert.equal(direct?.corridorY, undefined);
  assert.ok(item(plan, 'reads-frame-50').content.includes('OrderPaid'));
});

test('the deepest caption still clears the first corridor', () => {
  const captions = plan.items.filter((candidate) => candidate.key.startsWith('reads-'));
  const deepest = Math.max(...captions.map((caption) => caption.y + caption.height / 2));
  const first = Math.min(
    ...plan.connectors.map((connector) => connector.corridorY).filter((y): y is number => y !== undefined),
  );
  assert.ok(deepest < first, `${String(deepest)} against ${String(first)}`);
});

test('an empty model still plans: a frame, a legend, and nothing to draw', () => {
  const empty: Model = { ...exampleModel(), slices: [] };
  const planned = planBoard(empty);
  assert.equal(boxes(planned).length, 0);
  assert.equal(planned.connectors.length, 0);
  assert.ok(planned.frame.width > 0 && planned.frame.height > 0);
});
