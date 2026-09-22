/**
 * A `BoardPlan` as a draw.io file: mxGraph's XML, uncompressed, one string.
 *
 * Pure. It reads nothing and decides nothing about layout; every position, size, colour and arrow comes
 * from the plan. What it owns is the format: which cell is which, how a centre becomes mxGraph's corner,
 * how a label's HTML survives being an XML attribute, and what an id may contain.
 *
 * ── What draw.io needs, learnt the hard way ──────────────────────────────────────────────────────────
 *
 * - The frame is a real container (`container=1;collapsible=0;recursiveResize=0;`). mxGraph positions a
 *   child relative to its parent's top-left, which is the coordinate system the plan is already in, so
 *   there is no offset arithmetic — and dragging the frame moves the whole model.
 * - A label's HTML is XML-escaped into `value`, and the style carries `html=1`, or draw.io shows the tags
 *   literally. An unescaped `<p>` closes `mxCell`, and the file opens as empty rather than as broken.
 * - Ids are sanitised (`[^A-Za-z0-9_-]` → `_`) and prefixed: mxGraph reserves `0` and `1` for its two
 *   root cells, and a key built from model data could be anything.
 * - Uncompressed. draw.io's deflated payload would show as one changed blob on every regeneration; plain
 *   XML diffs line by line, and a reviewer can see which box moved.
 * - No `edgeLabel` child cells. They did not render: an edge label's position is something mxGraph derives
 *   from the edge's own path, and for an edge inside a container carrying hand-placed waypoints that is a
 *   calculation nobody can see the result of until draw.io has opened the file. Captions are positioned
 *   text cells, the same kind as the lane labels, which demonstrably render.
 * - `jumpStyle=arc` on every edge, so a crossing reads as a hop rather than a junction.
 *
 * ── The determinism contract ─────────────────────────────────────────────────────────────────────────
 * No `modified`, `agent` or `version` on `mxfile`, no timestamp anywhere, no generated id: the same plan
 * serialises to the same bytes, which is what lets `check-drawio` compare a committed file to a fresh
 * one. The file ends with a newline, or every diff shows a spurious last-line change.
 */
import type { BoardPlan, PlannedConnector, PlannedItem } from './board-plan.ts';

const FRAME_STYLE =
  'rounded=0;html=1;whiteSpace=wrap;fillColor=none;strokeColor=#b3b3b3;verticalAlign=top;align=left;' +
  'spacingLeft=16;spacingTop=8;fontSize=28;fontColor=#8c8c8c;container=1;collapsible=0;recursiveResize=0;';

const EDGE_BASE = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jumpStyle=arc;jumpSize=8;';
/** Exits right and enters left: the direction the timeline reads in. */
const ENDS_DIRECT = 'exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;';
/** Leaves underneath and rises into the target from underneath, by way of a corridor. */
const ENDS_DETOUR = 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;';
const STROKE_SEQUENCE = 'strokeColor=#4a4a4a;strokeWidth=1.5;';
const STROKE_READS = 'strokeColor=#9a9a9a;strokeWidth=1.5;dashed=1;dashPattern=8 6;';
const ARROWHEAD = 'endArrow=block;endFill=1;';

/** Attribute text: the five characters XML gives a meaning to, once each. */
export function escapeXml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

/** A plan key as a cell id: prefixed so it can never be `0` or `1`, and reduced to what an id may hold. */
export function cellId(key: string): string {
  return `c-${key.replaceAll(/[^A-Za-z0-9_-]/g, '_')}`;
}

export function edgeId(connector: PlannedConnector): string {
  return `e-${cellId(connector.from)}-${cellId(connector.to)}`;
}

function textStyle(item: PlannedItem): string {
  return (
    `text;html=1;whiteSpace=wrap;fontSize=${String(item.fontSize)};align=${item.align};verticalAlign=middle;` +
    'strokeColor=none;fillColor=none;'
  );
}

