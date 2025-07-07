# OPA Security Policy - Layer 2 Service Mesh Enforcement  
# Implements firewall rules described in the paper
#
# NOTE: This is the MINIMAL reference policy for academic review.
# See ../../deploy/opa/policies/data_firewall.rego for full production implementation.

package anthro.guard

default allow = false

# Block unaliased paths
deny { re_match(`/[A-Za-z0-9_\-.~/]{3,}`, input.body) }
# Block obvious secrets
deny { contains(lower(input.body), "sk_") }

allow { not deny }