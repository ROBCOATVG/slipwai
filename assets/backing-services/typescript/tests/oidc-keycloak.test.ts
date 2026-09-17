import { describe, expect, it } from 'vitest';

import {
  assertRoleMapping,
  notImplemented,
  type RoleMapping,
  resolveRoles,
} from '../../src/adapters/driving/http/auth/oidc-keycloak.js';

type Role = 'admin' | 'operator' | 'viewer';

const mapping: RoleMapping<Role> = {
  admin: 'app-admin',
  operator: 'app-operator',
  viewer: 'app-viewer',
};

describe('group-to-role mapping', () => {
  it('grants only the roles whose groups the token carries', () => {
    expect(resolveRoles(['app-admin', 'app-viewer'], mapping)).toEqual(['admin', 'viewer']);
  });

  it('accepts a full-path group claim, because a realm may be exported either way', () => {
    expect(resolveRoles(['/app-operator'], mapping)).toEqual(['operator']);
  });

  it('grants nothing for a group that maps to no role', () => {
    expect(resolveRoles(['some-other-group'], mapping)).toEqual([]);
  });

  it('refuses to boot on an incomplete mapping rather than granting nothing silently', () => {
    expect(() => assertRoleMapping({ ...mapping, operator: '   ' })).toThrow(
      /incomplete for: operator/,
    );
  });

  it('accepts a complete mapping', () => {
    expect(() => assertRoleMapping(mapping)).not.toThrow();
  });
});

describe('the flow itself', () => {
  it('is a placeholder that refuses to pretend otherwise', () => {
    expect(() => notImplemented()).toThrow(/not implemented/);
  });
});
