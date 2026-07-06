package com.example.orderservice;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Map;
import java.util.Set;

/**
 * Jakarta Servlet Filter that enforces sidecar trust.
 * Rejects requests without the X-Forwarded-Client-Cert header (set by
 * the service mesh sidecar) with a 403.  Open paths like /healthz are
 * exempt.
 */
@Component
@Order(1)
public class SidecarTrustFilter implements Filter {

    private static final Set<String> OPEN_PATHS = Set.of("/healthz");
    private static final String IDENTITY_HEADER = "X-Forwarded-Client-Cert";
    private static final String SUBJECT_HEADER = "X-Jwt-Claim-Sub";

    public static final String ATTR_IDENTITY = "sidecar.identity";
    public static final String ATTR_SUBJECT = "sidecar.subject";

    private final ObjectMapper mapper = new ObjectMapper();

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {

        HttpServletRequest httpReq = (HttpServletRequest) request;
        HttpServletResponse httpRes = (HttpServletResponse) response;

        if (OPEN_PATHS.contains(httpReq.getRequestURI())) {
            chain.doFilter(request, response);
            return;
        }

        String spiffe = httpReq.getHeader(IDENTITY_HEADER);
        if (spiffe == null || spiffe.isBlank()) {
            httpRes.setStatus(403);
            httpRes.setContentType("application/json");
            httpRes.getWriter().write(
                    mapper.writeValueAsString(Map.of("detail", "no validated identity")));
            return;
        }

        httpReq.setAttribute(ATTR_IDENTITY, spiffe);
        String subject = httpReq.getHeader(SUBJECT_HEADER);
        httpReq.setAttribute(ATTR_SUBJECT, subject != null && !subject.isBlank() ? subject : "anonymous");

        chain.doFilter(request, response);
    }
}
