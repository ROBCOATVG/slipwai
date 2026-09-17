/**
 * ⚠️  PLACEHOLDER — this is NOT a working OIDC client.
 *
 * Selecting Keycloak wires the container, the environment variables, and the group-to-role mapping. The
 * protocol flow is deliberately not written here.
 *
 * OIDC is one of the few places where writing it yourself from memory is a bad idea. Before implementing,
 * load `skills/secure-oauth-oidc/SKILL.md` — it covers what this file must get right and what silently
 * breaks if it does not:
 *
 *   - Authorization Code flow with PKCE. Never the implicit grant.
 *   - `state` bound to the session (CSRF) and `nonce` bound to the ID token (replay).
 *   - Full ID-token validation: signature against the issuer's JWKS, `iss`, `aud`, `exp`, `nonce`.
 *   - Exact redirect-URI registration; no wildcards.
 *   - Mix-up defence when more than one issuer is possible.
 *
 * Use a maintained OIDC client library rather than hand-rolling these checks.
 *
 * ── The parity hazard worth knowing about now ────────────────────────────────────────────────────────
 * Group-to-role mapping is where this breaks in the least helpful way: groups that exist in staging but
 * not production produce an authorisation model that passes every test and fails in production. Assert the
 * mapping at startup (see `assertRoleMapping` below) so a misconfigured environment refuses to boot instead
 * of misbehaving under load.
 *
 * ── Roles are yours to name ───────────────────────────────────────────────────────────────────────────
 * Everything below is generic in `Role`, because an authorisation model is a product decision. Declare
 * your own union and the mechanism follows it:
 *
 *     type Role = 'admin' | 'operator' | 'viewer';
 *     const mapping: RoleMapping<Role> = { admin: 'app-admin', operator: 'app-operator', viewer: 'app-viewer' };
 *
 * The three group names in `docker/keycloak/realms/app.json` and in `.env.example` are the local fixture
 * those values are checked against, not a prescription.
 *
 * When the flow is written, read the groups from the claim named by `OIDC_GROUPS_CLAIM` rather than from
 * a literal: Keycloak's group-membership mapper writes `groups`, Cognito writes `cognito:groups`, and the
 * one mapping below serves both.
 */

export type RoleMapping<Role extends string = string> = Readonly<Record<Role, string>>;

export type Principal<Role extends string = string> = {
  readonly subject: string;
  readonly roles: readonly Role[];
};

/**
 * Assert every configured group is present, at startup. Called by the composition root.
 * Fails loudly rather than granting nothing silently.
 */
export function assertRoleMapping<Role extends string>(mapping: RoleMapping<Role>): void {
  const missing = (Object.keys(mapping) as Role[]).filter((role) => {
    // Annotated, not inferred: the type says every role has a group, and the whole point of this
    // function is that a mapping assembled from environment variables at runtime may not.
    const group: string | undefined = mapping[role];
    return group === undefined || group.trim().length === 0;
  });
  if (missing.length > 0) {
    throw new Error(
      `OIDC group mapping incomplete for: ${missing.join(', ')}. ` +
        'A missing group grants nothing and looks identical to a permissions bug at runtime.',
    );
  }
}

/** Map provider group claims to application roles. Pure, so it is testable without a provider. */
export function resolveRoles<Role extends string>(
  groupClaims: readonly string[],
  mapping: RoleMapping<Role>,
): readonly Role[] {
  // Keycloak's group-membership mapper emits `/app-admin` when `full.path` is true and `app-admin` when
  // it is false. Accepting both means a realm exported with the other setting does not silently grant
  // nobody anything.
  const claims = new Set(groupClaims.map((claim) => claim.replace(/^\//, '')));
  return (Object.keys(mapping) as Role[]).filter((role) => claims.has(mapping[role]));
}

export function notImplemented(): never {
  throw new Error(
    'OIDC flow not implemented. See the guidance at the top of this file and the secure-oauth-oidc skill.',
  );
}
