/**
 * The event names a project already had in a log when the two naming rules reached it.
 *
 * An event in a log keeps its name for as long as the log is kept: a stored event cannot be renamed, so a
 * rule that arrives after it was written has nothing to ask of it that the project could do. `slipwai
 * migrate` writes the names once, at the crossing from version 1, from the slices that were `implemented`
 * then; `event-is-not-crud` and `event-is-not-negative` pass exactly those names and hold every other one
 * as before. A project without the file was made under the rules, and every name it has is held to them.
 *
 * This mirrors `held_event_names` in `check.py`, which is what `make check-model` runs, and imports nothing
 * but Node: the keel's suite runs both readers over the same files to hold them in step, and it does so
 * without an `npm install`.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

/** Where the names are recorded. `check.py` spells the same path. */
export const EVENT_NAMES_FROM = '.specify/event-names-from.json';

const SHAPE =
  'it holds {"events": ["<EventName>", ...]}; restore it with ' +
  `\`git checkout -- ${EVENT_NAMES_FROM}\`, or correct it by hand`;

/**
 * The names neither naming rule asks about, or none where the project has no file.
 *
 * **Absent is no exemption, and unreadable is a failure.** A file that will not parse, or holds anything
 * but a list of names, is not read as "nothing held" — that would fail every stored event with no word
 * about why — and never as "everything held".
 */
export function heldEventNames(root: string): ReadonlySet<string> {
  const path = join(root, ...EVENT_NAMES_FROM.split('/'));
  if (!existsSync(path)) {
    return new Set();
  }
  let held: unknown;
  try {
    held = JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    throw new Error(`${EVENT_NAMES_FROM} is not JSON; ${SHAPE}`);
  }
  const names =
    typeof held === 'object' && held !== null && !Array.isArray(held)
      ? (held as Record<string, unknown>)['events']
      : undefined;
  if (!Array.isArray(names) || names.some((name) => typeof name !== 'string' || name === '')) {
    throw new Error(`${EVENT_NAMES_FROM} names no list of events; ${SHAPE}`);
  }
  return new Set(names as string[]);
}
