/**
 * The gate. Validates the global event model and proves its committed diagram is the current one.
 *
 * Run with: make check-model — part of `make verify` and `make ci`.
 *
 * Deliberately browser-free, so it costs nothing to run on every commit. Staleness is decided by the hash
 * `render.ts` stamps into the SVG rather than by re-rendering: if the SVG's hash is not the hash of the
 * Mermaid this model produces now, the committed picture is out of date, and that is a build failure for
 * the same reason a stale lockfile is.
 */
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { extractHash, renderGlobalMermaid, renderSegmentMermaid } from './mermaid.ts';
import { locateReadmeBlock, readmeSectionIsCurrent, renderReadmeSection } from './readme.ts';
import { validate, type Violation } from './validate.ts';
import { segmentModel, type Model } from './model.ts';
import {
  createWorkspace,
  loadModel,
  MODEL_MERMAID,
  MODEL_SOURCE,
  MODEL_SVG,
  README,
  ROOT,
  SEGMENT_DIR,
  segmentArtifact,
} from './workspace.ts';

const REGENERATE = 'run `make model` and commit the result';

/**
 * The README's event-model block, if it has one.
 *
 * **A README with no markers is not a violation.** The block is opt-in, and every project generated from
 * this template inherits whatever README it was given — nagging about an absent section would make this
 * gate noise in exactly the projects that deliberately dropped it. A *malformed* pair is reported, because
 * that is a mistake rather than a choice, and a stale block is reported for the same reason a stale SVG is:
 * the README is what people read.
 */
function readmeViolations(model: Model): Violation[] {
  let readme: string;
  try {
    readme = readFileSync(join(ROOT, README), 'utf8');
  } catch {
    return [];
  }

  const located = locateReadmeBlock(readme);
  if (!located.present) {
    return located.reason === 'absent'
      ? []
      : [
          {
            rule: 'readme-block-current',
            message:
              `${README} has one event-model marker without its pair, or has them in the wrong order. ` +
              'Either both markers or neither',
          },
        ];
  }

  if (!readmeSectionIsCurrent(readme, renderReadmeSection(model))) {
    return [
      {
        rule: 'readme-block-current',
        message: `${README}'s event-model block does not match ${MODEL_SOURCE} — ${REGENERATE}`,
      },
    ];
  }

  return [];
}

function artifactViolations(expectedMermaid: string): Violation[] {
  const violations: Violation[] = [];
  const mermaidPath = join(ROOT, MODEL_MERMAID);

  if (!existsSync(mermaidPath)) {
    return [{ rule: 'diagram-current', message: `${MODEL_MERMAID} is missing — ${REGENERATE}` }];
  }

  if (readFileSync(mermaidPath, 'utf8') !== expectedMermaid) {
    violations.push({
      rule: 'diagram-current',
      message: `${MODEL_MERMAID} does not match ${MODEL_SOURCE} — ${REGENERATE}`,
    });
  }

  const svgPath = join(ROOT, MODEL_SVG);
  if (!existsSync(svgPath)) {
    violations.push({ rule: 'diagram-current', message: `${MODEL_SVG} is missing — ${REGENERATE}` });
    return violations;
  }

  const rendered = extractHash(readFileSync(svgPath, 'utf8'));
  const expected = extractHash(expectedMermaid);
  if (rendered !== expected) {
    violations.push({
      rule: 'diagram-current',
      message:
        `${MODEL_SVG} was rendered from an older model — ${REGENERATE}. ` +
        'The picture in the repository is what reviewers read, so a stale one is worse than none',
    });
  }

  return violations;
}

/**
 * The README's segment images, which are the diagrams most people actually see.
 *
 * Checked exactly like the global SVG — same hash, same reasoning — plus one thing the global SVG cannot
 * go wrong in: an *extra* segment. Shrink a model and re-render and the leftover file is deleted, but a
 * commit that updates the YAML without re-rendering leaves `model-4.svg` on disk with the README no longer
 * pointing at it. Nothing would ever look at it again, and it would sit there looking generated and
 * current.
 */
function segmentViolations(model: Model): Violation[] {
  const violations: Violation[] = [];
  const segments = segmentModel(model);

  for (const segment of segments) {
    const mermaidPath = segmentArtifact(segment.index, 'mmd');
    const svgPath = segmentArtifact(segment.index, 'svg');
    const expected = renderSegmentMermaid(model, segment.sliceIds);

    if (!existsSync(join(ROOT, mermaidPath))) {
      violations.push({ rule: 'diagram-current', message: `${mermaidPath} is missing — ${REGENERATE}` });
      continue;
    }
    if (readFileSync(join(ROOT, mermaidPath), 'utf8') !== expected) {
      violations.push({
        rule: 'diagram-current',
        message: `${mermaidPath} does not match ${MODEL_SOURCE} — ${REGENERATE}`,
      });
    }
    if (!existsSync(join(ROOT, svgPath))) {
      violations.push({ rule: 'diagram-current', message: `${svgPath} is missing — ${REGENERATE}` });
      continue;
    }
    if (extractHash(readFileSync(join(ROOT, svgPath), 'utf8')) !== extractHash(expected)) {
      violations.push({
        rule: 'diagram-current',
        message: `${svgPath} was rendered from an older model — ${REGENERATE}`,
      });
    }
  }

  const orphans = existsSync(join(ROOT, SEGMENT_DIR))
    ? readdirSync(join(ROOT, SEGMENT_DIR)).filter((entry) => {
        const index = /^model-(\d+)\.(?:mmd|svg)$/.exec(entry)?.[1];
        return index === undefined || Number(index) > segments.length;
      })
    : [];

  for (const orphan of orphans) {
    violations.push({
      rule: 'diagram-current',
      message:
        `${SEGMENT_DIR}/${orphan} belongs to no segment of the current timeline — ${REGENERATE}. ` +
        'A leftover diagram nothing links to is the kind of stale that never gets noticed',
    });
  }

  return violations;
}

function report(violations: readonly Violation[]): void {
  const byRule = new Map<string, Violation[]>();
  for (const violation of violations) {
    byRule.set(violation.rule, [...(byRule.get(violation.rule) ?? []), violation]);
  }

  console.error('');
  console.error(`check-model: ${String(violations.length)} problem(s) in ${MODEL_SOURCE}`);
  for (const [rule, group] of byRule) {
    console.error('');
    console.error(`  ${rule}`);
    for (const violation of group) {
      const where = violation.slice === undefined ? '' : `${violation.slice}: `;
      console.error(`    - ${where}${violation.message}`);
    }
  }
  console.error('');
}

function main(): void {
  const model = loadModel();

  if (model.slices.length === 0) {
    // Still worth checking the README: a block left saying "4 slices" after the model was emptied is drift
    // in the direction that misleads, and there is no diagram to catch it.
    const stale = readmeViolations(model);
    if (stale.length > 0) {
      report(stale);
      process.exitCode = 1;
      return;
    }
    console.log(`check-model: ${MODEL_SOURCE} has no slices yet — nothing to check.`);
    console.log('That is the right state until the first modelling session; it is not a passing model.');
    return;
  }

  const violations = [
    ...validate(model, createWorkspace(model)),
    ...artifactViolations(renderGlobalMermaid(model)),
    ...segmentViolations(model),
    ...readmeViolations(model),
  ];

  if (violations.length > 0) {
    report(violations);
    process.exitCode = 1;
    return;
  }

  const implemented = model.slices.filter((slice) => slice.status === 'implemented').length;
  console.log(
    `check-model: ${String(model.slices.length)} slices consistent, ` +
      `${String(implemented)} implemented, diagram current.`,
  );
}

main();
