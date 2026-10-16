PATCH

**After a migration, the crossing report asks for the one chart `make chart` writes.** That command writes
a single `chart.yaml`, into the first feature directory that holds a slice record, and the chart covers
the whole model. The report used to owe a chart for every feature directory, which no project with more
than one feature can satisfy, and the command it named will never write those files. It now asks whether
the feature in flight has its chart.

**Catch-up:** nothing. Run `python3 scripts/check-crossing.py` again; a feature other than the one in
flight no longer owes a chart.
