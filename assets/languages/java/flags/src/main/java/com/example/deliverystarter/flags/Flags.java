package com.example.deliverystarter.flags;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * This service's feature flags, and the only place this side reads one.
 *
 * <p>A flag is what makes merging and releasing two decisions. Every commit that passes {@code verify} on
 * {@code main} reaches production, so work that is not finished has to arrive there dark: the branch is
 * merged, the flag is off, and nobody outside sees it until somebody flips it.
 * {@code .specify/memory/constitution.md} requires exactly that, and this class is where the requirement
 * stops being prose.
 *
 * <h2>One flag, one name</h2>
 *
 * <p>A flag is declared once, in {@code infra/service/flags.auto.tfvars}, under the service that reads it,
 * with a key in one spelling: {@code checkout-v2}. Ask by key and the declaration and the code cannot
 * drift apart — which is the whole reason a slice calls {@code Flags.enabled("checkout-v2")} and never
 * reaches for a variable name of its own. A hand-derived variable is a typo waiting to happen, and a typo
 * reads as <em>absent</em>, which reads as <em>off</em>: the feature never turns on and the flip merely
 * looks broken.
 *
 * <h2>Where a value comes from is one object, and it is not this method</h2>
 *
 * <p>A {@link Source} answers two questions and no others: what this environment holds for one key, and
 * what it holds for all of them. Today there is one implementation and {@link #defaultSource()} returns
 * it: the stack turns each key into an SSM parameter and has ECS resolve it into this container's
 * environment as {@code FLAG_CHECKOUT_V2} — upper-cased, dashes to underscores — so
 * {@link #processEnvironment()} applies that transform and reads {@code System.getenv}.
 * {@link #variable(String)} is the transform and {@link #key(String)} is its inverse, both written here
 * and nowhere else, and both pinned by a test against the HCL that has to agree with them.
 *
 * <p>The point of the seam is that it is keyed by the flag's own key rather than by a variable name. A
 * transport that is not an environment — an AppConfig agent beside this container, answered over
 * loopback, which is what a flag that has to move <em>without</em> a restart needs — is then a second
 * {@code Source} and a one-line change to {@link #defaultSource()}, not a change to any call site, any
 * test, or the rule in {@code AGENTS.md} that points at this class. {@code docs/deployment.md} says which
 * of the two this project has and what a flip therefore costs.
 *
 * <p>{@link Source#snapshot()} is the second question because something has to answer it: the flags this
 * service holds are served to the browser app, which cannot read them itself. It is deliberately a
 * <em>snapshot</em> and not a subscription — the values as of the moment it was asked, which is all a
 * transport polling an agent can honestly promise.
 *
 * <h2>Off is the answer to every question this cannot answer</h2>
 *
 * <p>A flag is on only for the exact value {@code "on"} — the spelling {@code make flag} writes and the
 * only one {@code flags.auto.tfvars} seeds. {@code "off"}, {@code "true"}, {@code "1"}, a value that never
 * arrived: all off. That is the safe direction, and it matters most in the window between merging code
 * that reads a flag and the apply that creates its parameter. A source answers null there, which is why
 * the comparison below is written on the constant rather than on the value: in that window a task starts
 * with the feature quietly off instead of throwing on start-up.
 *
 * <h2>Deliberately not a bean</h2>
 *
 * <p>No {@code @ConfigProperty}, no {@code @Value}, no injection — the same decision as
 * {@code HealthStatus}, for two reasons beyond testability. A framework's configuration would give one
 * flag a second spelling to keep in step with the stack's, and it would bind the value when the bean is
 * created; a flag is read where behaviour branches, which is the point at which the answer should be
 * asked for. Read it in a use case or an adapter, never in the domain: the domain takes decided values as
 * inputs, exactly as it takes the clock.
 *
 * <h2>The seam exists so both paths can be tested</h2>
 *
 * <p>A test drives either path by passing a source, which is the whole reason the value is not read at the
 * point of use: {@code fixedSource(Map.of("checkout-v2", "on"))} for the on path and
 * {@code fixedSource(Map.of())} for the one production is running while the flag is off. It is keyed by
 * key, so a test never has to know how this environment happens to carry a flag.
 * {@code make check-flags} holds every declared flag to having both paths covered, because while a flag is
 * off the branch running in production is the one the slice's own tests do not reach — and "it worked
 * before the branch was added" is not evidence about the code after it.
 *
 * <p>Locally there is no parameter store and no flip: the flag is whatever this process's environment
 * says, so {@code FLAG_CHECKOUT_V2=on make dev} is the whole of it.
 */
public final class Flags {

    /** The only value that turns a flag on. Anything else, or nothing at all, gates its feature shut. */
    public static final String ON = "on";

    /** What the stack gives every flag variable, and what {@link #key(String)} will answer to. */
    private static final String PREFIX = "FLAG_";

    /**
     * Where this service's flags come from.
     *
     * <p>Keyed by the flag's key and not by an environment variable, so that a transport which is not an
     * environment is an implementation of this and nothing more.
     */
    public interface Source {

        /**
         * This environment's raw value for one flag.
         *
         * @param key the flag's name as {@code infra/service/flags.auto.tfvars} declares it
         * @return the value, or null when this environment carries nothing for that key
         */
        @Nullable String value(String key);

        /**
         * Every flag this source carries, by key, as of now.
         *
         * <p>A snapshot rather than a subscription: a transport that polls an agent can promise the values
         * it last saw and nothing stronger. Only flags with a value appear — an absent flag is off, and
         * saying so by omission is the same answer {@link #value(String)} gives.
         *
         * @return the flags, by the key each is declared with
         */
        Map<String, String> snapshot();
    }

    private Flags() {
        // Static reads only; there is no per-instance state a flag could have.
    }

    /**
     * The environment variable a flag's key is read from.
     *
     * @param key the flag's name as {@code infra/service/flags.auto.tfvars} declares it, in one spelling
     * @return that key as the stack spells it: {@code checkout-v2} becomes {@code FLAG_CHECKOUT_V2}
     */
    public static String variable(String key) {
        return PREFIX + key.toUpperCase(Locale.ROOT).replace('-', '_');
    }

    /**
     * The key a flag variable came from, or null for a variable that is not a flag's.
     *
     * <p>The inverse is exact only because a key may not contain an underscore — {@code check-flags.py}
     * holds every declared key to {@code [a-z0-9][a-z0-9-]*} — so every underscore in the variable came
     * from a dash. It is deliberately anchored on the prefix, which is why {@code VITE_FLAG_CHECKOUT_V2},
     * the browser's spelling of the same flag, is not a flag variable here.
     *
     * @param variable an environment variable's name
     * @return the flag's key: {@code FLAG_CHECKOUT_V2} becomes {@code checkout-v2}
     */
    public static @Nullable String key(String variable) {
        if (!variable.startsWith(PREFIX)) {
            return null;
        }
        return variable.substring(PREFIX.length()).toLowerCase(Locale.ROOT).replace('_', '-');
    }

    /**
     * A source over the given variables, under the names {@code infra/service/flags.tf} gives them.
     *
     * <p>The only source that knows a flag is carried under a different name than the one it is declared
     * with: the transform is the environment's business and nobody else's.
     *
     * @param environment the variables to read; a key it does not carry is off, as an unset one is
     * @return a source reading that map through {@link #variable(String)}
     */
    public static Source environmentSource(Map<String, String> environment) {
        return new Source() {

            @Override
            public @Nullable String value(String key) {
                return environment.get(variable(key));
            }

            @Override
            public Map<String, String> snapshot() {
                Map<String, String> flags = new HashMap<>();
                environment.forEach((variable, value) -> {
                    String declared = key(variable);
                    if (declared != null) {
                        flags.put(declared, value);
                    }
                });
                return Map.copyOf(flags);
            }
        };
    }

    /**
     * A source over this process's own environment, which is where ECS puts the parameters.
     *
     * @return a source over {@code System.getenv}
     */
    public static Source processEnvironment() {
        return environmentSource(System.getenv());
    }

    /**
     * A source over flags held by key, which is what a test drives both paths with.
     *
     * @param values the flags, under the keys {@code flags.auto.tfvars} declares them with — so a test
     *     never spells a variable name
     * @return a source reading that map by key
     */
    public static Source fixedSource(Map<String, String> values) {
        return new Source() {

            @Override
            public @Nullable String value(String key) {
                return values.get(key);
            }

            @Override
            public Map<String, String> snapshot() {
                return Map.copyOf(values);
            }
        };
    }

    /**
     * Where this service's flags come from — the one line a change of transport is.
     *
     * <p>Returned per read rather than held in a static field, so that a source with state of its own (a
     * poller holding the last configuration it fetched) can memoize behind this and still be swapped in
     * here alone.
     *
     * @return the transport this service reads its flags through
     */
    public static Source defaultSource() {
        return processEnvironment();
    }

    /**
     * Whether the named flag is on, read through this service's own source.
     *
     * @param key the flag's name as {@code infra/service/flags.auto.tfvars} declares it
     * @return true only when this environment sets it to {@code on}
     */
    public static boolean enabled(String key) {
        return enabled(key, defaultSource());
    }

    /**
     * Whether the named flag is on in the given source, which is what a test drives both paths with.
     *
     * @param key the flag's name as {@code infra/service/flags.auto.tfvars} declares it
     * @param source where to read it from
     * @return true only when that source answers {@code on}
     */
    public static boolean enabled(String key, Source source) {
        return ON.equals(source.value(key));
    }
}
