PATCH

**A Continue the build that failed can be pressed again.** The board remembered pressing it for as long as it
ran, whether `make launch` went through or not, so a failed launch hid the button for good, left no chart for
Cast off the fleet to appear from, and answered a press with "nothing to continue from here: a
specification ... is what the build continues from" — about a project that had one. A launch that exits
non-zero now brings the button back, unless a fleet is running in the project anyway. A launch that went
through is still pressed once only, which is what stops a second fleet.

**The refusal says why.** Pressing Continue the build when it cannot go now names the reason that holds:
the build already being continued, another step running on the board or in the project, nothing modelled
yet on the event-modelling profile, a step that failed, or a feature already charted.

**A model that failed has a Model again button.** On the event-modelling profile, approving the storyboard
starts `make model-next` once and locks the verdict, so a model step that failed — or an approval given while
the board was busy — left only a chip saying to go to the agent. Model again appears while the storyboard is
approved, nothing is modelled and nothing is running, and starts the model step from the board.

**Catch-up:** none. Restart the board, and a launch or a model that failed before shows its button again.
