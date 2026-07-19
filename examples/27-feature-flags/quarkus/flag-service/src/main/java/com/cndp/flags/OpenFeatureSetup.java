package com.cndp.flags;

import dev.openfeature.contrib.providers.flagd.FlagdOptions;
import dev.openfeature.contrib.providers.flagd.FlagdProvider;
import dev.openfeature.sdk.OpenFeatureAPI;
import io.quarkus.logging.Log;
import io.quarkus.runtime.ShutdownEvent;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class OpenFeatureSetup {

    @ConfigProperty(name = "flagd.host", defaultValue = "flagd")
    String flagdHost;

    @ConfigProperty(name = "flagd.port", defaultValue = "8013")
    int flagdPort;

    void onStart(@Observes StartupEvent ev) {
        try {
            FlagdProvider provider = new FlagdProvider(
                FlagdOptions.builder()
                    .host(flagdHost)
                    .port(flagdPort)
                    .deadline(2000)
                    .build()
            );
            OpenFeatureAPI.getInstance().setProvider(provider);
            Log.infof("OpenFeature provider set: flagd at %s:%d", flagdHost, flagdPort);
        } catch (Exception e) {
            Log.warnf("Failed to connect to flagd at %s:%d — will use defaults: %s",
                      flagdHost, flagdPort, e.getMessage());
        }
    }

    void onStop(@Observes ShutdownEvent ev) {
        try {
            OpenFeatureAPI.getInstance().shutdown();
        } catch (Exception e) {
            Log.debugf("Shutdown error: %s", e.getMessage());
        }
    }
}
