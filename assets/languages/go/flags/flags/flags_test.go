package flags

import (
	"maps"
	"testing"
)

func TestVariableSpellsAFlagTheWayTheStackDoes(t *testing.T) {
	// The same transform as `FLAG_${upper(replace(flag.key, "-", "_"))}` in infra/service/flags.tf, which
	// is what puts the value in this container's environment at start-up. If this expectation changes the
	// flag stops arriving — and an absent flag reads as off, so nothing fails loudly to say so.
	for key, want := range map[string]string{
		"checkout-v2":   "FLAG_CHECKOUT_V2",
		"publish-table": "FLAG_PUBLISH_TABLE",
	} {
		if got := Variable(key); got != want {
			t.Fatalf("Variable(%q) = %q, want %q", key, got, want)
		}
	}
}

func TestKeyIsTheExactInverseOfVariable(t *testing.T) {
	// Exact only because check-flags.py holds a key to [a-z0-9][a-z0-9-]*: no underscore can be in a key,
	// so every underscore in the variable came from a dash.
	for _, key := range []string{"checkout-v2", "publish-table", "a", "b2b-invoicing-v10"} {
		got, ok := Key(Variable(key))
		if !ok || got != key {
			t.Fatalf("Key(Variable(%q)) = %q, %v; want %q, true", key, got, ok, key)
		}
	}
}

func TestAVariableThatIsNotAFlagHasNoKey(t *testing.T) {
	// The browser's spelling of the same flag is a flag, but it is not this side's — the prefix anchor is
	// what keeps the two apart, here and in check-flags.py's read pattern.
	for _, variable := range []string{"DATABASE_URL", "PGSSLMODE", "VITE_FLAG_CHECKOUT_V2"} {
		if got, ok := Key(variable); ok {
			t.Fatalf("Key(%q) = %q, true; want not a flag", variable, got)
		}
	}
}

func TestAnEnvironmentSourceReadsAKeyUnderTheNameTheStackGivesIt(t *testing.T) {
	// The transform is the environment's business and nobody else's: this is the only source that knows a
	// flag is carried under a different name than the one it is declared with.
	if got := EnvironmentSource(map[string]string{"FLAG_CHECKOUT_V2": "on"}).Value("checkout-v2"); got != "on" {
		t.Fatalf("environment source answered %q, want %q", got, "on")
	}
	if got := EnvironmentSource(map[string]string{}).Value("checkout-v2"); got != "" {
		t.Fatalf("a variable the environment does not carry answered %q, want empty", got)
	}
}

func TestAnEnvironmentSourceSnapshotsEveryFlagAndNothingThatIsNotOne(t *testing.T) {
	// What the service serves to the browser app, which cannot read these itself. The database URL is in
	// the same environment and is not a flag; VITE_FLAG_… is a flag and is not this side's.
	source := EnvironmentSource(map[string]string{
		"FLAG_CHECKOUT_V2":      "on",
		"FLAG_PUBLISH_TABLE":    "off",
		"DATABASE_URL":          "postgres://nope",
		"VITE_FLAG_CHECKOUT_V2": "on",
	})
	want := map[string]string{"checkout-v2": "on", "publish-table": "off"}
	if got := source.Snapshot(); !maps.Equal(got, want) {
		t.Fatalf("Snapshot() = %v, want %v", got, want)
	}
}

func TestAFixedSourceIsKeyedByTheFlagKey(t *testing.T) {
	// So a test never spells a variable name.
	if got := FixedSource(map[string]string{"checkout-v2": "on"}).Value("checkout-v2"); got != "on" {
		t.Fatalf("fixed source answered %q, want %q", got, "on")
	}
	if got := FixedSource(map[string]string{}).Value("checkout-v2"); got != "" {
		t.Fatalf("a key the source does not carry answered %q, want empty", got)
	}
	want := map[string]string{"checkout-v2": "on"}
	if got := FixedSource(map[string]string{"checkout-v2": "on"}).Snapshot(); !maps.Equal(got, want) {
		t.Fatalf("Snapshot() = %v, want %v", got, want)
	}
}

func TestTheDefaultSourceIsTheTransportThisServiceHas(t *testing.T) {
	// Where a flag comes from is this one function, and a change of transport is a change to it alone.
	// Asked for a key no project would declare, so that somebody who has exported a real flag to try a
	// feature locally does not fail this suite by doing so.
	if got := DefaultSource().Value("no-flag-sets-this"); got != "" {
		t.Fatalf("the default source answered %q for an undeclared key, want empty", got)
	}
}

func TestTheProcessEnvironmentSnapshotReadsRealVariables(t *testing.T) {
	// Snapshot over os.Environ() rather than over a map, which is a different code path: it has to split
	// each entry and keep only the flags.
	t.Setenv("FLAG_SNAPSHOT_PROBE", "on")
	snapshot := ProcessEnvironment().Snapshot()
	if snapshot["snapshot-probe"] != "on" {
		t.Fatalf("Snapshot() = %v, want it to carry snapshot-probe=on", snapshot)
	}
	if _, carried := snapshot["path"]; carried {
		t.Fatal("Snapshot() should carry no variable that is not a flag")
	}
}

func TestAFlagIsOnOnlyForTheValueMakeFlagWrites(t *testing.T) {
	if !EnabledIn("checkout-v2", FixedSource(map[string]string{"checkout-v2": "on"})) {
		t.Fatal("on should be on")
	}
	if EnabledIn("checkout-v2", FixedSource(map[string]string{"checkout-v2": "off"})) {
		t.Fatal("off should be off")
	}
}

func TestAFlagNothingSetIsOff(t *testing.T) {
	// The window between merging code that reads a flag and the apply that creates its parameter: the
	// feature is quietly off rather than the task failing to start.
	if EnabledIn("checkout-v2", FixedSource(map[string]string{})) {
		t.Fatal("an undeclared flag should be off")
	}
	// The process's own environment, asked for a key no project would declare — so that somebody who has
	// exported a real flag to try a feature locally does not fail this suite by doing so.
	if Enabled("no-flag-sets-this") {
		t.Fatal("a flag this process's environment does not carry should be off")
	}
}

func TestAValueTheReaderDoesNotUnderstandIsOff(t *testing.T) {
	// What a shell, a tfvars file or a hand-run `aws ssm put-parameter` would let somebody write. None of
	// them is the spelling, so all of them are off: a flag whose value is not understood hides the feature
	// it gates rather than half-revealing one.
	for _, value := range []string{"true", "1", "ON", "yes"} {
		if EnabledIn("checkout-v2", FixedSource(map[string]string{"checkout-v2": value})) {
			t.Fatalf("%q should be off", value)
		}
	}
}

func TestAFlagReadsThroughWhicheverSourceItIsGiven(t *testing.T) {
	// The two implementations meeting at one call: same key, same answer, different transport.
	if !EnabledIn("checkout-v2", EnvironmentSource(map[string]string{"FLAG_CHECKOUT_V2": "on"})) {
		t.Fatal("an environment source should read the same flag")
	}
	if EnabledIn("checkout-v2", EnvironmentSource(map[string]string{})) {
		t.Fatal("an empty environment should be off")
	}
}
