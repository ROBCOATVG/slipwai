/**
 * Regenerates every artifact the model produces: Mermaid source, SVGs, and the browsable page.
 *
 * Run with: make model            (add PNG=1 for a raster copy)
 *
 * Mermaid CLI is fetched on demand into `scripts/event-model/.mermaid-cli/` rather than being a
 * devDependency, because it pulls a headless browser: making every `npm install` in the project pay for
 * that, so that one person can regenerate a diagram, is a poor trade. The local prefix exists so the
 * swimlane patch (mermaid-js/mermaid#7986, until mermaid-cli ships it) can run against a tree we own.
 * `make check-model` needs no browser at all, which is why *it* is the gate that runs in CI.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { extractHash, renderGlobalMermaid, renderSegmentMermaid, renderSliceMermaid } from './mermaid.ts';
import { patchInstalledMermaid } from './patch-mermaid-swimlanes.ts';
import { renderPage } from './page.ts';
import { renderReadmeSection, withReadmeSection } from './readme.ts';
import { segmentModel, type Model } from './model.ts';
import {
  loadModel,
  loadServices,
  MODEL_HTML,
  MODEL_MERMAID,
  MODEL_PNG,
  MODEL_SOURCE,
  MODEL_SVG,
  README,
  ROOT,
  SEGMENT_DIR,
  segmentArtifact,
  SLICE_DIR,
  sliceArtifact,
} from './workspace.ts';

/**
 * Pinned. An unpinned renderer means the committed SVG changes whenever upstream does, and every diff
 * then contains rendering churn nobody authored.
 */
const MERMAID_CLI = '@mermaid-js/mermaid-cli@11.16.0';

/** Wide enough that a dozen slices stay legible; Mermaid scales the viewBox to fit. */
const WIDTH = '2400';

/**
 * Escape hatch for hosts where Puppeteer's download does not exist — Google ships no Chrome for
 * linux/arm64, so `npx mmdc` fails outright on ARM sandboxes and containers. Point this at a Puppeteer
 * JSON config naming an `executablePath` (Playwright's arm64 Chromium works) plus whatever the container
 * needs, typically `"args": ["--no-sandbox", "--disable-dev-shm-usage"]`. Unset, rendering is unchanged.
 */
const PUPPETEER_CONFIG = process.env['MERMAID_PUPPETEER_CONFIG'];
const PUPPETEER_FLAGS = PUPPETEER_CONFIG === undefined || PUPPETEER_CONFIG === ''
  ? []
  : ['--puppeteerConfigFile', PUPPETEER_CONFIG];

const CLI_PREFIX = join(dirname(fileURLToPath(import.meta.url)), '.mermaid-cli');

/**
 * mermaid-cli, installed once into a gitignored prefix so we can patch its mermaid before the first
 * render. `npx -y` would run the binary before we could touch the tree.
 */
function mermaidCli(): string {
  const bin = join(CLI_PREFIX, 'node_modules', '.bin', 'mmdc');
  if (!existsSync(bin)) {
    mkdirSync(CLI_PREFIX, { recursive: true });
    const manifest = join(CLI_PREFIX, 'package.json');
    if (!existsSync(manifest)) {
      writeFileSync(manifest, '{"name":"event-model-mermaid-cli","private":true}\n');
    }
    execFileSync('npm', ['install', '--no-audit', '--no-fund', '--loglevel=error', MERMAID_CLI], {
      cwd: CLI_PREFIX,
      stdio: 'inherit',
    });
  }
  patchInstalledMermaid(CLI_PREFIX);
  return bin;
}

/**
 * Runs mermaid-cli once. Chromium refuses to start as root without `--no-sandbox`, which is how every rootless
 * container fails here; when that is the situation and no Puppeteer config was given, say which variable
 * fixes it before rethrowing, rather than leaving Chromium's own message to be searched for.
 */
function runMermaid(args: string[]): void {
  try {
    execFileSync(mermaidCli(), [...args, ...PUPPETEER_FLAGS], { cwd: ROOT, stdio: 'inherit' });
  } catch (error) {
    if (PUPPETEER_FLAGS.length === 0 && typeof process.getuid === 'function' && process.getuid() === 0) {
      process.stderr.write(
        'render: running as root, and Chromium will not start without --no-sandbox. Point MERMAID_PUPPETEER_CONFIG '
          + 'at a JSON file such as {"args": ["--no-sandbox", "--disable-dev-shm-usage"]} and rerun; the generated '
          + 'CI workflow does exactly this.\n',
      );
    }
    throw error;
  }
}

function mermaidToSvg(input: string, output: string): void {
  runMermaid(['--input', input, '--output', output, '--width', WIDTH]);
}

function mermaidToPng(input: string, output: string): void {
  runMermaid(['--input', input, '--output', output, '--width', WIDTH, '--backgroundColor', 'white']);
}

/**
 * Copies the source hash from the Mermaid file into the SVG.
 *
 * This is what lets `check-model` tell a current diagram from a stale one without launching a browser: if
 * the hash the SVG carries is not the hash of the Mermaid the model produces now, the picture is old.
 */
