# Placeholder Terraform root for Houston's substrate.
# TODO: design and implement per docs/planning/v0.md (infra/v0). See README.md.
# Do NOT reintroduce marlin's app-deploy model (per-deploy Aurora/Redis/ALB,
# single-host EC2, Vercel frontend). Houston's infra is a shared substrate.

# terraform {
#   required_version = ">= 1.5"
#   backend "s3" {}
# }
