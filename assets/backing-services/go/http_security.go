package http

import "net/http"

// SecurityHeaders is what a browser is told to enforce on every response, whatever the route.
//
// Written out rather than taken from a package: these four headers are four strings, and the one
// dependency that would supply them would also supply thirty settings this project has not decided.
// Nosniff is the one that matters most for a JSON API — without it a browser may decide a response is
// HTML because of what is inside it, and runs what it finds. The rest are cheap insurance that matters the
// day a route starts returning HTML: an error page, a hosted callback, a rendered receipt. Turning them on
// later is a change nobody remembers to make.
//
// HSTS is deliberately absent. It is a promise about a domain that a browser then refuses to let anybody
// take back for as long as it was given for, and a starter cannot know whether this service owns its
// domain or shares one. Add it where the deployment is known.
var SecurityHeaders = map[string]string{
	"X-Content-Type-Options":  "nosniff",
	"X-Frame-Options":         "DENY",
	"Referrer-Policy":         "no-referrer",
	"Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

// Secure wraps a handler in the two things a browser meets before any route does: the headers above, and
// the answer to whether this origin may ask at all.
//
// Applied in cmd/serve rather than inside BuildApp, for the reason the tracing wrapper is: it is the
// process that is exposed, and the handler a test drives with httptest is the routes and nothing else.
// Its own tests below drive this wrapper directly.
func Secure(next http.Handler, allowedOrigins []string) http.Handler {
	return securityHeaders(cors(next, allowedOrigins))
}

func securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		header := w.Header()
		for name, value := range SecurityHeaders {
			header.Set(name, value)
		}
		next.ServeHTTP(w, r)
	})
}

// cors answers whether this origin may read this service's replies, and nothing more generous than that.
//
// Hand-written and eighteen lines, because that is the whole of what CORS asks of a server: echo the
// origin when it is one you allow, say so varies by origin, and answer a preflight before any route runs.
// A dependency here would buy a configuration language for a decision that is one list.
//
// Empty is the default and means no CORS headers are sent to anybody, which is same-origin only. That is
// the right answer for `make dev` and `make demo`: the browser app is served from its own origin and the
// dev server forwards /api here, so nothing is cross-origin and nothing needs permitting.
//
// CORS_ALLOWED_ORIGINS names the exact origins that may. There is deliberately no `*`: a wildcard and
// credentials cannot be combined at all, and a wildcard without them still hands every page on the
// internet a reader for whatever this service answers unauthenticated. An origin this service does not
// recognise gets a reply with no Access-Control-Allow-Origin header, and the browser refuses it — which is
// the enforcement, since CORS is a rule browsers apply and not one this process can apply on their behalf.
//
// Vary: Origin is set whether or not the origin was allowed, and that is not optional: without it a shared
// cache can serve the permitted origin's response — headers and all — to a request from another one.
func cors(next http.Handler, allowedOrigins []string) http.Handler {
	allowed := make(map[string]bool, len(allowedOrigins))
	for _, origin := range allowedOrigins {
		allowed[origin] = true
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if origin != "" {
			w.Header().Add("Vary", "Origin")
		}
		if origin != "" && allowed[origin] {
			header := w.Header()
			header.Set("Access-Control-Allow-Origin", origin)
			header.Set("Access-Control-Allow-Credentials", "true")
			if r.Method == http.MethodOptions && r.Header.Get("Access-Control-Request-Method") != "" {
				// A preflight is answered here and never reaches the mux: it names a method and headers
				// the browser is *asking* about, and the routes have nothing to say about a question
				// that is not yet a request.
				header.Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
				header.Set("Access-Control-Allow-Headers", requestedHeaders(r))
				header.Set("Access-Control-Max-Age", "600")
				w.WriteHeader(http.StatusNoContent)
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

// requestedHeaders echoes what the preflight asked to send, or the one header every JSON caller needs.
func requestedHeaders(r *http.Request) string {
	if asked := r.Header.Get("Access-Control-Request-Headers"); asked != "" {
		return asked
	}
	return "content-type"
}
