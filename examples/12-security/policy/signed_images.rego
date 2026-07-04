package main

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    not startswith(container.image, "registry.internal/")
    not startswith(container.image, "registry.access.redhat.com/")
    msg := sprintf("container '%s' uses untrusted image '%s'", [container.name, container.image])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("container '%s' runs privileged", [container.name])
}

deny[msg] {
    input.kind == "Deployment"
    container := input.spec.template.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := sprintf("container '%s' runs as root (UID 0)", [container.name])
}
