package com.example.deliverystarter.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/**
 * The URL translation, tested directly.
 *
 * <p>Worth its own tests rather than being covered incidentally by the integration suite: this is the seam
 * between the address every backend in this factory shares and the one JDBC insists on, it runs before
 * anything is connected, and a mistake in it points a service at the wrong database rather than failing.
 */
class DatabaseUrlTest {

    @Test
    void splitsALibpqUrlIntoWhatJdbcNeeds() {
        DatabaseUrl parsed = DatabaseUrl.parse("postgres://app:secret@localhost:5433/app");

        assertThat(parsed.jdbcUrl()).isEqualTo("jdbc:postgresql://localhost:5433/app");
        assertThat(parsed.username()).isEqualTo("app");
        assertThat(parsed.password()).isEqualTo("secret");
    }

    @Test
    void acceptsTheHostAndPortCiRuns() {
        assertThat(DatabaseUrl.parse("postgres://app:app@postgres:5432/app").jdbcUrl())
                .isEqualTo("jdbc:postgresql://postgres:5432/app");
    }

    @Test
    void acceptsBothSpellingsOfTheScheme() {
        assertThat(DatabaseUrl.parse("postgresql://host/db").jdbcUrl())
                .isEqualTo("jdbc:postgresql://host/db");
    }

    /** sslmode is the option that matters in a real environment, so options are carried through. */
    @Test
    void keepsTheQueryStringSoConnectionOptionsSurvive() {
        assertThat(DatabaseUrl.parse("postgres://app@db:5432/app?sslmode=require").jdbcUrl())
                .isEqualTo("jdbc:postgresql://db:5432/app?sslmode=require");
    }

    @Test
    void readsAUrlWithNoPasswordAsHavingNone() {
        DatabaseUrl parsed = DatabaseUrl.parse("postgres://app@db/app");

        assertThat(parsed.username()).isEqualTo("app");
        assertThat(parsed.password()).isEmpty();
    }

    /**
     * Loud rather than silent, on purpose. A configuration mistake that produces no value produces a service
     * connected to the fallback database, which is the most expensive way to learn about a typo.
     */
    @Test
    void refusesAnUnsetUrlWithTheInstructionThatFixesIt() {
        assertThatThrownBy(() -> DatabaseUrl.parse(null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining(".env.example");
        assertThatThrownBy(() -> DatabaseUrl.parse("   "))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void refusesASchemeItCannotTranslate() {
        assertThatThrownBy(() -> DatabaseUrl.parse("mysql://app@db/app"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("postgres");
    }

    @Test
    void refusesAUrlWithNoHost() {
        assertThatThrownBy(() -> DatabaseUrl.parse("postgres:///app"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("no host");
    }
}
