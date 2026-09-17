// Package flags reads this service's feature flags, and is the only place this side reads one.
//
// A flag is what makes merging and releasing two decisions. Every commit that passes `verify` on `main`
// reaches production, so work that is not finished has to arrive there dark: the branch is merged, the
// flag is off, and nobody outside sees it until somebody flips it. .specify/memory/constitution.md
// requires exactly that, and this package is where the requirement stops being prose.
//
// # One flag, one name
//
// A flag is declared once, in infra/service/flags.auto.tfvars, under the service that reads it, with a
// key in one spelling: checkout-v2. Ask by key and the declaration and the code cannot drift apart —
// which is the whole reason a slice calls flags.Enabled("checkout-v2") and never reaches for a variable
// name of its own. A hand-derived variable is a typo waiting to happen, and a typo reads as absent, which
// reads as off: the feature never turns on and the flip merely looks broken.
//
// # Where a value comes from is one value, and it is not this function
//
// A Source answers two questions and no others: what this environment holds for one key, and what it
// holds for all of them. Today there is one implementation and DefaultSource returns it: the stack turns
// each key into an SSM parameter and has ECS resolve it into this container's environment as
// FLAG_CHECKOUT_V2 — upper-cased, dashes to underscores — so ProcessEnvironment applies that transform
// and reads os.Getenv. Variable is the transform and Key is its inverse, both written here and nowhere
// else, and both pinned by a test against the HCL that has to agree with them.
//
// The point of the seam is that it is keyed by the flag's own key rather than by a variable name. A
// transport that is not an environment — an AppConfig agent beside this container, answered over
// loopback, which is what a flag that has to move without a restart needs — is then a second Source and
// a one-line change to DefaultSource, not a change to any call site, any test, or the rule in AGENTS.md
// that points at this package. docs/deployment.md says which of the two this project has and what a flip
// therefore costs.
//
// Snapshot is the second question because something has to answer it: the flags this service holds are
// served to the browser app, which cannot read them itself. It is deliberately a snapshot and not a
// subscription — the values as of the moment it was asked, which is all a transport polling an agent can
// honestly promise.
//
// # Off is the answer to every question this cannot answer
//
// A flag is on only for the exact value "on" — the spelling `make flag` writes and the only one
// flags.auto.tfvars seeds. "off", "true", "1", a value that never arrived: all off. That is the safe
// direction, and it matters most in the window between merging code that reads a flag and the apply that
// creates its parameter. A source reports an absent flag as the empty string, so in that window a task
// starts with the feature quietly off rather than failing to start at all.
//
// # The seam exists so both paths can be tested
//
// A test drives either path by passing a source, which is the whole reason the value is not read at the
// point of use: FixedSource(map[string]string{"checkout-v2": "on"}) for the on path and
// FixedSource(map[string]string{}) for the one production is running while the flag is off. It is keyed
// by key, so a test never has to know how this environment happens to carry a flag. `make check-flags`
// holds every declared flag to having both paths covered, because while a flag is off the branch running
// in production is the one the slice's own tests do not reach — and "it worked before the branch was
// added" is not evidence about the code after it. os.Getenv is called here and in no other package.
//
// Locally there is no parameter store and no flip: the flag is whatever this process's environment says,
// so FLAG_CHECKOUT_V2=on make dev is the whole of it.
package flags

import (
	"os"
	"strings"
)

// On is the only value that turns a flag on. Anything else, or nothing at all, gates its feature shut.
const On = "on"

// prefix is what the stack gives every flag variable, and what Key will answer to.
const prefix = "FLAG_"

// Source is where this service's flags come from.
//
// Keyed by the flag's key and not by an environment variable, so that a transport which is not an
// environment is an implementation of this and nothing more.
type Source interface {
	// Value is this environment's raw value for one flag, or the empty string when it carries none.
	Value(key string) string

	// Snapshot is every flag this source carries, by key, as of now.
	//
	// A snapshot rather than a subscription: a transport that polls an agent can promise the values it
	// last saw and nothing stronger. Only flags with a value appear — an absent flag is off, and saying
	// so by omission is the same answer Value gives.
	Snapshot() map[string]string
}

