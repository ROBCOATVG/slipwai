/**
 * The serialisation, over the worked example's plan. No file, no browser, no network.
 *
 * The last two tests are the ones the gate rests on: without "same model, same bytes" there is no
 * `check-drawio`, and without "a changed model changes the file" the check would pass stale work.
 *
 * Run with: make model-drawio-test
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { planBoard, type BoardPlan, type PlannedItem } from './board-plan.ts';
import { cellId, renderDrawio } from './drawio.ts';
import { exampleModel } from './example-model.ts';
import { SWATCHES } from './palette.ts';

const plan = planBoard(exampleModel());
const xml = renderDrawio(plan);

/** The `<mxCell …>` opening tag with this id, attributes and all. */
function cell(of: string, id: string): string {
  const match = new RegExp(`<mxCell id="${id}"[^>]*>`).exec(of);
  assert.ok(match !== null, `no cell ${id}`);
  return match[0];
}

/** The geometry line that follows a cell's opening tag. */
function geometryOf(of: string, id: string): string {
  const start = of.indexOf(cell(of, id));
  const line = /<mxGeometry[^>]*>/.exec(of.slice(start));
  assert.ok(line !== null, `no geometry for ${id}`);
  return line[0];
}

function item(key: string): PlannedItem {
  const found = plan.items.find((candidate) => candidate.key === key);
  assert.ok(found !== undefined, `no item ${key}`);
  return found;
}

/** A hand-built plan, for the cases the example cannot show without a renderer's help. */
function tinyPlan(items: PlannedItem[]): BoardPlan {
  return { frame: { key: 'frame', title: 'Tiny', x: 200, y: 100, width: 400, height: 200 }, items, connectors: [] };
}

const text = (key: string, content: string): PlannedItem => ({
  key,
  kind: 'text',
  x: 100,
  y: 50,
  width: 100,
  height: 20,
  content,
  fontSize: 11,
  align: 'center',
});

test("one page holding one frame, with mxGraph's two root cells above it", () => {
  assert.equal((xml.match(/<diagram /g) ?? []).length, 1);
  assert.ok(xml.includes('<mxCell id="0" />\n        <mxCell id="1" parent="0" />'));
  const frame = cell(xml, 'c-frame');
  assert.ok(frame.includes('parent="1"'));
  assert.ok(frame.includes('container=1;collapsible=0;recursiveResize=0;'));
  assert.ok(frame.includes(`value="${plan.frame.title}"`));
});

test('every box is a child of the frame', () => {
  for (const planned of plan.items) {
    assert.ok(cell(xml, cellId(planned.key)).includes('parent="c-frame"'), planned.key);
  }
});

test("a planned centre becomes an mxGeometry corner, and the frame's own corner likewise", () => {
  const box = item('frame-12');
  const geometry = geometryOf(xml, 'c-frame-12');
  assert.ok(geometry.includes(`x="${String(box.x - box.width / 2)}"`));
  assert.ok(geometry.includes(`y="${String(box.y - box.height / 2)}"`));
  assert.ok(geometry.includes(`width="${String(box.width)}" height="${String(box.height)}"`));
  const frame = geometryOf(xml, 'c-frame');
  assert.ok(frame.includes('x="0" y="0"'));
  assert.ok(frame.includes(`width="${String(plan.frame.width)}" height="${String(plan.frame.height)}"`));
});

test('a box keeps the real swatch', () => {
  const event = cell(xml, 'c-frame-12');
  assert.ok(event.includes(`fillColor=${SWATCHES.evt.fill};strokeColor=${SWATCHES.evt.stroke};`));
  const screen = cell(xml, 'c-frame-10');
  assert.ok(screen.includes(`rounded=0;html=1;`));
  assert.ok(screen.includes(`fillColor=${SWATCHES.ui.fill};strokeColor=${SWATCHES.ui.stroke};`));
});

test("a label's HTML is escaped into the attribute rather than closing the cell, and the style says html=1", () => {
  const event = cell(xml, 'c-frame-12');
  assert.ok(event.includes('value="&lt;p&gt;&lt;b&gt;OrderPlaced&lt;/b&gt;&lt;/p&gt;'));
  assert.ok(event.includes('html=1;'));
  // Nothing in the file is a live tag that the plan wrote: only mxGraph's own elements.
  assert.equal((xml.match(/<(?!\/?(?:mxfile|diagram|mxGraphModel|root|mxCell|mxGeometry|Array|mxPoint)\b)/g) ?? []).length, 0);
});

