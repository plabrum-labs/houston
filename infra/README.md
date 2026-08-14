# infra/ — Terraform Infrastructure

AWS infrastructure for Houston, managed with Terraform.

**Do NOT apply locally.** All Terraform runs happen via CI/CD or a designated ops machine with the correct AWS credentials and state backend configured.

## Architecture

| Resource | Service | Notes |
|---|---|---|
| API containers | ECS Fargate | Auto-scales on CPU, tasks in public subnets (no NAT cost) |
| Worker containers | ECS Fargate | SAQ background queue processor |
| Container registry | ECR | Images pushed by CI/CD |
| Database | Aurora Serverless v2 (PostgreSQL) | Scale-to-zero when idle |
| Cache / queue | ElastiCache Redis 7 | SAQ jobs + Litestar sessions |
| Audio storage | S3 | Call recordings, lifecycle → Glacier after 90 days |
| Transcripts | S3 | STT output from Deepgram |
| Load balancer | ALB | HTTPS only, HTTP redirects to HTTPS |
| SSL | ACM | Auto-renewed, DNS-validated via Route53 |
| DNS | Route53 | `houstonlabs.co` zone — root/www/app → Vercel, api → ALB |
| Email | SES | Outbound only (magic links, call summaries) |
| Secrets | Secrets Manager | API keys, session secret — managed outside Terraform |
| Sessions | SSM (via VPC endpoints) | ECS Exec / SSH into tasks |

## File Layout

```
infra/
├── main.tf          # Root: providers, module calls, top-level outputs
├── variables.tf     # All input variables with defaults
├── aws/
│   ├── main.tf      # VPC, ECS, Aurora, ALB, Route53, S3, IAM
│   ├── redis.tf     # ElastiCache Redis
│   ├── ses.tf       # SES outbound + Route53 DKIM/SPF/DMARC records
│   ├── variables.tf
│   └── outputs.tf
└── vercel/
    ├── main.tf      # Vercel projects (landing + web) and domain attachments
    ├── variables.tf
    └── outputs.tf
```

## Domain

`houstonlabs.co` — registered via Vercel, DNS managed by Route53.

After `terraform apply`, get the Route53 nameservers and set them in the Vercel registrar dashboard (Domains → houstonlabs.co → Nameservers → Custom):
```bash
terraform output route53_nameservers
```

## First Deploy

1. Create the S3 state bucket (one-time):
   ```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   aws s3api create-bucket --bucket tf-state-${ACCOUNT_ID} --region us-east-1
   aws s3api put-bucket-versioning --bucket tf-state-${ACCOUNT_ID} \
     --versioning-configuration Status=Enabled
   ```

2. Run via CI — push to `main` and let `build-test-deploy.yml` handle it. To run locally:
   ```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   terraform -chdir=infra init -reconfigure \
     -backend-config="bucket=tf-state-${ACCOUNT_ID}" \
     -backend-config="key=houston/dev/terraform.tfstate" \
     -backend-config="region=us-east-1" \
     -backend-config="encrypt=true"
   terraform -chdir=infra workspace select -or-create production
   terraform -chdir=infra plan
   terraform -chdir=infra apply
   ```

5. After apply, update the domain registrar nameservers:
   ```bash
   terraform output route53_nameservers
   ```

6. Rotate the initial DB password and populate Secrets Manager keys via the AWS console.

## Updating Secrets

Secrets are created by Terraform but intentionally **not updated** by it (lifecycle `ignore_changes`). Use the AWS console or CLI:

```bash
aws secretsmanager put-secret-value \
  --secret-id houston-production-app-secrets \
  --secret-string '{"OPENAI_API_KEY": "sk-...", ...}'
```

## ECS Exec (SSH into tasks)

```bash
# Get a shell in a running API task
TASK_ARN=$(aws ecs list-tasks \
  --cluster houston-production-cluster \
  --service-name houston-production-api-service \
  --query 'taskArns[0]' --output text)

aws ecs execute-command \
  --cluster houston-production-cluster \
  --task $TASK_ARN \
  --container app \
  --interactive \
  --command "/bin/bash"
```
