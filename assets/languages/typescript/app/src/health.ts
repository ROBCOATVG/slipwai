export type Health = Readonly<{ status: 'ok' }>;

export function health(): Health {
  return { status: 'ok' };
}
