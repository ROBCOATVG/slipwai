/**
 * The filesystem half: where the model lives, how it is loaded, and the two questions `validate.ts` asks
 * about the repository.
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, posix } from 'node:path';

import { parse as parseYaml } from 'yaml';

import { MODEL_DIR_POSIX, parseModel, type Model } from './model.ts';
import type { Workspace } from './validate.ts';

export const ROOT = process.cwd();
/**
 * Platform-joined, and derived from the forward-slashed constant `validate.ts` uses rather than written out
 * again. Two literals for one directory is how the publish rule and the publish workflow drift apart.
 */
export const MODEL_DIR = join(...MODEL_DIR_POSIX.split('/'));
export const MODEL_SOURCE = join(MODEL_DIR, 'model.yaml');
export const MODEL_MERMAID = join(MODEL_DIR, 'model.mmd');
export const MODEL_SVG = join(MODEL_DIR, 'model.svg');
export const MODEL_PNG = join(MODEL_DIR, 'model.png');
export const MODEL_HTML = join(MODEL_DIR, 'model.html');
export const SLICE_DIR = join(MODEL_DIR, 'slices');
export const SEGMENT_DIR = join(MODEL_DIR, 'segments');

/**
 * The project README, which carries the generated event-model block when it has the markers for it.
 *
 * At the root rather than in `MODEL_DIR`, because the point is that the model appears where people already
 * look. A model nobody sees is a model nobody notices has gone stale.
 */
export const README = 'README.md';

/** The project manifest: which services exist, and what each says it owns. */
export const MANIFEST = 'project.json';

/**
 * One service as `project.json` records it, as far as the model cares: its name (what a slice's `service`
 * names), where it lives, what it owns, and the bounded contexts it holds (what a slice's `context` names) —
 * several when the service is the modular monolith a project starts as, itself when it names none.
 */
export interface ServiceRecord {
  name: string;
  path: string;
  purpose?: string | undefined;
  contexts: readonly string[];
}

/**
 * The services in `project.json`, in the order the manifest lists them.
 *
 * Read rather than discovered from `apps/`: the manifest is the one list every other reader of this
 * repository uses (the Makefile, Compose, CI, the import gate), and a directory under `apps/` that is not on
 * it is not a service. An unreadable or absent manifest is an empty list, not an error — the rules that
 * need it then have nothing to require, and the manifest's own readers are the ones that report it.
 */
export function loadServices(): ServiceRecord[] {
  const path = join(ROOT, MANIFEST);
  if (!existsSync(path)) {
    return [];
  }
  let document: unknown;
  try {
    document = JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    return [];
  }
  const deployables =
    typeof document === 'object' && document !== null && 'deployables' in document
      ? (document as { deployables: unknown }).deployables
      : undefined;
  if (typeof deployables !== 'object' || deployables === null) {
    return [];
  }
  return Object.entries(deployables as Record<string, unknown>).flatMap(([name, record]) => {
    if (typeof record !== 'object' || record === null) return [];
    const entry = record as Record<string, unknown>;
    if (entry['kind'] !== 'service') return [];
    // `contexts` as written now; the one `context` a manifest written before a service could hold several
    // named, read as a list of one; the service itself when it names none.
    const listed = Array.isArray(entry['contexts'])
      ? entry['contexts'].filter((item): item is string => typeof item === 'string' && item !== '')
      : [];
    const single = typeof entry['context'] === 'string' && entry['context'] !== '' ? [entry['context']] : [name];
    return [
      {
        name,
        path: typeof entry['path'] === 'string' ? entry['path'] : `apps/${name}`,
        purpose: typeof entry['purpose'] === 'string' && entry['purpose'] !== '' ? entry['purpose'] : undefined,
        contexts: listed.length > 0 ? listed : single,
      },
    ];
  });
}

/**
 * Trees searched by `sourceMentions`. Anything outside them is not this project's implementation.
 *
 * `apps` is where this monorepo keeps its deployables (one directory per service, plus `apps/web`); `src` and `tests`
 * cover a project that later flattens to a single-app layout.
 */
