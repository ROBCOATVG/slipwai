package config_test

import (
	"strconv"
	"strings"
	"testing"

	"example.com/delivery-starter/config"
)

// environment is a hand-written stand-in for os.LookupEnv: the values this run was given, and nothing
// else. A fake rather than a framework, and a map rather than t.Setenv, so a case can describe an
// environment without the process having one.
func environment(values map[string]string) config.Lookup {
	return func(name string) (string, bool) {
		value, ok := values[name]
		return value, ok
	}
}

func TestCarriesTheDefaultsTheEnvironmentTemplateWritesDown(t *testing.T) {
	loaded, err := config.LoadFrom(environment(nil))
	if err != nil {
		t.Fatalf("an empty environment was refused: %v", err)
	}

	if loaded.Port != 3000 || loaded.Host != "0.0.0.0" {
		t.Fatalf("config is %+v", loaded)
	}
	if loaded.Address() != "0.0.0.0:3000" {
		t.Fatalf("address is %q", loaded.Address())
	}
	// Nothing to report but the port it bound, so that is what it reports.
	if loaded.ReportedURL() != "http://localhost:3000" {
		t.Fatalf("reported URL is %q", loaded.ReportedURL())
	}
}

// The point of checking the environment at start-up rather than at the point of use: the process that
// cannot work refuses to start, and says which variable is why.
func TestRefusesAPortItCannotUseAndNamesIt(t *testing.T) {
	for _, port := range []string{"the-usual-one", "0", "70000", "-1"} {
		if _, err := config.LoadFrom(environment(map[string]string{"PORT": port})); err == nil {
			t.Errorf("PORT=%q was accepted", port)
		} else if !strings.Contains(err.Error(), "PORT") {
			t.Errorf("PORT=%q was refused without naming the variable: %v", port, err)
		}
	}
}

// The valid range is 1-65535 inclusive at both ends: TestRefusesAPortItCannotUseAndNamesIt only
// exercises values outside it, which leaves 1 and 65535 themselves unproven as accepted.
func TestAcceptsAPortAtEitherEndOfTheValidRange(t *testing.T) {
	for _, port := range []string{"1", "65535"} {
		loaded, err := config.LoadFrom(environment(map[string]string{"PORT": port}))
		if err != nil {
			t.Errorf("PORT=%q was refused: %v", port, err)
		} else if got := strconv.Itoa(loaded.Port); got != port {
			t.Errorf("PORT=%q loaded as %q", port, got)
		}
	}
}

func TestRefusesAnAddressThatIsNotOne(t *testing.T) {
	_, err := config.LoadFrom(environment(map[string]string{"PUBLIC_BASE_URL": "service.internal:3000"}))

	if err == nil {
		t.Fatalf("an address that is not one was accepted")
	}
	if !strings.Contains(err.Error(), "PUBLIC_BASE_URL") {
		t.Fatalf("refused without naming the variable: %v", err)
	}
}

func TestReportsTheAddressSomebodyCanOpen(t *testing.T) {
	// Behind a proxy or a tunnel the bound port and the public address differ, and the one worth
	// logging is the one that can be opened.
	loaded, err := config.LoadFrom(environment(map[string]string{
		"PORT":            "8080",
		"PUBLIC_BASE_URL": "https://service.example.com",
	}))
	if err != nil {
		t.Fatalf("refused: %v", err)
	}

	if loaded.ReportedURL() != "https://service.example.com" {
		t.Fatalf("reported URL is %q", loaded.ReportedURL())
	}
}

func TestAnEmptyVariableIsAnUnsetOne(t *testing.T) {
	// A Compose file or a task definition that declares a variable it has no value for hands the
	// process an empty string, which is not an answer — it is the absence of one.
	loaded, err := config.LoadFrom(environment(map[string]string{"HOST": "", "PORT": ""}))
	if err != nil {
		t.Fatalf("refused: %v", err)
	}

	if loaded.Host != "0.0.0.0" || loaded.Port != 3000 {
		t.Fatalf("config is %+v", loaded)
	}
}

func TestAnAllowListIsReadTheWayADeploymentWritesOne(t *testing.T) {
	loaded, err := config.LoadFrom(environment(map[string]string{
		"CORS_ALLOWED_ORIGINS": "http://a.example, http://b.example,",
	}))
	if err != nil {
		t.Fatalf("refused: %v", err)
	}

	// A trailing comma must not become a permission for the empty string, which is what an Origin
	// header carries when a request has none.
	if len(loaded.CORSAllowedOrigins) != 2 ||
		loaded.CORSAllowedOrigins[0] != "http://a.example" ||
		loaded.CORSAllowedOrigins[1] != "http://b.example" {
		t.Fatalf("an allow-list was read as %v", loaded.CORSAllowedOrigins)
	}
}

func TestNoOriginIsAllowedUntilOneIsNamed(t *testing.T) {
	// Empty is the default, and it is same-origin only.
	loaded, err := config.LoadFrom(environment(map[string]string{}))
	if err != nil {
		t.Fatalf("refused: %v", err)
	}

	if len(loaded.CORSAllowedOrigins) != 0 {
		t.Fatalf("nothing was named and %v came back", loaded.CORSAllowedOrigins)
	}
	// And nothing is exported until somewhere was named to export to.
	if loaded.OTelExporterOTLPEndpoint != "" {
		t.Fatalf("an exporter endpoint appeared from nowhere: %q", loaded.OTelExporterOTLPEndpoint)
	}
}

func TestAnExporterEndpointThatIsNotAnAddressStopsTheProcess(t *testing.T) {
	// A wrong endpoint is not a slower service: it is telemetry going nowhere with nothing to say so,
	// which is exactly the kind of failure this package exists to turn into a refusal to start.
	_, err := config.LoadFrom(environment(map[string]string{
		"OTEL_EXPORTER_OTLP_ENDPOINT": "collector:4318",
	}))

	if err == nil {
		t.Fatal("an endpoint that is not an address was accepted")
	}
	if !strings.Contains(err.Error(), "OTEL_EXPORTER_OTLP_ENDPOINT") {
		t.Fatalf("the refusal does not name the variable: %v", err)
	}
}
