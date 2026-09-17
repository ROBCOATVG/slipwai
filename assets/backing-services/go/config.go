// Package config holds this process's configuration: one struct over the environment, read and checked
// before anything binds.
//
// Twelve-factor says configuration comes from the environment, which is a decision about where it comes
// from and says nothing about when it is read. Read at the point of use, a missing or misspelt value is
// discovered by the first request that needs it — in production, by a customer, as a 500 naming something
// the operator never set. Read here, it is discovered by the process that will not start, and the error
// names the variable.
//
// The standard library and nothing else: os.LookupEnv and strconv are the whole of what parsing an
// environment needs, and a configuration library would be this service's first dependency spent on
// reading five variables.
//
// It is a package rather than a block inside cmd/serve for one reason: cmd/serve is deliberately the only
// package in the service with no test, because everything it does is composition. Checking the
// environment is not composition — it is a rule, with values that pass and values that do not — so it
// lives where a test can drive it.
//
// LOG_LEVEL and LOG_FORMAT are deliberately not checked. A typo in a log variable must never be the thing
// that stops a deployment; cmd/serve falls back to info and to JSON, and that is the right answer there.
// OTEL_EXPORTER_OTLP_ENDPOINT is checked, because it is an address: a wrong one is not a slower service,
// it is telemetry going nowhere with nothing to say so.
package config

import (
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
)

// Config is the environment this process was given, as the service is allowed to read it.
type Config struct {
	// Host defaults to 0.0.0.0 rather than to localhost because this process runs inside a container as
	// often as beside you, and a server bound to 127.0.0.1 in a container is reachable from nothing: the
	// published port answers, the connection is refused, and nothing in the logs says why.
	Host string
	Port int
	// PublicBaseURL is the address callers reach this service on, which is not derivable from Port —
	// behind a proxy or a tunnel they differ. Empty is fine and cmd/serve falls back to the bound port;
	// what is refused is a value that is not an address, because that one gets printed and pasted.
	PublicBaseURL string
	LogLevel      string
	LogFormat     string
	// OTelServiceName is what this service calls itself in a trace, defaulted to its own name: a
	// service exporting spans as `unknown_service` is one nobody can find again.
	OTelServiceName string
	// OTelExporterOTLPEndpoint is where to send them, and the one thing that decides whether anything
	// is sent at all (package observability). Empty is the default and means spans are recorded and
	// dropped; a value that is not an address is refused here rather than surfacing as an exporter
	// that silently never connects.
	OTelExporterOTLPEndpoint string
	// CORSAllowedOrigins is which browser origins may call this service cross-origin. Empty — the
	// default — is same-origin only: no CORS headers are sent to anybody. A wildcard is deliberately
	// not a value this accepts; adapters/driving/http/security.go says why an allow-list is spelled out.
	CORSAllowedOrigins []string
	// backing-service:sqlite:begin
	// Where the event log lives. A path, not a URL: SQLite is a file this process opens, with no server
	// to address. cmd/serve opens the store from this and from nothing else.
	EventStorePath string
	// backing-service:sqlite:end
	// backing-service:postgres:begin
	// The event store's DSN, which cmd/serve opens the store from. Empty is not refused here — a service
	// that cannot reach its store reports /ready as 503 rather than failing to start — but a value that
	// is not a Postgres URL is, because that one is a typo nothing else will ever tell anybody about.
	DatabaseURL string
	// backing-service:postgres:end
}

// Lookup is os.LookupEnv's shape, so a test can hand this package an environment rather than set one.
type Lookup func(name string) (string, bool)

// Load reads and checks this process's own environment.
func Load() (Config, error) { return LoadFrom(os.LookupEnv) }

// LoadFrom reads and checks an environment, or refuses it with the variable named.
func LoadFrom(lookup Lookup) (Config, error) {
	value := func(name, fallback string) string {
		if found, ok := lookup(name); ok && found != "" {
			return found
		}
		return fallback
	}

	config := Config{
		Host:                     value("HOST", "0.0.0.0"),
		PublicBaseURL:            value("PUBLIC_BASE_URL", ""),
		LogLevel:                 value("LOG_LEVEL", "info"),
		LogFormat:                value("LOG_FORMAT", "json"),
		OTelServiceName:          value("OTEL_SERVICE_NAME", "__SERVICE_NAME__"),
		OTelExporterOTLPEndpoint: value("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
		CORSAllowedOrigins:       splitOrigins(value("CORS_ALLOWED_ORIGINS", "")),
	}

	// backing-service:sqlite:begin
	// Assigned after the literal rather than inside it: a marked region between two fields of a composite
	// literal is a comment gofmt would rather align around than leave where the pruner needs it.
	config.EventStorePath = value("EVENT_STORE_PATH", "./events.sqlite3")
	// backing-service:sqlite:end
	// backing-service:postgres:begin
	config.DatabaseURL = value("DATABASE_URL", "")
	// backing-service:postgres:end
	port, err := strconv.Atoi(value("PORT", "3000"))
	if err != nil || port < 1 || port > 65535 {
		return Config{}, fmt.Errorf("PORT must be a port number between 1 and 65535, not %q", value("PORT", ""))
	}
	config.Port = port

	if config.PublicBaseURL != "" &&
		!strings.HasPrefix(config.PublicBaseURL, "http://") &&
		!strings.HasPrefix(config.PublicBaseURL, "https://") {
		return Config{}, fmt.Errorf(
			"PUBLIC_BASE_URL must begin with http:// or https://, not %q", config.PublicBaseURL,
		)
	}

	if config.OTelExporterOTLPEndpoint != "" &&
		!strings.HasPrefix(config.OTelExporterOTLPEndpoint, "http://") &&
		!strings.HasPrefix(config.OTelExporterOTLPEndpoint, "https://") {
		return Config{}, fmt.Errorf(
			"OTEL_EXPORTER_OTLP_ENDPOINT must begin with http:// or https://, not %q",
			config.OTelExporterOTLPEndpoint,
		)
	}

	// backing-service:postgres:begin
	if config.DatabaseURL != "" &&
		!strings.HasPrefix(config.DatabaseURL, "postgres://") &&
		!strings.HasPrefix(config.DatabaseURL, "postgresql://") {
		return Config{}, fmt.Errorf(
			"DATABASE_URL must begin with postgres:// or postgresql://, not %q", config.DatabaseURL,
		)
	}
	// backing-service:postgres:end
	return config, nil
}

// splitOrigins reads a comma-separated allow-list the way a deployment writes one.
//
// Whitespace around a comma is dropped and an empty entry is not an origin — a trailing comma in a
// deployment's environment must not become a permission for the empty string, which is what an Origin
// header carries when a request has none.
func splitOrigins(raw string) []string {
	origins := []string{}
	for _, origin := range strings.Split(raw, ",") {
		if trimmed := strings.TrimSpace(origin); trimmed != "" {
			origins = append(origins, trimmed)
		}
	}
	return origins
}

// Address is where the server binds, as net.Listen wants it. JoinHostPort rather than concatenation,
// because an IPv6 host has to be bracketed and nothing else in the service would notice it was not.
func (c Config) Address() string { return net.JoinHostPort(c.Host, strconv.Itoa(c.Port)) }

// ReportedURL is the address worth logging: the one somebody can open.
func (c Config) ReportedURL() string {
	if c.PublicBaseURL != "" {
		return c.PublicBaseURL
	}
	return "http://localhost:" + strconv.Itoa(c.Port)
}
