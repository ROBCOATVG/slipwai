import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Testing Library unmounts after each test only when it can find a global `afterEach`, and this project
// deliberately has none: `vite.config.ts` leaves `test.globals` off, so every test imports `describe`,
// `it` and `expect` by name. So the hook is registered here, explicitly. Without it the second `render`
// in a file mounts beside the first and every `getBy*` fails with "found multiple elements" — a failure
// that reads as a bug in the component and is not one.
afterEach(cleanup);
