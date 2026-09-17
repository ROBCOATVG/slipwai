package com.example.deliverystarter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * The entry point, and the whole of what "Spring Boot owns startup" means in one file.
 *
 * <p>There is no composition root here, and that is the difference between this backend and one where
 * nothing owns startup. {@code @SpringBootApplication} turns on component scanning over this package and
 * everything below it, so the driving adapters register themselves and the driven ones are configured by
 * the starters they belong to. What that buys is the datasource and its pool, the migration integration,
 * the readiness endpoint and the token validation — none of them written here.
 *
 * <p>What it does not buy, and must not: which event store this application uses. Several adapters can be on
 * the classpath at once and choosing between them is a composition decision, so none of them is a bean. The
 * first slice that needs one writes the {@code @Bean} method — see the note on {@code PostgresEventStore}.
 *
 * <p>It is in the root package on purpose. Component scanning starts from the annotated class's own package,
 * so a main class one level down would silently stop finding half the application.
 */
@SpringBootApplication
public class ServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(ServiceApplication.class, args);
    }
}
