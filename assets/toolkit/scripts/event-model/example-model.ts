/**
 * The worked example the canvas tests run over: a parsed `Model` built in memory, so no test touches the
 * real `model.yaml`, the filesystem, a browser or the network.
 *
 * Not a `*.test.ts` on purpose — importing one runs its tests — and shared by both test files so the
 * planner and the serialiser are exercised on the same shape. Every kind of box, every pattern, a lane per
 * grouping source, a read that is a neighbour, reads that are far enough to detour, two trunks that
 * overlap, one reader with several reads, model text that would close a tag, and a line of data long
 * enough to truncate: each of these is here because a test asks about it.
 *
 * Columns, for the assertions that count them:
 *
 *     S1  0 CheckoutScreen  1 PlaceOrder  2 OrderPlaced
 *     S2  3 OrderSummary    4 OrderPage                              reads OrderPlaced — a neighbour
 *     S3  5 Unpaid  6 ChargeOnPlaced  7 Charge  8 Charged           reads OrderPlaced — detours
 *     S4  9 PaymentSettled  10 OnSettlement  11 MarkPaid  12 OrderPaid
 *     S5  13 OrderHistory   14 HistoryPage                           reads OrderPaid (neighbour), Charged
 *                                                                    and OrderPlaced (both detour)
 */
import { parseModel, type Model } from './model.ts';

/** Longer than any box should show, with the characters an attribute value must not let through. */
export const LONG_DATA =
  'orders: [{ id: 1, total: 41.00, paid: true }, { id: 2, total: 12.50, paid: false }], ' +
  'filter: <b>last 30 days</b> & "everything", sortedBy: placedAt desc, page: 1 of 12, note: keep going ' +
  'until this line is well past the limit a box can show';

/** A fresh parse each time, so a test that mutates its copy cannot leak into another. */
export function exampleModel(): Model {
  return parseModel({
    version: 1,
    render: { lanes: { ui: 'actor', data: 'none', events: 'stream' } },
    slices: [
      {
        id: 'S1',
        name: 'Place an order',
        pattern: 'state-change',
        status: 'implemented',
        actor: 'Guest',
        stream: 'order-{orderId}',
        gwt: 'README.md',
        code: ['README.md'],
        frames: [
          { type: 'ui', name: 'CheckoutScreen', data: 'cart: 2 lines, total: 41.00' },
          { type: 'cmd', name: 'PlaceOrder', data: 'orderId, lines' },
          {
            type: 'evt',
            name: 'OrderPlaced',
            attributes: [
              { name: 'orderId', identifies: 'order' },
              { name: 'total', type: 'money' },
            ],
          },
        ],
      },
      {
        id: 'S2',
        name: 'See the order',
        pattern: 'state-view',
        status: 'modelled',
        actor: 'Guest',
        reads: ['OrderPlaced'],
        frames: [
          { type: 'rmo', name: 'OrderSummary', data: 'orderId, total, status' },
          { type: 'ui', name: 'OrderPage' },
        ],
      },
      {
        id: 'S3',
        name: 'Take payment',
        pattern: 'automation',
        status: 'planned',
        actor: 'PaymentProcessor',
        context: 'billing',
        reads: ['OrderPlaced'],
        materialisation: 'async',
        guard: { by: ['order'], because: 'an order is charged once' },
        frames: [
          { type: 'rmo', name: 'Unpaid', data: 'orders placed and not yet charged' },
          { type: 'pcr', name: 'ChargeOnPlaced' },
          { type: 'cmd', name: 'Charge', data: 'orderId, amount' },
          {
            type: 'evt',
            name: 'Charged',
            attributes: [
              { name: 'orderId', identifies: 'order' },
              { name: 'amount' },
            ],
          },
        ],
      },
      {
        id: 'S4',
        name: 'Record a settlement',
        pattern: 'translation',
        status: 'modelled',
        stream: 'order-{orderId}',
        frames: [
          { type: 'evt', name: 'PaymentSettled', external: true, data: 'reference, amount' },
          { type: 'pcr', name: 'OnSettlement' },
          { type: 'cmd', name: 'MarkPaid', data: 'orderId' },
          { type: 'evt', name: 'OrderPaid', data: 'orderId, paidAt' },
        ],
      },
      {
        id: 'S5',
        name: 'Browse order history',
        pattern: 'state-view',
        status: 'proposed',
        actor: 'Guest',
        // Deliberately unsorted: the caption sorts them.
        reads: ['OrderPaid', 'Charged', 'OrderPlaced'],
        frames: [
          { type: 'rmo', name: 'OrderHistory', data: LONG_DATA },
          { type: 'ui', name: 'HistoryPage' },
        ],
      },
    ],
  });
}

/**
 * A hub: one state-change slice and `readers` state-views all reading its event. Every read but the
 * first is long enough to detour, and all of them leave the same event — so they should share one
 * corridor, not take one each.
 */
export function hubModel(readers: number): Model {
  const first = exampleModel().slices[0];
  /* c8 ignore next -- the example always has a first slice */
  if (first === undefined) throw new Error('the example has no slices');
  return parseModel({
    version: 1,
    slices: [
      first,
      ...Array.from({ length: readers }, (_, index) => ({
        id: `V${String(index + 1)}`,
        name: `View ${String(index + 1)}`,
        pattern: 'state-view',
        status: 'modelled',
        actor: 'Guest',
        reads: ['OrderPlaced'],
        frames: [{ type: 'rmo', name: `View${String(index + 1)}` }],
      })),
    ],
  });
}
