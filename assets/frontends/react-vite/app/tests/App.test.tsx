import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { App } from '../src/App';

/** The shell, rendered the way `main.tsx` renders it: inside a router, and nothing else. */
function renderApp() {
  return render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
}

describe('App', () => {
  it('paints the shell before anything has been fetched', () => {
    renderApp();

    // The header and the footer are there on the first frame. That is the whole point of not awaiting
    // anything before `createRoot`: a slow service is a page that says it is loading, not a blank tab.
    expect(screen.getByRole('banner')).toBeVisible();
    expect(screen.getByRole('heading', { level: 1 })).toBeVisible();
    expect(screen.getByRole('contentinfo')).toBeVisible();
    // And the routed content says what it is waiting for rather than rendering a screen it is about to
    // change its mind about. Read synchronously, on the first frame: the flags arrive a microtask later
    // here, and the whole claim is that this is what was painted before they did.
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
  });

  // backing-service:__TRANSPORT__:begin
  it('shows the route once this bundle has been handed its flags', async () => {
    renderApp();

    expect(await screen.findByRole('heading', { name: 'Ready' })).toBeVisible();
  });
  // backing-service:__TRANSPORT__:end
});
