package com.example.orderservice;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Mints and verifies HMAC-SHA256 valet keys scoped to a resource and
 * operation with a TTL of 300 seconds.
 */
@Service
public class ValetKeyService {

    private static final String ALGORITHM = "HmacSHA256";
    private static final int TTL_SECONDS = 300;

    private final byte[] secret;

    public ValetKeyService(@Value("${VALET_SECRET:demo-secret-do-not-use-in-prod}") String secret) {
        this.secret = secret.getBytes();
    }

    /**
     * Mint a signed valet key for the given resource and operation.
     */
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

    /**
     * Verify a valet key.  Returns true only when the token is not expired
     * and the HMAC matches (constant-time comparison).
     */
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
