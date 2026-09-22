/**
 * The committed canvas: writes `docs/event-model/model.drawio` from the model, or proves it is current.
 *
 * Run with: make model-drawio          (write it)
 *           make check-drawio          (regenerate in memory, compare, fail with the fix in the message)
 *
 * This is the one rendering of the model that lives in the repository and is held current by the gate.
 * The Mermaid pipeline (`make model`) drives a headless browser, so nothing browser-free can prove its
 * output current and none of it is committed. A draw.io file is arithmetic and a string: no browser, no
 * account, no network. So it can be committed, diffed line by line, opened and edited by a person, and —
 * the point — regenerated and compared on every commit, inside `make verify`.
 *
 * No layout opinion lives here. `board-plan.ts` decides where everything goes and `drawio.ts` how it is
 * written; this file only knows the path, and whether it was asked to write or to check.
 */
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { planBoard } from './board-plan.ts';
import { renderDrawio } from './drawio.ts';
import { loadModel, MODEL_DIR, MODEL_SOURCE, ROOT } from './workspace.ts';

export const MODEL_DRAWIO = join(MODEL_DIR, 'model.drawio');

const FIX = 'Run make model-drawio and commit the result.';

function main(): void {
  const check = process.argv.includes('--check');
  const model = loadModel();
  const path = join(ROOT, MODEL_DRAWIO);
  // An empty model is the correct state until the first modelling session, and a canvas of nothing would
  // only invite somebody to draw the model there instead of in the YAML. So there is no file, and a file
  // left behind by a model that has since been emptied is stale like any other.
  const expected = model.slices.length === 0 ? undefined : renderDrawio(planBoard(model));

  if (!check) {
    if (expected === undefined) {
      rmSync(path, { force: true });
      console.log(`${MODEL_SOURCE} has no slices yet — nothing to draw, and no ${MODEL_DRAWIO} to keep.`);
      return;
    }
    writeFileSync(path, expected, 'utf8');
    console.log(`  wrote ${MODEL_DRAWIO}`);
    console.log(`model-drawio: ${String(model.slices.length)} slices drawn. Open it in draw.io; commit it with the model.`);
    return;
  }

  if (expected === undefined) {
    if (existsSync(path)) {
      console.error(`check-drawio: ${MODEL_SOURCE} has no slices, but ${MODEL_DRAWIO} still exists. ${FIX}`);
      process.exitCode = 1;
      return;
    }
    console.log(`check-drawio: ${MODEL_SOURCE} has no slices yet — nothing to check.`);
    return;
  }
  if (!existsSync(path)) {
    console.error(`check-drawio: ${MODEL_DRAWIO} is missing. ${FIX}`);
    process.exitCode = 1;
    return;
  }
  if (readFileSync(path, 'utf8') !== expected) {
    console.error(
      `check-drawio: ${MODEL_DRAWIO} is stale — it does not match ${MODEL_SOURCE}. ${FIX} ` +
        'The canvas in the repository is what reviewers open, so a stale one is worse than none.',
    );
    process.exitCode = 1;
    return;
  }
  console.log(`check-drawio: ${MODEL_DRAWIO} is current (${String(model.slices.length)} slices).`);
}

main();
