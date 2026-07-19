package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

@ApplicationScoped
public class ValetKeyService {

    private static final String ALGORITHM = "HmacSHA256";
    private static final int TTL_SECONDS = 300;

    private final byte[] secret;

    public ValetKeyService(
            @ConfigProperty(name = "VALET_SECRET", defaultValue = "demo-secret-do-not-use-in-prod")
            String secret) {
        this.secret = secret.getBytes();
    }

    public Map<String, Object> mint(String resource, String operation) {
        long expires = System.currentTimeMillis() / 1000 + TTL_SECONDS;
        String payload = resource + ":" + operation + ":" + expires;
        String token = hmac(payload);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("resource", resource);
        result.put("operation", operation);
        result.put("expires", expires);
        result.put("token", token);
        return result;
    }

    public boolean verify(String resource, String operation, long expires, String token) {
        if (System.currentTimeMillis() / 1000 > expires) {
            return false;
        }
        String payload = resource + ":" + operation + ":" + expires;
        String expected = hmac(payload);
        return MessageDigest.isEqual(token.getBytes(), expected.getBytes());
    }

    private String hmac(String payload) {
        try {
            Mac mac = Mac.getInstance(ALGORITHM);
            mac.init(new SecretKeySpec(secret, ALGORITHM));
            byte[] hash = mac.doFinal(payload.getBytes());
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            throw new RuntimeException("HMAC computation failed", e);
        }
    }
}
