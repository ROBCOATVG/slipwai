MINOR

**An adopted repository is given a playbook for each change strategy.** `docs/strategies/` holds one per
strategy — leave it, in place, strangler fig, rewrite — saying what the decided one means for every step after it:
where a new feature is built, what the specification and the mock-ups show, what the gate refuses and the order of
the work. Beside them are the build floor every strategy starts with, and the target shape the system is moving
towards. `docs/change-strategy.md` now chooses between four strategies rather than three, and separates how traffic
moves from how much of the system moves.
