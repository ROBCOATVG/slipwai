PATCH

**The Voyage's two "Continue the build" buttons no longer share an id.** The strip's button and the one on
the *Made* card were both `id="launch"`, so the poll showed and hid only the first, and the card's could
stay on the page after the build had been continued.

**Catch-up:** nothing; the board is served from the installed command.