const SOURCE_TREES = ['apps', 'src', 'tests'] as const;

/**
 * Extensions counted as this project's source.
 *
 * `.ts` alone was the whole list while the only thing checked was an event name, which is always written
 * in TypeScript. A white box is a *screen*, and a screen is written in whatever the frontend is — so a
 * corpus of `.ts` files could not see a component and reported every screen as unbuilt. Widening can only
 * make `sourceMentions` answer *yes* more often, so it cannot fail a model that passes today.
 */
const SOURCE_EXTENSIONS = [
  '.ts',
  '.tsx',
  '.mts',
  '.cts',
  '.js',
  '.jsx',
  '.mjs',
  '.vue',
  '.svelte',
  '.astro',
  // This factory generates Python and Go backends beside TypeScript ones, and an event lives in
  // whichever language the service is written in.
  '.py',
  '.go',
] as const;

export function loadModel(): Model {
  const path = join(ROOT, MODEL_SOURCE);
  if (!existsSync(path)) {
    throw new Error(
      `${MODEL_SOURCE} is missing. It is the global event model — restore it from the template rather ` +
        'than starting a second one somewhere else.',
    );
  }
  return parseModel(parseYaml(readFileSync(path, 'utf8')));
}

function* walkSource(dir: string): Generator<string> {
  if (!existsSync(dir)) {
    return;
  }
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      yield* walkSource(full);
    } else if (SOURCE_EXTENSIONS.some((extension) => entry.endsWith(extension))) {
      yield full;
    }
  }
}

/**
 * The files every slice names in `code`, wherever they live.
 *
 * The trees above are this template's own convention, and a project is free to put its frontend somewhere
 * else. Rather than guess at a list of directories a frontend might be in — a list that would be wrong for
 * the first project that chose differently — the model is asked: `code` already names the files that
 * realise each slice, and `code-recorded` already proves they exist. So the corpus is "our trees, plus
 * wherever the model says its code is", and no layout is assumed.
 *
 * Missing paths are skipped rather than thrown on: `code-recorded` is the rule that reports them, and a
 * gate that crashes instead of reporting tells you nothing about the other twelve slices.
 */
function codeFiles(model: Model): string[] {
  return model.slices
    .flatMap((slice) => slice.code ?? [])
    .map((path) => join(ROOT, ...path.split('/')))
    .filter((path) => existsSync(path) && statSync(path).isFile());
}

export function createWorkspace(model: Model): Workspace {
  // Read once: a model with thirty slices asks about a hundred identifiers, and re-reading the tree for
  // each one turns a fast gate into one people skip.
  let corpus: string | undefined;
  const readCorpus = (): string => {
    corpus ??= [
      ...new Set([...SOURCE_TREES.flatMap((tree) => [...walkSource(join(ROOT, tree))]), ...codeFiles(model)]),
    ]
      .map((file) => readFileSync(file, 'utf8'))
      .join('\n');
    return corpus;
  };

  return {
    exists(path: string): boolean {
      return existsSync(join(ROOT, path));
    },
    sourceMentions(identifier: string): boolean {
      return new RegExp(`\\b${identifier}\\b`).test(readCorpus());
    },
    services(): readonly string[] {
      return loadServices().map((service) => service.name);
    },
    contextsOf(service: string): readonly string[] {
      return loadServices().find((record) => record.name === service)?.contexts ?? [];
    },
  };
}

/** Slice diagram paths use forward slashes so the generated HTML works on every platform. */
export function sliceArtifact(sliceId: string, extension: 'mmd' | 'svg'): string {
  return posix.join(MODEL_DIR_POSIX, 'slices', `${sliceId}.${extension}`);
}

/**
 * Segment diagram paths, forward-slashed for the same reason — these end up in the README, which is read
 * on a forge as often as on a filesystem.
 */
export function segmentArtifact(index: number, extension: 'mmd' | 'svg'): string {
  return posix.join(MODEL_DIR_POSIX, 'segments', `model-${String(index)}.${extension}`);
}
