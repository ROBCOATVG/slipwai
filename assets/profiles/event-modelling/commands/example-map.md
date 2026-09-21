---
description: Turn one event-model slice into concrete rules, examples, and executable scenarios
argument-hint: [slice-id]
---

# Example map

Read the slice in `docs/event-model/model.yaml` and use `skills/event-modeling/SKILL.md`. Work with four
items: story, rules, concrete examples, and unresolved questions. Do not invent an event, field, command,
stream identity, or policy to close a product question. Write the agreed Given/When/Then scenarios and link
their path from the slice's `gwt` field. Preserve the Event Modeling/event-sourcing contract as one unit.

## Rules own their examples

Write the map as numbered rules, `R1`…`Rn`, each heading carrying its own examples and their scenarios —
not every rule in one section and every scenario in another. The rule is the unit of a RED-GREEN-REFACTOR
increment (Principle V), so the grouping here is the boundary the tasks are cut on and the verdicts cite:
without a stated grouping there is no agreed rule boundary, and whoever writes the tasks invents one.

```markdown
## Story
Buyer places an order for the items in their cart and gets a confirmation.

## R1 — An order cannot be placed from an empty cart
- empty cart → rejected, nothing recorded

### Scenario: Cannot place order with empty cart (CS-1)
**Given** CartCreated { cartId: "CART-001" } · **When** PlaceOrder { cartId: "CART-001" } ·
**Then** error "cart CART-001 contains no items", no events

## R2 — The order total is the sum of the cart's line totals at the moment it is placed
- 2 x £29.99 → order total £59.98, and later price changes do not move it

### Scenario: Successfully place an order (CS-2)
…

## Questions
- Does a cart expire, and if so does expiry reject or silently empty it? → for the product owner
```

Never renumber a rule once a task or a verdict cites it: a new rule takes the next number, and a dropped one
keeps its number with a line saying it was dropped and why. Do not retrofit this shape onto a map that is
already agreed and implemented — the format applies from the next slice mapped, and an older map is read
as it stands.
