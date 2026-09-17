/**
 * Applies mermaid-js/mermaid#7986 to the mermaid-cli install `make model` fetches.
 *
 * Upstream still ships eventmodeling swimlanes that never store `namespace`, so every namespaced box
 * opens a new lane (mermaid-js/mermaid#7925). The generator already emits the documented identifiers;
 * this file is the local renderer half, so `render.actorLanes` can stay on. Delete it the day
 * mermaid-cli ships a mermaid that already has the fix — the matcher below becomes a no-op then, and
 * failing to find either shape is how a future pin tells us the chunk moved.
 *
 * The needles are the unminified `mermaid.esm` emit of mermaid 11.16.x–11.17.x, which is what
 * mermaid-cli 11.16.0 loads. Minified copies are left alone; mermaid-cli does not use them.
 */
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export type SwimlaneFixStatus = 'patched' | 'already' | 'absent';

const BROKEN_FIND = `function findSwimlaneByNamespace(swimlanes, namespace) {
  if (!namespace || namespace.length === 0) {
    return void 0;
  }
  return Object.values(swimlanes).find((swimlane) => swimlane.namespace === namespace);
}`;

const FIXED_FIND = `function findSwimlaneByNamespace(swimlanes, namespace, boundaryMin, boundaryMax) {
  if (!namespace || namespace.length === 0) {
    return void 0;
  }
  return Object.values(swimlanes).find(
    (swimlane) =>
      swimlane.namespace === namespace &&
      swimlane.index > boundaryMin &&
      swimlane.index < boundaryMax
  );
}`;

const BROKEN_CALCULATE = `function calculateSwimlaneProps(frame, swimlanes) {
  const namespace = extractNamespace(frame.entityIdentifier);
  const sw = findSwimlaneByNamespace(swimlanes, namespace);
  switch (frame.modelEntityType) {
    case "ui":
    case "pcr":
    case "processor":
      if (sw) {
        return {
          index: sw.index,
          label: sw.namespace || diagramProps.labelUiAutomation
        };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 0, 100),
          label: diagramProps.labelUiAutomationPrefix + namespace
        };
      }
      return { index: 0, label: diagramProps.labelUiAutomation };
    case "rmo":
    case "readmodel":
    case "cmd":
    case "command":
      if (sw) {
        return {
          index: sw.index,
          label: sw.namespace || diagramProps.labelCommandReadModel
        };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 100, 200),
          label: diagramProps.labelCommandReadModelPrefix + namespace
        };
      }
      return { index: 100, label: diagramProps.labelCommandReadModel };
    case "evt":
    case "event":
    default:
      if (sw) {
        return {
          index: sw.index,
          label: sw.namespace || diagramProps.labelEvents
        };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 200, 300),
          label: diagramProps.labelEventsPrefix + namespace
        };
      }
      return { index: 200, label: diagramProps.labelEvents };
  }
}`;

const FIXED_CALCULATE = `function calculateSwimlaneProps(frame, swimlanes) {
  const namespace = extractNamespace(frame.entityIdentifier);
  switch (frame.modelEntityType) {
    case "ui":
    case "pcr":
    case "processor": {
      const sw = findSwimlaneByNamespace(swimlanes, namespace, 0, 100);
      if (sw) {
        return { index: sw.index, label: sw.label, namespace: sw.namespace };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 0, 100),
          label: diagramProps.labelUiAutomationPrefix + namespace,
          namespace
        };
      }
      return { index: 0, label: diagramProps.labelUiAutomation };
    }
    case "rmo":
    case "readmodel":
    case "cmd":
    case "command": {
      const sw = findSwimlaneByNamespace(swimlanes, namespace, 100, 200);
      if (sw) {
        return { index: sw.index, label: sw.label, namespace: sw.namespace };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 100, 200),
          label: diagramProps.labelCommandReadModelPrefix + namespace,
          namespace
        };
      }
      return { index: 100, label: diagramProps.labelCommandReadModel };
    }
    case "evt":
    case "event":
    default: {
      const sw = findSwimlaneByNamespace(swimlanes, namespace, 200, 300);
      if (sw) {
        return { index: sw.index, label: sw.label, namespace: sw.namespace };
      } else if (namespace) {
        return {
          index: findNextAvailableIndex(swimlanes, 200, 300),
          label: diagramProps.labelEventsPrefix + namespace,
          namespace
        };
      }
      return { index: 200, label: diagramProps.labelEvents };
    }
  }
}`;

const BROKEN_CREATE = `    swimlane = {
      index: swimlaneProps.index,
      label: swimlaneProps.label,
      r: 0,`;

const FIXED_CREATE = `    swimlane = {
      index: swimlaneProps.index,
      label: swimlaneProps.label,
      namespace: swimlaneProps.namespace,
      r: 0,`;

const ALREADY = 'function findSwimlaneByNamespace(swimlanes, namespace, boundaryMin, boundaryMax)';

/** One mermaid.esm chunk, or any other file that happens to carry the same emit. */
export function applySwimlaneFix(source: string): { text: string; status: SwimlaneFixStatus } {
  if (source.includes(ALREADY)) {
    return { text: source, status: 'already' };
  }
  if (!source.includes(BROKEN_FIND)) {
    return { text: source, status: 'absent' };
  }
  if (!source.includes(BROKEN_CALCULATE) || !source.includes(BROKEN_CREATE)) {
    throw new Error(
      'mermaid eventmodeling swimlane code is the broken shape of #7925 but not the emit this patcher ' +
        'was written against — mermaid-cli was likely unpinned. Restore the pin or rewrite the patcher.',
    );
  }
  const text = source.replace(BROKEN_FIND, FIXED_FIND).replace(BROKEN_CALCULATE, FIXED_CALCULATE).replace(BROKEN_CREATE, FIXED_CREATE);
  return { text, status: 'patched' };
}

function mermaidPackageRoots(cliPrefix: string): string[] {
  const candidates = [
    join(cliPrefix, 'node_modules', 'mermaid'),
    join(cliPrefix, 'node_modules', '@mermaid-js', 'mermaid-cli', 'node_modules', 'mermaid'),
  ];
  return candidates.filter((root) => {
    try {
      readdirSync(root);
      return true;
    } catch {
      return false;
    }
  });
}

function esmChunks(mermaidRoot: string): string[] {
  const dir = join(mermaidRoot, 'dist', 'chunks', 'mermaid.esm');
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return [];
  }
  return names.filter((name) => name.endsWith('.mjs') && !name.endsWith('.map')).map((name) => join(dir, name));
}

/**
 * Patches every unminified eventmodeling chunk under a mermaid-cli prefix.
 *
 * Throws if mermaid is present and none of its esm chunks look like either the known-broken emit or
 * the already-fixed one — that is a pin that moved, not a success.
 */
export function patchInstalledMermaid(cliPrefix: string): void {
  const roots = mermaidPackageRoots(cliPrefix);
  if (roots.length === 0) {
    throw new Error(`no mermaid package under ${cliPrefix} — mermaid-cli did not install`);
  }
  let seen = 0;
  for (const root of roots) {
    for (const path of esmChunks(root)) {
      const current = readFileSync(path, 'utf8');
      const { text, status } = applySwimlaneFix(current);
      if (status === 'absent') continue;
      seen += 1;
      if (status === 'patched') {
        writeFileSync(path, text, 'utf8');
      }
    }
  }
  if (seen === 0) {
    throw new Error(
      `mermaid under ${cliPrefix} has no eventmodeling swimlane emit this patcher recognises ` +
        '(mermaid-js/mermaid#7925 / #7986). The mermaid-cli pin likely pulled a new chunk layout.',
    );
  }
}