function boxStyle(item: PlannedItem): string {
  return (
    `rounded=${item.rounded === true ? '1' : '0'};html=1;whiteSpace=wrap;fontSize=${String(item.fontSize)};` +
    `align=${item.align};verticalAlign=middle;fillColor=${item.fill ?? 'none'};strokeColor=${item.stroke ?? 'none'};`
  );
}

function edgeStyle(connector: PlannedConnector): string {
  const ends = connector.corridorY === undefined ? ENDS_DIRECT : ENDS_DETOUR;
  const stroke = connector.kind === 'sequence' ? STROKE_SEQUENCE : STROKE_READS;
  return `${EDGE_BASE}${ends}${stroke}${ARROWHEAD}`;
}

/** The plan keeps centres; mxGraph wants a top-left corner. Converted here, once. */
function geometry(item: { x: number; y: number; width: number; height: number }, indent: string): string {
  const x = item.x - item.width / 2;
  const y = item.y - item.height / 2;
  return (
    `${indent}<mxGeometry x="${String(x)}" y="${String(y)}" width="${String(item.width)}" ` +
    `height="${String(item.height)}" as="geometry" />`
  );
}

function vertex(id: string, value: string, style: string, parent: string, box: PlannedItem | BoardPlan['frame']): string {
  return [
    `        <mxCell id="${id}" value="${escapeXml(value)}" style="${escapeXml(style)}" vertex="1" parent="${parent}">`,
    geometry(box, '          '),
    '        </mxCell>',
  ].join('\n');
}

function edge(connector: PlannedConnector, frameId: string, centreX: (key: string) => number): string {
  const open =
    `        <mxCell id="${edgeId(connector)}" style="${escapeXml(edgeStyle(connector))}" edge="1" ` +
    `parent="${frameId}" source="${cellId(connector.from)}" target="${cellId(connector.to)}">`;
  if (connector.corridorY === undefined) {
    return [open, '          <mxGeometry relative="1" as="geometry" />', '        </mxCell>'].join('\n');
  }
  const y = String(connector.corridorY);
  return [
    open,
    '          <mxGeometry relative="1" as="geometry">',
    '            <Array as="points">',
    `              <mxPoint x="${String(centreX(connector.from))}" y="${y}" />`,
    `              <mxPoint x="${String(centreX(connector.to))}" y="${y}" />`,
    '            </Array>',
    '          </mxGeometry>',
    '        </mxCell>',
  ].join('\n');
}

/** The whole plan as one draw.io page. Pure: same plan, same bytes. */
export function renderDrawio(plan: BoardPlan): string {
  const frameId = cellId(plan.frame.key);
  const seen = new Set<string>(['0', '1', frameId]);
  const claim = (id: string): string => {
    if (seen.has(id)) {
      throw new Error(`two cells would share the id ${id} — plan keys must stay distinct after sanitising`);
    }
    seen.add(id);
    return id;
  };
  const byKey = new Map(plan.items.map((item) => [item.key, item]));
  const centreX = (key: string): number => {
    const item = byKey.get(key);
    if (item === undefined) throw new Error(`connector names ${key}, which the plan has no item for`);
    return item.x;
  };

  const cells = [
    vertex(frameId, plan.frame.title, FRAME_STYLE, '1', plan.frame),
    ...plan.items.map((item) =>
      vertex(
        claim(cellId(item.key)),
        item.content,
        item.kind === 'text' ? textStyle(item) : boxStyle(item),
        frameId,
        item,
      ),
    ),
    ...plan.connectors.map((connector) => {
      claim(edgeId(connector));
      return edge(connector, frameId, centreX);
    }),
  ];

  return [
    '<mxfile host="app.diagrams.net">',
    '  <diagram id="event-model" name="Event model">',
    '    <mxGraphModel dx="0" dy="0" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" ' +
      'fold="1" page="0" pageScale="1" math="0" shadow="0">',
    '      <root>',
    '        <mxCell id="0" />',
    '        <mxCell id="1" parent="0" />',
    ...cells,
    '      </root>',
    '    </mxGraphModel>',
    '  </diagram>',
    '</mxfile>',
    '',
  ].join('\n');
}
