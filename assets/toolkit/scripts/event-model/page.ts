/**
 * The browsable model: one self-contained HTML page holding the timeline, the slice register, and each
 * slice on its own.
 *
 * It exists because the diagram alone cannot answer the questions people actually arrive with — which
 * slices are built, where a slice's scenarios are, which code realises it. The SVGs are inlined rather
 * than linked so the page can be opened from disk, attached to a review, or printed to PDF with nothing
 * fetched from anywhere.
 *
 * **Nothing here is scripted, and that is a test rather than a preference.** The page has to work from a
 * `file://` path, inside a review attachment, and on paper, so every control is a checkbox or a radio and
 * a CSS rule: the zoom is `:checked`, and the filters are `:has()`. A page that needed a script to be
 * navigable would be a page that is blank in half the places it gets opened.
 *
 * Colours are Mermaid's own event-modeling defaults, so the legend cannot drift from the boxes.
 */
import {
  FRAME_TYPES,
  isExternalMockup,
  PATTERNS,
  segmentModel,
  segmentRange,
  STATUSES,
  type Frame,
  type Model,
  type Mockup,
  type Pattern,
  type Slice,
  type Status,
} from './model.ts';
import { SWATCHES as SWATCHES_BY_TYPE, type Swatch } from './palette.ts';
import { MODEL_DIR, MODEL_SVG, segmentArtifact, type ServiceRecord } from './workspace.ts';

/** The legend, in the order the bands read: `palette.ts` is the one table, shared with the draw.io canvas. */
const SWATCHES: ReadonlyArray<Swatch> = FRAME_TYPES.map((type) => SWATCHES_BY_TYPE[type]);

const STATUS_COLOURS: Readonly<Record<Status, string>> = {
  proposed: '#8a8a8a',
  modelled: '#679ac3',
  planned: '#b88cbf',
  implemented: '#4f8a2f',
};

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

const forwardSlashed = (path: string): string => path.split('\\').join('/');

/**
 * A repository-relative path, rewritten relative to **this page**.
 *
 * The page lives in `docs/event-model/`, so a link to `docs/event-model/model.svg` resolves from there to
 * `docs/event-model/docs/event-model/model.svg` and 404s. The README block is the opposite case — it sits
 * at the repository root and wants the path unchanged — and reusing its paths here is precisely the
 * mistake that produced the broken links this exists to prevent. It matters twice over now: these links
 * are also what a published copy of this page serves.
 *
 * A path *outside* the directory climbs out of it, which only mockups can be. That link resolves in a
 * clone and cannot resolve on the published site, because the workflow serves this directory as the site
 * root and `../../` escapes it — which is the whole reason `mockup-publishes-with-the-page` refuses one
 * once `render.page` is set.
 */
function besideThePage(repoRelative: string): string {
  const segments = forwardSlashed(MODEL_DIR).split('/');
  const prefix = `${segments.join('/')}/`;
  const path = forwardSlashed(repoRelative);
  return path.startsWith(prefix) ? path.slice(prefix.length) : `${'../'.repeat(segments.length)}${path}`;
}

/**
 * Prepares one Mermaid SVG for inlining, and reports the width it wants.
 *
 * Mermaid hard-codes `id="my-svg"` and refers to it from its own `<style>` block and from every arrowhead
 * as `url(#em-arrowhead-my-svg)`. Inline five of those in one page and each document has five elements
 * sharing an id: the arrowheads in diagrams two to five resolve against the *first* diagram's `defs`.
 * They happen to look right because the markers are identical, which is exactly what makes it a bug worth
 * fixing rather than noticing later. Namespacing the id per diagram makes each SVG self-contained.
 */
function inlineSvg(svg: string, key: string): { markup: string; naturalWidth: number } {
  const markup = svg
    .replace(/<\?xml[^>]*\?>/, '')
    .replace(/<!DOCTYPE[^>]*>/, '')
    .replaceAll('my-svg', `em-${key}`)
    .trim();

  // Mermaid states the width it wants as `max-width: NNNpx`; the element itself is `width="100%"`, so the
  // page decides whether the diagram is scaled to fit or shown at full size and scrolled.
  const declared = /max-width:\s*(\d+(?:\.\d+)?)px/.exec(markup)?.[1];
  return { markup, naturalWidth: declared === undefined ? 0 : Math.ceil(Number(declared)) };
}

/**
 * A diagram that fits the page by default and shows at full resolution when clicked.
 *
 * A twenty-slice timeline is several thousand pixels wide; scaled to fit a page it is a coloured smear.
 * The toggle is a checkbox and a label rather than a script, so the page stays a single static file that
 * needs nothing to run — including when it is printed or opened from a file:// path.
 */
