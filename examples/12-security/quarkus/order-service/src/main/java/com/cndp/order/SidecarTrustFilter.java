package com.cndp.order;

import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.container.PreMatching;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.Provider;

@Provider
@PreMatching
public class SidecarTrustFilter implements ContainerRequestFilter {

    static final String IDENTITY_PROPERTY = "sidecar.identity";
    static final String SUBJECT_PROPERTY = "sidecar.subject";

    private static final String IDENTITY_HEADER = "X-Forwarded-Client-Cert";
    private static final String SUBJECT_HEADER = "X-Jwt-Claim-Sub";

    @Override
    public void filter(ContainerRequestContext context) {
        String path = context.getUriInfo().getPath();
        if (path.equals("healthz") || path.equals("/healthz")) {
            return;
        }

        String spiffe = context.getHeaderString(IDENTITY_HEADER);
        if (spiffe == null || spiffe.isBlank()) {
            context.abortWith(Response.status(Response.Status.FORBIDDEN)
                    .entity("{\"error\":\"no validated identity\"}")
                    .type(MediaType.APPLICATION_JSON)
                    .build());
            return;
        }

        context.setProperty(IDENTITY_PROPERTY, spiffe);
        String subject = context.getHeaderString(SUBJECT_HEADER);
        context.setProperty(SUBJECT_PROPERTY,
                subject != null && !subject.isBlank() ? subject : "anonymous");
    }
}
