package http_test

import (
	"os"
	"regexp"
	"strings"
	"testing"
)

// The published contract and the routes that serve it, held together.
//
// openapi.yaml is hand-written on this backend — there is no generator, and buying one would cost the
// dependency this backend exists without. What keeps a hand-written document honest is this: a route the
// mux serves and the document does not describe fails `make verify`, in the same run that added it.
//
// Read out of the source rather than out of the mux, because net/http's ServeMux does not say what it
// holds: there is no Routes() to ask. The pattern below is the one spelling BuildApp uses, so a route
// registered any other way is a route this test cannot see — which is the reason the count is asserted
// too.
var registration = regexp.MustCompile(`mux\.HandleFunc\("([A-Z]+) ([^"]+)"`)

func TestEveryRouteIsInThePublishedDocument(t *testing.T) {
	source, err := os.ReadFile("app.go")
	if err != nil {
		t.Fatalf("the adapter's own source: %v", err)
	}
	// From adapters/driving/http up to the service directory, where the contract sits beside go.mod.
	document, err := os.ReadFile("../../../openapi.yaml")
	if err != nil {
		t.Fatalf("the published contract: %v", err)
	}

	routes := registration.FindAllStringSubmatch(string(source), -1)
	if len(routes) < 2 {
		t.Fatalf("found %d routes in app.go; the pattern this test reads them with has gone stale", len(routes))
	}
	for _, route := range routes {
		method, path := strings.ToLower(route[1]), route[2]
		if !strings.Contains(string(document), "\n  "+path+":\n") {
			t.Errorf("%s %s is served and openapi.yaml does not describe it", route[1], path)
			continue
		}
		if !strings.Contains(string(document), "\n    "+method+":\n") {
			t.Errorf("openapi.yaml describes no %s operation, and %s %s is served", method, route[1], path)
		}
	}
}
