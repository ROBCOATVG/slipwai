package com.example.deliverystarter.adapters.driving.http;

import com.example.deliverystarter.flags.Flags;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * This environment's feature flags, for the browser app — which cannot read them itself.
 *
 * <p>Vite inlines a {@code VITE_}-prefixed value while the bundle is <em>built</em>, so a flag compiled
 * into a bundle is a property of that build and not of the environment it runs in. The service already
 * holds the answer — {@link Flags.Source#snapshot()} is it — so the service serves it and the two halves
 * of one flag move together. The link is relative rather than fully qualified because the package it
 * would name is this project's, and a long project name pushes that line past Checkstyle's 120 columns.
 *
 * <p>Under {@code /api} because that is this service's product surface and a browser calls it;
 * {@code /health} sits outside it, being a probe. {@code vite.config.ts} forwards {@code /api} with the
 * prefix intact and CloudFront's {@code /api/*} behaviour rewrites nothing, so this is the one path in
 * both places.
 *
 * <p>A controller rather than a route registered somewhere, because Spring discovers it — the same reason
 * {@code ServiceHealthIndicator} contributes to a probe it does not own. Which also means this file is the
 * whole of the conditional: a project with nowhere to declare a flag simply does not have it, and so has
 * no {@code /api/flags} rather than one that always answers an empty object.
 *
 * <p>{@code no-store} because the answer is what the environment is set to <em>now</em>: a flipped flag
 * that a cache still hides is the flip looking broken.
 */
@RestController
public class FeatureFlagsController {

    @GetMapping("/api/flags")
    public ResponseEntity<Map<String, String>> flags() {
        return ResponseEntity.ok()
                .header("Cache-Control", "no-store")
                .body(Flags.defaultSource().snapshot());
    }
}