function diagram(svg: string | undefined, key: string, standalone?: string): string {
  if (svg === undefined) {
    return '<p class="none">not rendered — run <code>make model</code></p>';
  }
  const { markup, naturalWidth } = inlineSvg(svg, key);
  const link =
    standalone === undefined
      ? ''
      : ` <a class="control" href="${escapeHtml(standalone)}">open the SVG</a>`;

  return `<div class="diagram" style="--natural:${String(naturalWidth)}px">
        <input class="zoomer" type="checkbox" id="zoom-${escapeHtml(key)}">
        <p class="controls"><label class="control" for="zoom-${escapeHtml(key)}"></label>${link}</p>
        <figure>${markup}</figure>
      </div>`;
}

function cell(value: string | undefined): string {
  return value === undefined || value === '' ? '<span class="none">—</span>' : escapeHtml(value);
}

function statusBadge(status: Status): string {
  return `<span class="badge" style="background:${STATUS_COLOURS[status]}">${status}</span>`;
}

/** The `data-` pair every filterable element carries — register row, slice section, and jump link alike. */
function filterable(slice: Slice): string {
  return `data-status="${slice.status}" data-pattern="${slice.pattern}"`;
}

function sliceRow(slice: Slice): string {
  const code = (slice.code ?? []).map((path) => `<code>${escapeHtml(path)}</code>`).join('<br>');
  return `      <tr ${filterable(slice)}>
        <td><a href="#${escapeHtml(slice.id)}">${escapeHtml(slice.id)}</a></td>
        <td>${escapeHtml(slice.name)}</td>
        <td>${escapeHtml(slice.pattern)}</td>
        <td>${statusBadge(slice.status)}</td>
        <td>${cell(slice.actor)}</td>
        <td>${slice.service === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.service)}</code>`}</td>
        <td>${slice.context === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.context)}</code>`}</td>
        <td>${slice.stream === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.stream)}</code>`}</td>
        <td>${slice.gwt === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.gwt)}</code>`}</td>
        <td>${code === '' ? '<span class="none">—</span>' : code}</td>
      </tr>`;
}

/**
 * How big a wireframe is drawn, and at what fidelity.
 *
 * The mock is rendered at a plausible screen width and scaled down, rather than loaded into a small frame,
 * because a mock reflowed to 280px is a different design from the one under review — the two-column layout
 * you were asked to look at becomes one column, and the thumbnail quietly stops being evidence.
 */
const PREVIEW = { width: 700, height: 520, scale: 0.4 } as const;

