package anthro.guard

default allow = false

# Block unaliased paths
deny { re_match(`/[A-Za-z0-9_\-.~/]{3,}`, input.body) }
# Block obvious secrets
deny { contains(lower(input.body), "sk_") }

allow { not deny }