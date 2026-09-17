package com.example.deliverystarter.flags;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The transform, its inverse, both sources and both paths, tested with nothing running.
 *
 * <p>Plain JUnit 5 and no application context, for the reason {@code HealthStatusTest} states: this class
 * names no framework type, so booting one to assert a string comparison would be slower and prove less.
 */
class FlagsTest {

    @Test
    void spellsAFlagTheWayTheStackAsksEcsToSpellIt() {
        // The same transform as `FLAG_${upper(replace(flag.key, "-", "_"))}` in infra/service/flags.tf,
        // which is what puts the value in this container's environment at start-up. If this expectation
        // changes the flag stops arriving — and an absent flag reads as off, so nothing says so loudly.
        assertThat(Flags.variable("checkout-v2")).isEqualTo("FLAG_CHECKOUT_V2");
        assertThat(Flags.variable("publish-table")).isEqualTo("FLAG_PUBLISH_TABLE");
    }

    @Test
    void theKeyIsTheExactInverseOfTheVariable() {
        // Exact only because `check-flags.py` holds a key to `[a-z0-9][a-z0-9-]*`: no underscore can be in
        // a key, so every underscore in the variable came from a dash.
        for (String key : new String[] {"checkout-v2", "publish-table", "a", "b2b-invoicing-v10"}) {
            assertThat(Flags.key(Flags.variable(key))).isEqualTo(key);
        }
    }

    @Test
    void aVariableThatIsNotAFlagHasNoKey() {
        assertThat(Flags.key("DATABASE_URL")).isNull();
        assertThat(Flags.key("PGSSLMODE")).isNull();
        // The browser's spelling of the same flag. It is a flag, but it is not this side's — the prefix
        // anchor is what keeps the two apart, here and in `check-flags.py`'s read pattern.
        assertThat(Flags.key("VITE_FLAG_CHECKOUT_V2")).isNull();
    }

    @Test
    void anEnvironmentSourceReadsAKeyUnderTheNameTheStackGivesIt() {
        // The transform is the environment's business and nobody else's: this is the only source that
        // knows a flag is carried under a different name than the one it is declared with.
        assertThat(Flags.environmentSource(Map.of("FLAG_CHECKOUT_V2", "on")).value("checkout-v2"))
                .isEqualTo("on");
        assertThat(Flags.environmentSource(Map.of()).value("checkout-v2")).isNull();
    }

    @Test
    void anEnvironmentSourceSnapshotsEveryFlagAndNothingThatIsNotOne() {
        // What the service serves to the browser app, which cannot read these itself. The database URL is
        // in the same environment and is not a flag; `VITE_FLAG_…` is a flag and is not this side's.
        Map<String, String> environment = Map.of(
                "FLAG_CHECKOUT_V2", "on",
                "FLAG_PUBLISH_TABLE", "off",
                "DATABASE_URL", "postgres://nope",
                "VITE_FLAG_CHECKOUT_V2", "on");
        assertThat(Flags.environmentSource(environment).snapshot())
                .containsExactlyInAnyOrderEntriesOf(Map.of("checkout-v2", "on", "publish-table", "off"));
    }

    @Test
    void aFixedSourceIsKeyedByTheFlagKey() {
        // So a test never spells a variable name.
        assertThat(Flags.fixedSource(Map.of("checkout-v2", "on")).value("checkout-v2")).isEqualTo("on");
        assertThat(Flags.fixedSource(Map.of()).value("checkout-v2")).isNull();
        assertThat(Flags.fixedSource(Map.of("checkout-v2", "on")).snapshot())
                .containsExactlyInAnyOrderEntriesOf(Map.of("checkout-v2", "on"));
    }

    @Test
    void theDefaultSourceIsTheTransportThisServiceHas() {
        // Where a flag comes from is this one method, and a change of transport is a change to it alone.
        // Asked for a key no project would declare, so that somebody who has exported a real flag to try
        // a feature locally does not fail this suite by doing so.
        assertThat(Flags.defaultSource().value("no-flag-sets-this")).isNull();
    }

    @Test
    void isOnOnlyForTheValueMakeFlagWrites() {
        assertThat(Flags.enabled("checkout-v2", Flags.fixedSource(Map.of("checkout-v2", "on")))).isTrue();
        assertThat(Flags.enabled("checkout-v2", Flags.fixedSource(Map.of("checkout-v2", "off")))).isFalse();
    }

    @Test
    void isOffWhenNothingSetItRatherThanThrowing() {
        // The window between merging code that reads a flag and the apply that creates its parameter. Off
        // is a feature nobody can see yet; an exception is a task that will not start.
        assertThat(Flags.enabled("checkout-v2", Flags.fixedSource(Map.of()))).isFalse();
        // The process's own environment, asked for a key no project would declare — so that somebody who
        // has exported a real flag to try a feature locally does not fail this suite by doing so.
        assertThat(Flags.enabled("no-flag-sets-this")).isFalse();
    }

    @Test
    void isOffForAValueItDoesNotUnderstand() {
        // What a shell, a tfvars file or a hand-run `aws ssm put-parameter` would let somebody write. None
        // of them is the spelling, so all of them are off: a flag whose value is not understood hides the
        // feature it gates rather than half-revealing one.
        for (String value : new String[] {"true", "1", "ON", "yes"}) {
            assertThat(Flags.enabled("checkout-v2", Flags.fixedSource(Map.of("checkout-v2", value))))
                    .isFalse();
        }
    }

    @Test
    void readsThroughWhicheverSourceItIsGiven() {
        // The two implementations meeting at one call: same key, same answer, different transport.
        assertThat(Flags.enabled("checkout-v2", Flags.environmentSource(Map.of("FLAG_CHECKOUT_V2", "on"))))
                .isTrue();
        assertThat(Flags.enabled("checkout-v2", Flags.environmentSource(Map.of()))).isFalse();
    }
}
