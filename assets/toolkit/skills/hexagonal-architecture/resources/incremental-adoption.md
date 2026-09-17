# Incremental Adoption

How to introduce hexagonal architecture into an existing codebase. You don't need to rewrite everything — extract boundaries incrementally.

## The Strangler Fig Approach

Don't refactor the entire app at once. Wrap new boundaries around existing code, then migrate logic inward over time.

### Step 1: Identify the First Boundary

Pick a feature where business logic is tangled with infrastructure — typically a route handler that queries the database, applies business rules, and sends a response all in one function.

{{example: hexagonal-architecture/incremental-before-tangled-handler}}

### Step 2: Extract the Domain Function

Pull the business rule into a pure function. No infrastructure, no async.

{{example: hexagonal-architecture/incremental-extract-domain-function}}

### Step 3: Extract the Port Interface

Define the external conversation that application policy needs. Keep the contract inside and express it in domain language.

{{example: hexagonal-architecture/incremental-extract-port-interface}}

### Step 4: Create the Adapter

Wrap the existing database access behind the port interface.

{{example: hexagonal-architecture/incremental-create-adapter}}

### Step 5: Create the Use Case

Wire the domain function to the port.

{{example: hexagonal-architecture/incremental-create-use-case}}

### Step 6: Thin Out the Executable Entry Point

{{example: hexagonal-architecture/incremental-after-thin-entrypoint}}

Inline construction is valid here only when the framework makes this handler the executable deployment entrypoint and the graph remains trivial and unshared. In a conventional or shared host, move database, repository, and use-case construction to `main.ts` or `composition/`; inject the prepared `ForDeductingUserBalances` into an ordinary route adapter.

## What to Migrate First

| Signal | Priority |
|--------|----------|
| Business logic in route handlers | High — extract domain functions |
| Direct DB queries in multiple places | High — extract repository port |
| Untestable code (needs real DB to test) | High — extract port + create fake |
| Simple CRUD with no business rules | Low — hex arch adds overhead without benefit |
| Stable code that rarely changes | Low — migration risk exceeds benefit |

## What NOT to Do

- **Don't create a complete repository-root `hexagon/` skeleton and migrate everything at once.** Use `structure-codebase` to establish one capability's first honest inside/outside slice, write tests, verify it, then move to the next.
- **Don't introduce ports for things that don't need them.** A simple config lookup doesn't need a `ConfigPort` interface.
- **Don't force hex arch on CRUD endpoints.** If a route handler just reads from a database and returns JSON with no business logic, leave it alone.
- **Don't create abstract base classes** (`BaseRepository<T>`). Each port is specific to its aggregate.

## The Test is the Proof

After each extraction, you should be able to write a use case test with fakes that proves the feature works — without touching the database. If you can, the boundary is correct. If you can't, something is still tangled.
