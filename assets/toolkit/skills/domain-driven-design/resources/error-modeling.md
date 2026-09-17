# Error Modeling

How to represent and propagate errors across architectural layers.

## The Default: Discriminated Union Results

For expected outcomes, return discriminated unions. Domain results contain business decisions such as rule violations; application results may add orchestration outcomes such as not-found. Errors stay explicit data rather than hidden control flow.

{{example: domain-driven-design/discriminated-union-pledge-result}}

**Why not exceptions?** Exceptions are invisible in the type signature. A function that returns `Occasion` but can throw `InsufficientBalanceError` has a hidden return path that the compiler doesn't track. Callers can forget to handle it. A discriminated union makes every outcome explicit — the compiler enforces exhaustive handling.

## When Exceptions Are Appropriate

Exceptions are for truly unexpected errors — things that indicate a bug or an infrastructure failure that no business rule can handle:

- **Programmer mistakes:** accessing a null reference, index out of bounds, type coercion failures
- **Infrastructure failures:** database connection lost, network timeout, disk full
- **Invariant violations:** an entity is constructed in an invalid state (this means the factory function has a bug)

These should crash or propagate up to a top-level error handler. They are not business outcomes — they are defects or outages.

{{example: domain-driven-design/exception-vs-result-type}}

**The test:** Could a user's action legitimately cause this outcome? If yes, it's a result type. If no (it would mean a bug), it's an exception.

## How Errors Propagate Through Layers

```
Domain function    → returns PledgeDecision (business outcomes)
       ↓
Use case           → adds application outcomes such as not-found and decides whether to save
       ↓
Route handler      → translates result.reason to HTTP status code
       ↓
HTTP response      → { error: "contributor-ineligible" } with 422
```

Each layer handles errors at its own level of abstraction:

{{example: domain-driven-design/error-propagation-through-layers}}

**The domain never knows about HTTP.** The route handler never knows about business rules. Each layer translates errors into its own vocabulary.

## Modeling Multiple Error Types

For domains with many possible outcomes, use specific reason strings rather than error classes:

{{example: domain-driven-design/multiple-error-reasons-union}}

The `reason` field is a string literal union — exhaustive switch handling catches missing cases at compile time. No error class hierarchies, no inheritance, no `instanceof` checks.

## What NOT To Do

**Don't use exceptions for business rules:**
{{example: domain-driven-design/wrong-exception-for-business-rule}}

**Don't use generic error types:**
{{example: domain-driven-design/wrong-generic-error-type}}

**Don't catch and re-throw to add context:**
{{example: domain-driven-design/wrong-catch-rethrow-context}}

If infrastructure fails (database down), let it propagate to the top-level handler. The use case doesn't need to know why the database is down.

## Testing Errors

Test error paths through the same use case boundary as success paths:

{{example: domain-driven-design/test-error-funding-closed}}

The test proves both the rejection AND the side-effect absence (nothing saved). This is behavioral testing — not "does the function throw?", but "does the feature behave correctly when the business rule is violated?"