test('escaping happens once, not twice', () => {
  const once = renderDrawio(tinyPlan([text('t', '<p>a &amp; b</p>')]));
  assert.ok(once.includes('value="&lt;p&gt;a &amp;amp; b&lt;/p&gt;"'));
  assert.ok(!once.includes('&amp;lt;'));
});

test('an arrow names both ends by the cell ids its boxes were given', () => {
  const step = cell(xml, 'e-c-frame-10-c-frame-11');
  assert.ok(step.includes('edge="1"'));
  assert.ok(step.includes('source="c-frame-10" target="c-frame-11"'));
  assert.ok(step.includes('parent="c-frame"'));
});

test('a sequence arrow exits right and enters left; a detour leaves and enters underneath, by its corridor', () => {
  const step = cell(xml, 'e-c-frame-10-c-frame-11');
  assert.ok(step.includes('exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;'));
  assert.ok(step.includes('strokeColor=#4a4a4a;strokeWidth=1.5;endArrow=block;endFill=1;'));
  const detour = plan.connectors.find((connector) => connector.from === 'frame-12' && connector.to === 'frame-30');
  assert.ok(detour?.corridorY !== undefined);
  const read = cell(xml, 'e-c-frame-12-c-frame-30');
  assert.ok(read.includes('exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;'));
  assert.ok(read.includes('dashed=1;dashPattern=8 6;'));
  const start = xml.indexOf(read);
  const points = xml.slice(start, xml.indexOf('</mxCell>', start));
  assert.ok(points.includes(`<mxPoint x="${String(item('frame-12').x)}" y="${String(detour.corridorY)}" />`));
  assert.ok(points.includes(`<mxPoint x="${String(item('frame-30').x)}" y="${String(detour.corridorY)}" />`));
  // A direct arrow carries no waypoints.
  const direct = xml.indexOf(cell(xml, 'e-c-frame-12-c-frame-20'));
  assert.ok(xml.slice(direct, xml.indexOf('</mxCell>', direct)).includes('<mxGeometry relative="1" as="geometry" />'));
});

test('a text item has no fill or stroke where a shape has both', () => {
  const caption = cell(xml, 'c-reads-frame-20');
  assert.ok(caption.includes('text;html=1;'));
  assert.ok(caption.includes('strokeColor=none;fillColor=none;'));
  const box = cell(xml, 'c-frame-20');
  assert.ok(/fillColor=#[0-9a-f]{6};strokeColor=#[0-9a-f]{6};/.test(box));
});

test('an unsafe id is sanitised and never collides with 0 or 1', () => {
  assert.equal(cellId('a b/c.d'), 'c-a_b_c_d');
  assert.equal(cellId('0'), 'c-0');
  assert.equal(cellId('1'), 'c-1');
  assert.throws(() => renderDrawio(tinyPlan([text('a b', 'x'), text('a_b', 'y')])), /share the id/);
});

test('the same model serialises to the same bytes, and carries no clock', () => {
  const again = renderDrawio(planBoard(exampleModel()));
  assert.equal(again, xml);
  const mxfile = /<mxfile[^>]*>/.exec(xml)?.[0] ?? '';
  for (const attribute of ['modified', 'agent', 'version', 'etag']) assert.ok(!mxfile.includes(attribute), attribute);
  assert.ok(xml.endsWith('</mxfile>\n'));
});

test('a changed model changes the file', () => {
  const changed = exampleModel();
  const frame = changed.slices[0]?.frames[2];
  assert.ok(frame !== undefined);
  frame.name = 'OrderAccepted';
  assert.notEqual(renderDrawio(planBoard(changed)), xml);
});

test('the file is uncompressed and readable as it is', () => {
  assert.ok(xml.startsWith('<mxfile host="app.diagrams.net">\n  <diagram id="event-model" name="Event model">\n'));
  assert.ok(xml.includes('<mxGraphModel '));
  assert.ok(!/<diagram[^>]*>[A-Za-z0-9+/=]{40,}<\/diagram>/.test(xml), 'a deflated payload');
});
