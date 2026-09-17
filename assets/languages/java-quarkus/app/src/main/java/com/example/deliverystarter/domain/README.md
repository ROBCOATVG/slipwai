# The domain layer

The model and nothing else: entities, value objects, domain event types, and the decision methods that
turn a command and a fold of past events into new events or a refusal. This is the part of the service
that survives replacing the transport, the store and the framework, so it is the part that names none of
them.

This package ships empty because the model is yours to write; the layer exists from day one so that the
first thing written into it lands in the right place and the gate already guards it.

**What belongs here.** Records, sealed interfaces, enums and plain classes. No I/O, no `Instant.now()`,
no `Random`: a decision that needs the time or an id takes it as an argument, which is what lets its test
be a table of inputs and expected events.

**What it may not import**, enforced by `make check-imports`:

- anything under `adapters.`, `infrastructure.` or `delivery.` — those import the domain, never the
  reverse;
- any framework or driver package: `io.quarkus.`, `io.smallrye.`, `jakarta.`, `javax.`, `java.sql.`,
  `org.eclipse.microprofile.`, `org.hibernate.`, `org.flywaydb.`,
  `com.fasterxml.jackson.`. The rest of the JDK — `java.util`,
  `java.time`, `java.math` — is the language, not a framework, and is fine here.

The port interfaces a decision is driven through live in `..application.ports`.
