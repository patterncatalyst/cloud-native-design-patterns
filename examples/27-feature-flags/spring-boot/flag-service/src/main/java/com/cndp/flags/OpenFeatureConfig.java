package com.cndp.flags;

import dev.openfeature.contrib.providers.flagd.FlagdOptions;
import dev.openfeature.contrib.providers.flagd.FlagdProvider;
import dev.openfeature.sdk.OpenFeatureAPI;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import jakarta.annotation.PostConstruct;

@Configuration
public class OpenFeatureConfig {

    private static final Logger log = LoggerFactory.getLogger(OpenFeatureConfig.class);

    @Value("${flagd.host:flagd}")
    private String flagdHost;

    @Value("${flagd.port:8013}")
    private int flagdPort;

    @PostConstruct
    public void init() {
        try {
            FlagdProvider provider = new FlagdProvider(
                FlagdOptions.builder()
                    .host(flagdHost)
                    .port(flagdPort)
                    .deadline(2000)
                    .build()
            );
            OpenFeatureAPI.getInstance().setProvider(provider);
            log.info("OpenFeature provider set: flagd at {}:{}", flagdHost, flagdPort);
        } catch (Exception e) {
            log.warn("Failed to connect to flagd at {}:{} — will use defaults: {}",
                     flagdHost, flagdPort, e.getMessage());
        }
    }

    @PreDestroy
    public void shutdown() {
        try {
            OpenFeatureAPI.getInstance().shutdown();
        } catch (Exception e) {
            // ignore
        }
    }
}
