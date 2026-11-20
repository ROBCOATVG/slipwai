PATCH

**A further feature is drawn, modelled and split before it is built, and a launch no longer skips all
three.** In a project that had finished a feature, **Continue the build** on the next one exited in a second
and said the fleet was cast off: every stage above the chart asked whether the *project* had a model, a chart
and a storyboard, the first feature answered yes, and the fleet started on a chart with nothing left in it.
**Draw the storyboard** drew the finished feature, **Model** was never offered, and the stage strip read
done. Each stage now asks about the feature in hand, the one `.specify/feature.json` names. A slice in
`docs/event-model/model.yaml` may say which feature it belongs to (`feature: <its directory under specs/>`),
`make chart` carries that into the chart, and a slice that says nothing belongs to the feature the chart is
written under, so a project with one feature reads as it did. The model step for a further feature adds its
slices to the model and leaves the ones already there alone. Still one chart per project: where a further
feature's slice records and deck logs live is not changed by this (#131).

**Catch-up:** `slipwai migrate` carries `scripts/agents/feature_stages.py`, `launch.py`, `model.py` and
`surfaces.py`, `scripts/event-model/chart.py` and `model.ts`, `commands/launch.md` and the re-rendered
`commands/sail.md`. An existing model and chart need no edit. For a further feature that was launched before
this and built nothing: press **Draw the storyboard** again.