// Variable is the environment variable a flag's key is read from: checkout-v2 becomes FLAG_CHECKOUT_V2.
func Variable(key string) string {
	return prefix + strings.ToUpper(strings.ReplaceAll(key, "-", "_"))
}

// Key is the key a flag variable came from: FLAG_CHECKOUT_V2 becomes checkout-v2. The second result is
// false for a variable that is not a flag's.
//
// The inverse is exact only because a key may not contain an underscore — check-flags.py holds every
// declared key to [a-z0-9][a-z0-9-]* — so every underscore in the variable came from a dash. It is
// deliberately anchored on the prefix, which is why VITE_FLAG_CHECKOUT_V2, the browser's spelling of the
// same flag, is not a flag variable here.
func Key(variable string) (string, bool) {
	rest, found := strings.CutPrefix(variable, prefix)
	if !found {
		return "", false
	}
	return strings.ToLower(strings.ReplaceAll(rest, "_", "-")), true
}

// processEnvironment reads this process's own environment, which is where ECS puts the parameters.
type processEnvironment struct{}

func (processEnvironment) Value(key string) string {
	return os.Getenv(Variable(key))
}

func (processEnvironment) Snapshot() map[string]string {
	flags := make(map[string]string)
	for _, entry := range os.Environ() {
		variable, value, found := strings.Cut(entry, "=")
		if !found {
			continue
		}
		if key, ok := Key(variable); ok {
			flags[key] = value
		}
	}
	return flags
}

// mapEnvironment reads variables handed to it, under the names infra/service/flags.tf gives them.
type mapEnvironment struct {
	variables map[string]string
}

func (source mapEnvironment) Value(key string) string {
	return source.variables[Variable(key)]
}

func (source mapEnvironment) Snapshot() map[string]string {
	flags := make(map[string]string)
	for variable, value := range source.variables {
		if key, ok := Key(variable); ok {
			flags[key] = value
		}
	}
	return flags
}

// fixed holds flags by key, which is what a test drives both paths with.
type fixed struct {
	values map[string]string
}

func (source fixed) Value(key string) string {
	return source.values[key]
}

func (source fixed) Snapshot() map[string]string {
	flags := make(map[string]string, len(source.values))
	for key, value := range source.values {
		flags[key] = value
	}
	return flags
}

// ProcessEnvironment is a Source over this process's own environment.
//
// The only source that knows a flag is carried under a different name than the one it is declared with:
// the transform is the environment's business and nobody else's.
func ProcessEnvironment() Source {
	return processEnvironment{}
}

// EnvironmentSource is a Source over the given variables. A key the map does not carry is off, exactly
// as an unset variable is.
func EnvironmentSource(environment map[string]string) Source {
	return mapEnvironment{variables: environment}
}

// FixedSource is a Source over flags held by key — the key itself, so a test never spells a variable name.
func FixedSource(values map[string]string) Source {
	return fixed{values: values}
}

// DefaultSource is where this service's flags come from — the one line a change of transport is.
//
// Called per read rather than resolved once into a package variable, so that a source with state of its
// own (a poller holding the last configuration it fetched) can memoize behind this and still be swapped
// in here alone.
func DefaultSource() Source {
	return ProcessEnvironment()
}

// Enabled reports whether the named flag is on, read through this service's own source.
//
// key is the flag's name as infra/service/flags.auto.tfvars declares it, in one spelling.
func Enabled(key string) bool {
	return EnabledIn(key, DefaultSource())
}

// EnabledIn reports whether the named flag is on in the given source, which is what a test drives both
// paths with.
func EnabledIn(key string, source Source) bool {
	return source.Value(key) == On
}
