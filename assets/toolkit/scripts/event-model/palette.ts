/**
 * The colour grammar, once.
 *
 * Mermaid's `emUiFill` and friends, from its eventmodeling renderer — which is what `make model` draws
 * with, so these are the colours the SVGs already carry. The browsable page's legend and the draw.io canvas
 * both read this table rather than keeping one of their own: two renderings of the same model showing two
 * oranges for an event would be two models as far as a reader is concerned, and a table copied into a
 * second file is how that starts.
 *
 * Pure data, on purpose. `board-plan.ts` is not allowed to read anything, and a palette it can import is
 * the only kind it can share with `page.ts`.
 */
import type { FrameType } from './model.ts';

export interface Swatch {
  /** What the legend calls the kind of box. */
  readonly label: string;
  /** One clause on what the kind means, for the legend. */
  readonly note: string;
  readonly fill: string;
  readonly stroke: string;
}

export const SWATCHES: Readonly<Record<FrameType, Swatch>> = {
  ui: { label: 'UI / wireframe', note: 'what the actor sees', fill: '#ffffff', stroke: '#dbdada' },
  pcr: { label: 'Processor', note: 'automation: the conditional logic', fill: '#edb3f6', stroke: '#b88cbf' },
  cmd: { label: 'Command', note: 'an intent that may be rejected', fill: '#bcd6fe', stroke: '#679ac3' },
  rmo: {
    label: 'Read model',
    note: 'a fold over events; never what a command decides from',
    fill: '#d3f1a2',
    stroke: '#a3b732',
  },
  evt: { label: 'Event', note: 'a fact, permanent once written', fill: '#ffb778', stroke: '#c19a0f' },
};