function stampSvg(path: string, mermaidSource: string): void {
  const hash = extractHash(mermaidSource);
  if (hash === undefined) {
    throw new Error(`generated Mermaid for ${path} carried no hash — mermaid.ts should always stamp one`);
  }
  const svg = readFileSync(path, 'utf8');
  writeFileSync(path, `<!-- em-source-sha256: ${hash} -->\n${svg}`, 'utf8');
}

function write(relativePath: string, contents: string): void {
  const absolute = join(ROOT, relativePath);
  writeFileSync(absolute, contents, 'utf8');
  console.log(`  wrote ${relativePath}`);
}

/**
 * Refreshes the README's event-model block, if it has one.
 *
 * Silent when the README carries no markers: a project that does not want the section deletes them, and a
 * generator that nagged about it would be a generator people stop running. Runs for an empty model too —
 * "no slices yet" is a true and useful thing for a README to say.
 */
function updateReadme(model: Model): void {
  const path = join(ROOT, README);
  let current: string;
  try {
    current = readFileSync(path, 'utf8');
  } catch {
    return; // No README at all. Not this script's business to create one.
  }

  const updated = withReadmeSection(current, renderReadmeSection(model));
  if (updated === undefined || updated === current) return;

  writeFileSync(path, updated, 'utf8');
  console.log(`  wrote ${README} (event-model block)`);
}

function main(): void {
  const model = loadModel();
  const wantPng = process.env['PNG'] === '1' || process.argv.includes('--png');

  if (model.slices.length === 0) {
    // An empty model is the correct state for a project that has not modelled anything yet, and for this
    // template permanently. Rendering an empty diagram would be a syntax error, and inventing a
    // placeholder slice would be inventing a domain model.
    console.log(`${MODEL_SOURCE} has no slices yet — nothing to render.`);
    console.log('Model your first workflow with the `event-modeling` skill, then run this again.');
    for (const artifact of [MODEL_MERMAID, MODEL_SVG, MODEL_PNG, MODEL_HTML]) {
      rmSync(join(ROOT, artifact), { force: true });
    }
    for (const dir of [SLICE_DIR, SEGMENT_DIR]) {
      rmSync(join(ROOT, dir), { force: true, recursive: true });
    }
    updateReadme(model);
    return;
  }

  const globalMermaid = renderGlobalMermaid(model);
  write(MODEL_MERMAID, globalMermaid);
  mermaidToSvg(MODEL_MERMAID, MODEL_SVG);
  stampSvg(join(ROOT, MODEL_SVG), globalMermaid);
  console.log(`  wrote ${MODEL_SVG}`);

  if (wantPng) {
    mermaidToPng(MODEL_MERMAID, MODEL_PNG);
    console.log(`  wrote ${MODEL_PNG}`);
  }

  // Segments are what the README embeds: whole slices grouped under a frame budget, because one image of
  // a twenty-slice timeline is a coloured smear in a fixed-width column. Regenerated wholesale for the
  // same reason as slice views — a model that shrank must not leave a segment behind claiming to be part
  // of the current timeline.
  rmSync(join(ROOT, SEGMENT_DIR), { force: true, recursive: true });
  mkdirSync(join(ROOT, SEGMENT_DIR), { recursive: true });

  const segmentSvgs = new Map<number, string>();
  for (const segment of segmentModel(model)) {
    const mermaidPath = segmentArtifact(segment.index, 'mmd');
    const svgPath = segmentArtifact(segment.index, 'svg');
    const source = renderSegmentMermaid(model, segment.sliceIds);
    write(mermaidPath, source);
    mermaidToSvg(mermaidPath, svgPath);
    stampSvg(join(ROOT, svgPath), source);
    segmentSvgs.set(segment.index, readFileSync(join(ROOT, svgPath), 'utf8'));
  }

  // Slice views are regenerated wholesale rather than updated, so a renamed or deleted slice cannot leave
  // an orphan diagram behind claiming to be current.
  rmSync(join(ROOT, SLICE_DIR), { force: true, recursive: true });
  mkdirSync(join(ROOT, SLICE_DIR), { recursive: true });

  const sliceSvgs = new Map<string, string>();
  for (const slice of model.slices) {
    const mermaidPath = sliceArtifact(slice.id, 'mmd');
    const svgPath = sliceArtifact(slice.id, 'svg');
    const source = renderSliceMermaid(model, slice.id);
    write(mermaidPath, source);
    mermaidToSvg(mermaidPath, svgPath);
    stampSvg(join(ROOT, svgPath), source);
    sliceSvgs.set(slice.id, readFileSync(join(ROOT, svgPath), 'utf8'));
  }

  write(
    MODEL_HTML,
    renderPage({
      model,
      globalSvg: readFileSync(join(ROOT, MODEL_SVG), 'utf8'),
      segmentSvgs,
      sliceSvgs,
      sourcePath: MODEL_SOURCE,
      services: loadServices(),
    }),
  );

  updateReadme(model);

  console.log('');
  console.log(`model: ${String(model.slices.length)} slices rendered. Open ${MODEL_HTML} to browse it.`);
}

main();
