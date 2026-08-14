# Infra / CI/CD

Auto-loaded when editing infra/terraform/workflow files.

## Dev environment (current)

During initial development, the app runs on a single t3.small EC2 instance via docker-compose.
Terraform for this lives in `infra/dev/` (separate state from the production ECS stack).

```bash
cd infra/dev
cp terraform.tfvars.example terraform.tfvars  # fill in db_password
terraform init \
  -backend-config="bucket=tf-state-houston-us-east-1" \
  -backend-config="key=houston/dev/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true"
terraform apply
```

After first apply:
1. Update the Secrets Manager secret (`houston-dev-app-secrets`) with real values (SECRET_KEY, etc.)
2. Push an image to ECR — CI does this automatically on push to main
3. CI deploys via SSM (`_deploy_ec2.yml`); or manually: `terraform output deploy_command`

**OIDC role prerequisite**: The GitHub Actions OIDC role needs `ssm:SendCommand` + `ssm:GetCommandInvocation` added to its policy for EC2 deploys to work.

## CI/CD (`.github/workflows/`)

GitHub Actions with change detection — only deploys when backend or infra changes. Uses AWS OIDC (no long-lived credentials). Pipeline: detect changes → test → build Docker image → Terraform → ECS deploy.

## Critical deployment gotchas

- **Infra-only changes don't redeploy ECS.** The deploy step only runs when `backend_changed=true`. If you change infra (e.g., recreate Redis), Terraform updates the task definition but ECS keeps running old containers with old env vars. Fix: trigger a manual workflow run with both "Deploy infrastructure" and "Deploy application" = true.
- **Migrations run on container startup** via `scripts/start.sh` → `scripts/migrate.py`. If migration fails, the container crashes, health checks return 500, ECS keeps restarting. Check BetterStack logs (not CloudWatch) for migration output.
- **Production logs are on BetterStack** (`logs.betterstack.com`), source `houston-production`. Shipped via OpenTelemetry. Search for `migration`, `alembic`, or error messages there — NOT CloudWatch.
- **Demo reseed:** `POST /api/demo/reseed` (admin-only) wipes and repopulates the demo org. Also runs automatically every Sunday at midnight UTC via SAQ scheduled task. Seed script: `backend/app/demo/seed.py`.
- **Never `uv pip install --force-reinstall`** individual packages — it breaks dependency versions. If venv is corrupted, delete it (`rm -rf backend/.venv`) and rebuild with `just install`.