/** Something a browser paints directly, as opposed to a page it has to load into a frame. */
function isImageMockup(at: string): boolean {
  return /\.(?:png|jpe?g|gif|webp|avif|svg)$/i.test(at.split(/[?#]/)[0] ?? '');
}

/**
 * One wireframe, shown at a size you can recognise rather than read, over a link to the real thing.
 *
 * ── Why an `iframe` and not a picture ────────────────────────────────────────────────────────────────
 * The mocks are usually HTML, and turning HTML into a picture means driving a browser. `make model`
 * already does that for Mermaid, but through `mermaid-cli`, and reaching into somebody else's puppeteer to
 * screenshot our own files would break the first time they changed a dependency. A frame renders the mock
 * with no build step and no new dependency, and stays correct when the mock changes without `make model`
 * being run again.
 *
 * ── Why `sandbox="allow-same-origin"` ────────────────────────────────────────────────────────────────
 * `sandbox=""` sounds safer and is worse than useless here: it gives the frame an opaque origin, so the
 * mock's own stylesheet does not load and the wireframe renders as unstyled text — a picture of nothing,
 * presented as evidence of a design. `allow-same-origin` alone restores rendering while still withholding
 * scripts, forms, popups, top-level navigation and downloads, which is every capability a static mock has
 * no use for. It is never paired with `allow-scripts`, the combination that would let framed content reach
 * back into this page.
 *
 * The overlay link sits above the frame so the thumbnail is one click target, and so the mock cannot be
 * half-operated inside a box too small to operate it in.
 */
function mockupShot(frame: Frame, mockup: Mockup): string {
  const external = isExternalMockup(mockup.at);
  const href = external ? mockup.at : besideThePage(mockup.at);
  const label = `${frame.name} · ${mockup.state}`;
  const rel = external ? ' rel="noopener noreferrer"' : '';

  // An off-site mock cannot be framed — a design tool sends `X-Frame-Options`, and a page that embedded
  // third-party URLs would stop being the self-contained file this one is. So it is named, and linked.
  //
  // Eager, deliberately. `loading="lazy"` is the obvious optimisation, and the failure it risks is not
  // symmetric with what it saves: a frame that has not loaded renders as a white rectangle, which in a
  // printed or attached copy is indistinguishable from a state nobody designed — the one thing this
  // section exists to make visible. Chrome forces lazy *images* to load before printing; it makes no such
  // guarantee for frames. The mocks are local static files, so loading them all costs little, and it costs
  // it in the browser rather than in the review.
  const preview = external
    ? '<p class="offsite">held off-site</p>'
    : isImageMockup(mockup.at)
      ? `<img src="${escapeHtml(href)}" alt="${escapeHtml(label)}">`
      : `<iframe sandbox="allow-same-origin" title="${escapeHtml(label)}" src="${escapeHtml(href)}"></iframe>`;

  return `          <li><figure>
            <div class="shot">${preview}<a class="hit" href="${escapeHtml(href)}"${rel} aria-label="${escapeHtml(label)}"></a></div>
            <figcaption><a href="${escapeHtml(href)}"${rel}>${escapeHtml(mockup.state)}${external ? ' ↗' : ''}</a></figcaption>
          </figure></li>`;
}

/**
 * A slice's screens, as wireframes, under the diagram that names them.
 *
 * This is the point of the field. A white box *is* a screen, and the states it can be in are where the
 * unmodelled behaviour hides — so a reviewer has to be able to see them next to the slice, not follow a
 * link and lose the diagram. A screen with no mocks says so rather than being omitted: an undesigned state
 * is a finding, and the sentence is how it stays visible.
 *
 * Slices with no `ui` frame at all — every automation and every translation — get nothing. A processor has
 * no screen, so silence there is accurate rather than a gap.
 */
function screens(slice: Slice): string {
  const uiFrames = slice.frames.filter((frame) => frame.type === 'ui');
  if (uiFrames.length === 0) {
    return '';
  }

  const blocks = uiFrames.map((frame) => {
    const mockups = frame.mockups ?? [];
    if (mockups.length === 0) {
      return `        <h4>${escapeHtml(frame.name)} <span class="none">— no mockups yet, so the states this screen can be in are undesigned</span></h4>`;
    }
    return `        <h4>${escapeHtml(frame.name)}</h4>
        <ul class="shots">
${mockups.map((mockup) => mockupShot(frame, mockup)).join('\n')}
        </ul>`;
  });

  return `        <div class="screens">
${blocks.join('\n')}
        </div>`;
}

/**
 * One slice, collapsible, and open by default.
 *
 * Open rather than closed because every route into a slice is an anchor — from the jump bar, from the
 * register, from a link someone pasted into a review — and a fragment that lands on a *closed* `<details>`
 * scrolls you to a title with nothing under it. Browsers auto-expand a `<details>` containing the target;
 * they do not expand one that *is* the target. So the affordance is collapse-what-you-have-read, which
 * costs nothing, rather than expand-what-you-want, which breaks every link.
 */
/**
 * The identifying attributes of a slice's events, which is what its tag index is derived from.
 *
 * On the page rather than in the diagram because the diagram has one line per box: there, an identifying
 * attribute is starred, and the kind it identifies is here. Two attributes may identify the same kind —
 * `fromHold` and `toHold` are both a `hold` — so this is a list and not a lookup.
 *
 * Nothing at all for a slice whose events name no attributes, which is every slice until somebody needs a
 * boundary drawn out of tags.
 */
function identities(slice: Slice): string {
  const rows = slice.frames
    .filter((frame) => frame.type === 'evt' && (frame.attributes ?? []).some((a) => a.identifies !== undefined))
    .map((frame) => {
      const marked = (frame.attributes ?? [])
        .filter((attribute) => attribute.identifies !== undefined)
        .map(
          (attribute) =>
            `<code>${escapeHtml(attribute.name)}</code> → <code>${escapeHtml(String(attribute.identifies))}:</code>`,
        )
        .join(', ');
      return `          <div><dt>${escapeHtml(frame.name)}</dt><dd>${marked}</dd></div>`;
    });
  if (rows.length === 0) {
    return '';
  }
  return `        <h4>Identifies</h4>
        <dl>
${rows.join('\n')}
        </dl>`;
}

function sliceSection(slice: Slice, svg: string | undefined): string {
  const reads = slice.reads ?? [];
  const facts = [
    ['Pattern', escapeHtml(slice.pattern)],
    ['Status', statusBadge(slice.status)],
    ['Actor', cell(slice.actor)],
    ['Service', slice.service === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.service)}</code>`],
    ['Context', slice.context === undefined ? '<span class="none">—</span>' : `<code>${escapeHtml(slice.context)}</code>`],
    ['Stream identity', cell(slice.stream)],
    ['Reads', reads.length === 0 ? '<span class="none">—</span>' : reads.map(escapeHtml).join(', ')],
    ['Scenarios', cell(slice.gwt)],
  ]
    .map(([label, value]) => `<div><dt>${String(label)}</dt><dd>${String(value)}</dd></div>`)
    .join('\n          ');

  return `    <section class="slice" id="${escapeHtml(slice.id)}" ${filterable(slice)}>
      <details open>
        <summary><h3>${escapeHtml(slice.id)} · ${escapeHtml(slice.name)} ${statusBadge(slice.status)}</h3></summary>
        <dl>
          ${facts}
        </dl>
        ${diagram(svg, `slice-${slice.id}`)}
${identities(slice)}
${screens(slice)}
      </details>
    </section>`;
}

/**
 * One bounded context, as a canvas nobody has to maintain.
 *
 * A Bounded Context Canvas asks a context what it is for, what comes in, what goes out, and what words it
 * owns. Every answer but the first is already in the model once each slice names its `service`: the commands
 * are its inbound messages, the events its outbound ones, the read models its questions, and the names of
 * all three its language. So the canvas is a projection of the model over the manifest — one per context,
 * grouping the services `project.json` puts in it — rather than a document that drifts from both. The one
 * thing only a person can say, the purpose, is read from `project.json` and shown as written or as missing.
 *
 * A slice's context is the one it names, or the only one its service holds. Slices that name no service
 * belong to the only service when there is one; a slice whose service or context cannot be told is listed as
 * unplaced: `check-model` refuses those from `modelled` onward, and the page shows the same gap so it is
 * visible before the gate is run. A service holding several contexts — the modular monolith a project
 * starts as — appears under each, so the canvases exist before any context is a service of its own.
 */
interface ContextView {
  name: string;
  services: readonly ServiceRecord[];
  slices: readonly Slice[];
}

function contextViews(
  model: Model,
  services: readonly ServiceRecord[],
): { contexts: ContextView[]; unplaced: Slice[] } {
  const contexts = new Map<string, ContextView>();
  for (const service of services) {
    for (const context of service.contexts) {
      const view = contexts.get(context) ?? { name: context, services: [], slices: [] };
      contexts.set(context, { ...view, services: [...view.services, service] });
    }
  }
  const byName = new Map(services.map((service) => [service.name, service] as const));
  const unplaced: Slice[] = [];
  for (const slice of model.slices) {
    const owner = byName.get(slice.service ?? (services.length === 1 ? (services[0]?.name ?? '') : ''));
    const held = owner?.contexts ?? [];
    const context = slice.context ?? (held.length === 1 ? held[0] : undefined);
    const view = context === undefined || !held.includes(context) ? undefined : contexts.get(context);
    if (context === undefined || view === undefined) {
      unplaced.push(slice);
      continue;
    }
    contexts.set(context, { ...view, slices: [...view.slices, slice] });
  }
  return { contexts: [...contexts.values()], unplaced };
}

function names(items: readonly string[]): string {
  const unique = [...new Set(items)];
  return unique.length === 0
    ? '<span class="none">—</span>'
    : unique.map((name) => `<code>${escapeHtml(name)}</code>`).join(', ');
}

function contextSection(view: ContextView, all: readonly ContextView[]): string {
  const frames = view.slices.flatMap((slice) => slice.frames);
  const commands = frames.filter((frame) => frame.type === 'cmd').map((frame) => frame.name);
  const events = frames.filter((frame) => frame.type === 'evt' && frame.external !== true).map((frame) => frame.name);
  const readModels = frames.filter((frame) => frame.type === 'rmo').map((frame) => frame.name);
  const external = frames.filter((frame) => frame.type === 'evt' && frame.external === true).map((frame) => frame.name);
  const streams = view.slices.flatMap((slice) => (slice.stream === undefined ? [] : [slice.stream]));
  const actors = view.slices.flatMap((slice) => (slice.actor === undefined ? [] : [slice.actor]));

  // What crosses the boundary: events this context reads that another context produces, and events it
  // produces that another context reads. The arrows on a context map, derived from `reads`.
  const producedBy = new Map<string, string>();
  for (const other of all) {
    for (const slice of other.slices) {
      for (const frame of slice.frames) {
        if (frame.type === 'evt' && frame.external !== true) producedBy.set(frame.name, other.name);
      }
    }
  }
  const ownEvents = new Set(events);
  const inboundFrom = view.slices
    .flatMap((slice) => slice.reads ?? [])
    .filter((event) => !ownEvents.has(event))
    .map(
      (event) =>
        `<code>${escapeHtml(event)}</code> <span class="none">from ${escapeHtml(producedBy.get(event) ?? 'no context yet')}</span>`,
    );
  const readBy = all
    .filter((other) => other.name !== view.name)
    .flatMap((other) =>
      other.slices
        .flatMap((slice) => slice.reads ?? [])
        .filter((event) => ownEvents.has(event))
        .map((event) => `<code>${escapeHtml(event)}</code> <span class="none">read by ${escapeHtml(other.name)}</span>`),
    );

  const services = view.services.map(
    (service) =>
      `<code>${escapeHtml(service.path)}</code>` +
      (service.purpose === undefined
        ? ' <span class="none">— no purpose recorded: say what it owns in <code>project.json</code></span>'
        : ` — ${escapeHtml(service.purpose)}`),
  );
  const slices = view.slices.map(
    (slice) =>
      `<a href="#${escapeHtml(slice.id)}">${escapeHtml(slice.id)}</a> ${escapeHtml(slice.name)} ${statusBadge(slice.status)}`,
  );

  const list = (items: readonly string[]): string =>
    items.length === 0 ? '<p class="none">—</p>' : `<ul>${items.map((item) => `<li>${item}</li>`).join('')}</ul>`;
  const panel = (title: string, body: string): string =>
    `          <div class="panel"><h4>${title}</h4>${body}</div>`;
  const plural = (count: number, noun: string): string => `${String(count)} ${noun}${count === 1 ? '' : 's'}`;

  return `    <section class="context" id="context-${escapeHtml(view.name)}">
      <details open>
        <summary><h3>${escapeHtml(view.name)}</h3> <span class="note">${plural(view.services.length, 'service')} · ${plural(view.slices.length, 'slice')}</span></summary>
        <div class="cols">
${panel('Purpose — the services and what each owns', list(services))}
${panel('Ubiquitous language', `<p>${names([...commands, ...events, ...readModels])}</p>`)}
${panel('Inbound — commands it accepts', `<p>${names(commands)}</p>`)}
${panel('Inbound — events it reads from elsewhere', list([...inboundFrom, ...external.map((name) => `<code>${escapeHtml(name)}</code> <span class="none">external</span>`)]))}
${panel('Outbound — events it publishes', `<p>${names(events)}</p>`)}
${panel('Outbound — read across the boundary', list(readBy))}
${panel('Questions it answers — read models', `<p>${names(readModels)}</p>`)}
${panel('Consistency boundaries — streams', `<p>${names(streams)}</p>`)}
${panel('Actors', `<p>${names(actors)}</p>`)}
${panel('Slices', list(slices))}
        </div>
      </details>
    </section>`;
}

function contextsSection(model: Model, services: readonly ServiceRecord[]): string {
  if (services.length === 0) {
    return '';
  }
  const { contexts, unplaced } = contextViews(model, services);
  const unplacedBlock =
    unplaced.length === 0
      ? ''
      : `    <section class="context unplaced">
      <h3>Unplaced</h3> <span class="note">${String(unplaced.length)} slice${unplaced.length === 1 ? ' names' : 's name'} no service, or no context its service holds — <code>check-model</code> refuses these from <code>modelled</code> onward</span>
      <ul>
${unplaced.map((slice) => `        <li><a href="#${escapeHtml(slice.id)}">${escapeHtml(slice.id)}</a> ${escapeHtml(slice.name)} ${statusBadge(slice.status)}</li>`).join('\n')}
      </ul>
    </section>`;
  return `
  <h2 id="contexts">Bounded contexts</h2>
  <p class="lede">One canvas per context, derived: the services and the contexts each holds from <code>project.json</code>,
     everything else from the slices that name them. Only the purpose is written by hand — on the service's manifest entry.
     A context here is a model boundary, not a deployment one: <code>docs/architecture.md</code> says when it should become a service.</p>
${contexts.map((view) => contextSection(view, contexts)).join('\n')}
${unplacedBlock}`;
}

/**
 * The sticky jump bar.
 *
 * The register answers "which slices are there" but scrolls away the moment you look at one, and a
 * twenty-slice page is a long way back to it. The links carry the same `data-` pair as everything else,
 * so a filtered page has a filtered jump bar rather than one advertising slices that are not on screen.
 */
function jumpBar(model: Model): string {
  const links = model.slices
    .map((slice) => `<a href="#${escapeHtml(slice.id)}" ${filterable(slice)} title="${escapeHtml(slice.name)}">${escapeHtml(slice.id)}</a>`)
    .join('\n    ');

  return `  <nav class="jump" aria-label="Jump to">
    <a class="anchor" href="#timeline">Timeline</a>
    <a class="anchor" href="#register">Register</a>
    <a class="anchor" href="#contexts">Contexts</a>
    ${links}
  </nav>`;
}

/** Only the values some slice actually has: a filter that can only ever empty the page is a trap. */
function present<T extends string>(all: readonly T[], used: readonly T[]): T[] {
  return all.filter((value) => used.includes(value));
}

function filterRow(name: string, label: string, values: readonly string[]): string {
  const radios = [`all`, ...values]
    .map(
      (value) =>
        `    <input class="filter" type="radio" name="${name}" id="f-${name}-${value}"${value === 'all' ? ' checked' : ''}>`,
    )
    .join('\n');
  const chips = [`all`, ...values]
    .map((value) => `<label class="control" for="f-${name}-${value}">${escapeHtml(value)}</label>`)
    .join('\n      ');

  return `${radios}
    <p class="filter-row"><span class="filter-label">${escapeHtml(label)}</span>
      ${chips}
    </p>`;
}

/**
 * The filter rules, generated because the page knows which values exist and CSS does not.
 *
 * Two independent axes that compose by both hiding: pick a status and a pattern and an element survives
 * only if it matches both. The empty-combination message is generated the same way — at build time we
 * know which pairs no slice has, so the page can say so instead of going blank.
 */
function filterRules(statuses: readonly Status[], patterns: readonly Pattern[], model: Model): string {
  const rules: string[] = [];

  for (const [name, values] of [
    ['status', statuses],
    ['pattern', patterns],
  ] as const) {
    for (const value of ['all', ...values]) {
      rules.push(
        `  main:has(#f-${name}-${value}:checked) label[for="f-${name}-${value}"] { color: var(--fg); background: var(--bg); border-color: var(--muted); font-weight: 600; }`,
      );
      if (value !== 'all') {
        rules.push(
          `  main:has(#f-${name}-${value}:checked) [data-${name}]:not([data-${name}="${value}"]) { display: none; }`,
        );
      }
    }
  }

  for (const status of statuses) {
    for (const pattern of patterns) {
      const exists = model.slices.some((slice) => slice.status === status && slice.pattern === pattern);
      if (exists) continue;
      rules.push(
        `  main:has(#f-status-${status}:checked):has(#f-pattern-${pattern}:checked) .no-match { display: block; }`,
      );
    }
  }

  return rules.join('\n');
}

/**
 * The whole timeline, and then the same timeline in readable pieces.
 *
 * **Both, never one or the other.** The whole model in one image is the thing this page exists to show,
 * and it can show it because it has the full-size toggle and a figure that scrolls — which is exactly what
 * the README lacks and why the README gets segments *instead*. Replacing the whole view here with segments
 * would take the one view no other artifact offers and leave the reader assembling the model from parts.
 *
 * The segments are the same runs the README embeds, carrying the same global frame numbers, so a box is
 * the same box in every view. A single-segment model is already whole, so it gets no second copy of itself.
 */
function timeline(model: Model, globalSvg: string, segmentSvgs: ReadonlyMap<number, string>): string {
  const segments = segmentModel(model);
  const whole = `  ${diagram(globalSvg, 'global', besideThePage(MODEL_SVG))}`;

  if (segments.length <= 1) return whole;

  const parts = segments.map((segment) => {
    const names = segment.sliceIds
      .map((id) => model.slices.find((slice) => slice.id === id)?.name ?? id)
      .join(', ');
    return `  <h3 class="segment">${escapeHtml(segmentRange(segment))} <span class="note">${escapeHtml(names)}</span></h3>
  ${diagram(segmentSvgs.get(segment.index), `segment-${String(segment.index)}`, besideThePage(segmentArtifact(segment.index, 'svg')))}`;
  });

  return `${whole}

  <h3 class="segment-heading">In ${String(segments.length)} segments</h3>
  <p class="lede">The same timeline, cut into runs of whole slices that each stay legible at this width.
     Read them in order — together they are the one model above. Frame numbers are global, so a box keeps
     its number here, in its own slice diagram, and in the whole timeline.</p>
${parts.join('\n')}`;
}

export interface PageInput {
  model: Model;
  globalSvg: string;
  /** Keyed by 1-based segment index, as `segmentArtifact` names them. Unused by a single-segment model. */
  segmentSvgs?: ReadonlyMap<number, string> | undefined;
  sliceSvgs: ReadonlyMap<string, string>;
  /** Repository-relative path of the source, named on the page so nobody edits the wrong file. */
  sourcePath: string;
  /** The services `project.json` lists; the bounded-context canvases are projected over them. None: no canvases. */
  services?: readonly ServiceRecord[] | undefined;
}

export function renderPage({
  model,
  globalSvg,
  segmentSvgs = new Map(),
  sliceSvgs,
  sourcePath,
  services = [],
}: PageInput): string {
  const counts = model.slices.reduce<Record<string, number>>((acc, slice) => {
    acc[slice.status] = (acc[slice.status] ?? 0) + 1;
    return acc;
  }, {});
  const summary = Object.entries(counts)
    .map(([status, count]) => `${String(count)} ${status}`)
    .join(' · ');

  const statuses = present(
    STATUSES,
    model.slices.map((slice) => slice.status),
  );
  const patterns = present(
    PATTERNS,
    model.slices.map((slice) => slice.pattern),
  );

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Global event model</title>
<style>
  :root { color-scheme: light dark; --fg: #1a1a1a; --muted: #5f5f5f; --bg: #ffffff; --line: #e2e2e2; --panel: #fafafa; }
  @media (prefers-color-scheme: dark) {
    :root { --fg: #e8e8e8; --muted: #a6a6a6; --bg: #16181c; --line: #2f333a; --panel: #1d2025; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 2rem 1.5rem 4rem; background: var(--bg); color: var(--fg);
         font: 16px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
  h2 { font-size: 1.15rem; margin: 2.5rem 0 .75rem; padding-bottom: .35rem; border-bottom: 1px solid var(--line); }
  h3 { font-size: 1rem; margin: 0; display: inline; }
  h3.segment { display: block; margin: 1.25rem 0 .5rem; font-size: .9rem; }
  h3.segment .note { color: var(--muted); font-weight: 400; }
  h3.segment-heading { display: block; margin: 2rem 0 .35rem; font-size: 1rem; }
  /* Anchors land under the sticky jump bar without this, which makes every link feel broken. */
  h2[id], .slice[id] { scroll-margin-top: 4rem; }
  p.lede { color: var(--muted); margin: 0 0 .5rem; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85em; }
  a { color: inherit; }
  /* Mermaid draws box labels as foreignObject HTML, which inherits the page colour. On a dark theme that
     is near-white text on a white box — invisible. The diagram keeps its own light surface, so the text
     colour is stated here rather than inherited. */
  figure { margin: 0; padding: .75rem; background: #ffffff; color: #1a1a1a; border: 1px solid var(--line);
           border-radius: 8px; overflow-x: auto; }
  figure svg { max-width: 100%; height: auto; display: block; }

  .diagram { margin: 0; }
  .diagram .zoomer { position: absolute; width: 1px; height: 1px; opacity: 0; }
  .diagram .controls { display: flex; gap: .5rem; justify-content: flex-end; margin: 0 0 .4rem; }
  .control { font-size: .74rem; letter-spacing: .02em; color: var(--muted); background: var(--panel);
             border: 1px solid var(--line); border-radius: 999px; padding: .2rem .6rem; cursor: pointer;
             text-decoration: none; white-space: nowrap; }
  .control:hover, .zoomer:focus-visible ~ .controls .control, .filter:focus-visible + .filter-row .control { color: var(--fg); border-color: var(--muted); }
  .diagram label.control::after { content: "⤢ full size"; }
  .diagram .zoomer:checked ~ .controls label.control::after { content: "⤡ fit width"; }
  /* Full size means the width Mermaid asked for, with the figure scrolling — not a scaled-down smear. */
  .diagram .zoomer:checked ~ figure svg { max-width: none; width: var(--natural); }

  /* The jump bar stays put, because the register scrolls away exactly when it becomes useful. */
  .jump { position: sticky; top: 0; z-index: 2; display: flex; gap: .35rem; align-items: center;
          margin: 1rem 0 0; padding: .5rem 0; background: var(--bg); border-bottom: 1px solid var(--line);
          overflow-x: auto; scrollbar-width: thin; }
  .jump a { font-size: .76rem; color: var(--muted); text-decoration: none; padding: .2rem .5rem;
            border-radius: 999px; white-space: nowrap; }
  .jump a:hover { color: var(--fg); background: var(--panel); }
  .jump a.anchor { color: var(--fg); font-weight: 600; }

  .filters { margin: 1rem 0 1.5rem; }
  .filter { position: absolute; width: 1px; height: 1px; opacity: 0; }
  .filter-row { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; margin: 0 0 .4rem; }
  .filter-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
                  min-width: 4.5rem; }
  .no-match { display: none; margin: 1rem 0; padding: .75rem 1rem; border: 1px dashed var(--line);
              border-radius: 8px; color: var(--muted); font-size: .88rem; }

  table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { font-size: .74rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
  .badge { display: inline-block; padding: .1rem .45rem; border-radius: 999px; color: #fff;
           font-size: .72rem; letter-spacing: .02em; vertical-align: middle; }
  .none { color: var(--muted); }
  .legend { display: flex; flex-wrap: wrap; gap: .6rem; padding: 0; margin: 0 0 1rem; list-style: none; }
  .legend li { display: flex; align-items: center; gap: .45rem; padding: .3rem .6rem; border: 1px solid var(--line);
               border-radius: 999px; background: var(--panel); font-size: .8rem; }
  .legend .chip { width: 1.1rem; height: .8rem; border-radius: 3px; }
  .legend .note { color: var(--muted); }
  .slice { margin: 1.5rem 0; padding: 1rem; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
  .slice summary { cursor: pointer; margin: 0 0 .85rem; }
  .slice summary::marker { color: var(--muted); }
  .slice dl { display: flex; flex-wrap: wrap; gap: .35rem 1.5rem; margin: 0 0 .85rem; font-size: .84rem; }
  .slice dt { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; }
  .slice dd { margin: 0; }

  /* The bounded-context canvases: the same card as a slice, with the canvas's panels laid out in columns. */
  .context { margin: 1.5rem 0; padding: 1rem; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
  .context summary { cursor: pointer; margin: 0 0 .85rem; }
  .context summary::marker { color: var(--muted); }
  .context .note { color: var(--muted); font-size: .84rem; }
  .context .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: .75rem; }
  .context .panel { padding: .6rem .75rem; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; font-size: .84rem; }
  .context .panel h4 { margin: 0 0 .4rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
  .context .panel p, .context .panel ul { margin: 0; }
  .context .panel ul { padding-left: 1.1rem; }
  .context.unplaced { border-style: dashed; }
  .context.unplaced h3 { display: inline; }
  .context.unplaced ul { margin: .5rem 0 0; padding-left: 1.1rem; font-size: .88rem; }

  /* The wireframes. A white box is a screen, so the slice shows the states of it that exist. */
  .screens { --mock-w: ${String(PREVIEW.width)}px; --mock-h: ${String(PREVIEW.height)}px;
             --shot-scale: ${String(PREVIEW.scale)};
             --shot-w: ${String(Math.round(PREVIEW.width * PREVIEW.scale))}px;
             --shot-h: ${String(Math.round(PREVIEW.height * PREVIEW.scale))}px;
             margin-top: 1rem; }
  .screens h4 { margin: 1rem 0 .5rem; font-size: .82rem; font-weight: 600; }
  .screens h4 .none { font-weight: 400; }
  .shots { display: flex; flex-wrap: wrap; gap: .8rem; margin: 0; padding: 0; list-style: none; }
  .shots figure { margin: 0; padding: 0; border: 0; background: none; width: var(--shot-w); }
  .shots figcaption { margin-top: .35rem; font-size: .78rem; color: var(--muted); }
  .shots figcaption a { text-decoration: none; }
  .shots figure:hover figcaption a { text-decoration: underline; }
  .shot { position: relative; width: var(--shot-w); height: var(--shot-h); overflow: hidden;
          border: 1px solid var(--line); border-radius: 6px; background: #ffffff; }
  .shots figure:hover .shot { border-color: var(--muted); }
  /* Rendered at a real screen width and scaled, so the layout under review is the layout on show. */
  .shot iframe { position: absolute; top: 0; left: 0; width: var(--mock-w); height: var(--mock-h);
                 border: 0; transform: scale(var(--shot-scale)); transform-origin: 0 0; }
  .shot img { display: block; width: 100%; height: 100%; object-fit: cover; object-position: top; }
  /* Over the frame, so the thumbnail is one click target and the mock cannot be half-operated in it. */
  .shot .hit { position: absolute; inset: 0; }
  .shot .offsite { position: absolute; inset: 0; margin: 0; display: grid; place-items: center;
                   background: var(--panel); color: var(--muted); font-size: .78rem; }

${filterRules(statuses, patterns, model)}

  /* Paper has no controls, so it gets everything and none of the affordances. */
  @media print {
    body { padding: 0; }
    .jump, .filters, .diagram .controls { display: none; }
    .slice, figure, .shots li { break-inside: avoid; }
    [data-status] { display: revert !important; }
  }
</style>
</head>
<body>
<main>
  <h1>Global event model</h1>
  <p class="lede">${escapeHtml(String(model.slices.length))} slices — ${escapeHtml(summary || 'none yet')}.</p>
  <p class="lede">Generated from <code>${escapeHtml(sourcePath)}</code> by <code>make model</code>. Edit the
     YAML, never this page.</p>

${jumpBar(model)}

  <div class="filters">
${filterRow('status', 'Status', statuses)}
${filterRow('pattern', 'Pattern', patterns)}
  </div>
  <p class="no-match">No slice has that combination of status and pattern.</p>

  <h2 id="timeline">Timeline</h2>
  <ul class="legend">
${SWATCHES.map(
  (s) =>
    `    <li><span class="chip" style="background:${s.fill};border:1px solid ${s.stroke}"></span>` +
    `<strong>${s.label}</strong><span class="note">${s.note}</span></li>`,
).join('\n')}
  </ul>
${timeline(model, globalSvg, segmentSvgs)}

  <h2 id="register">Slices</h2>
  <table>
    <thead>
      <tr><th>Id</th><th>Capability</th><th>Pattern</th><th>Status</th><th>Actor</th><th>Service</th><th>Context</th>
          <th>Stream identity</th><th>Scenarios</th><th>Code</th></tr>
    </thead>
    <tbody>
${model.slices.map(sliceRow).join('\n')}
    </tbody>
  </table>
${contextsSection(model, services)}

  <h2>Slice by slice</h2>
${model.slices.map((slice) => sliceSection(slice, sliceSvgs.get(slice.id))).join('\n')}
</main>
</body>
</html>
`;
}
