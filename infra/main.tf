terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.50, != 6.14.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 2.0"
    }
    logtail = {
      source  = "BetterStackHQ/logtail"
      version = "~> 0.8"
    }
  }

  # Backend config is passed via -backend-config flags in CI (terraform.yml).
  # Bucket name is derived at runtime: tf-state-<aws-account-id>
  # Run locally: scripts/tf-init.sh (or pass flags manually)
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "houston"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "vercel" {
  api_token = var.vercel_api_token
  team      = var.vercel_team_id != "" ? var.vercel_team_id : null
}

provider "logtail" {
  api_token = var.logtail_api_token
}

resource "logtail_source" "api" {
  name     = "${var.project_name}-${var.environment}"
  platform = "open_telemetry"
}

# -- EC2 stack (deploy_target = "ec2") -----------------------------------------

module "ec2" {
  count  = var.deploy_target == "ec2" ? 1 : 0
  source = "./modules/ec2_stack"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  domain       = var.domain

  hosted_zone_id     = aws_route53_zone.main.zone_id
  ecr_repository_url = aws_ecr_repository.app.repository_url

  image_tag   = var.image_tag
  db_password = var.db_password
  extra_env   = var.extra_env

  instance_type     = var.instance_type
  key_pair_name     = var.key_pair_name
  ssh_allowed_cidrs = var.ssh_allowed_cidrs

  betterstack_otlp_ingesting_host = logtail_source.api.ingesting_host
  betterstack_otlp_source_token   = logtail_source.api.token
}

# -- ECS stack (deploy_target = "ecs") -----------------------------------------

module "ecs" {
  count  = var.deploy_target == "ecs" ? 1 : 0
  source = "./modules/app_stack"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  domain       = var.domain

  hosted_zone_id     = aws_route53_zone.main.zone_id
  ecr_repository_url = aws_ecr_repository.app.repository_url

  image_tag   = var.image_tag
  db_password = var.db_password
  extra_env   = var.extra_env

  betterstack_otlp_ingesting_host = logtail_source.api.ingesting_host
  betterstack_otlp_source_token   = logtail_source.api.token
}

# -- Vercel DNS (Route53 side - points domains at Vercel's edge) ---------------

resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain
  type    = "A"
  ttl     = 300
  records = ["76.76.21.21"] # Vercel anycast IP
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain}"
  type    = "CNAME"
  ttl     = 300
  records = ["cname.vercel-dns.com"]
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.${var.domain}"
  type    = "CNAME"
  ttl     = 300
  records = ["cname.vercel-dns.com"]
}

# -- Vercel projects -----------------------------------------------------------

module "vercel_landing" {
  source = "./modules/vercel_project"

  name              = "${var.project_name}-landing"
  framework         = "nextjs"
  root_directory    = "landing"
  github_repo       = var.github_repo
  production_branch = var.production_branch
  team_id           = var.vercel_team_id

  domains = [var.domain, "www.${var.domain}"]

  environment_variables = [
    {
      key    = "NEXT_PUBLIC_API_URL"
      value  = "https://api.${var.domain}"
      target = ["production"]
    },
    {
      key    = "NEXT_PUBLIC_APP_URL"
      value  = "https://app.${var.domain}"
      target = ["production"]
    },
  ]
}

module "vercel_web" {
  source = "./modules/vercel_project"

  name              = "${var.project_name}-web"
  framework         = "vite"
  root_directory    = "frontend"
  github_repo       = var.github_repo
  production_branch = var.production_branch
  team_id           = var.vercel_team_id

  domains = ["app.${var.domain}"]

  environment_variables = [
    {
      key    = "VITE_API_URL"
      value  = "https://api.${var.domain}"
      target = ["production"]
    },
  ]
}

# -- Outputs -------------------------------------------------------------------

output "deploy_target" {
  description = "Active deploy target"
  value       = var.deploy_target
}

# EC2 outputs (empty when deploy_target = "ecs")
output "instance_id" {
  description = "EC2 instance ID (ec2 only)"
  value       = try(module.ec2[0].instance_id, "")
}

output "public_ip" {
  description = "EC2 public IP (ec2 only)"
  value       = try(module.ec2[0].public_ip, "")
}

# ECS outputs (empty when deploy_target = "ec2")
output "alb_dns_name" {
  description = "ALB DNS name (ecs only)"
  value       = try(module.ecs[0].alb_dns_name, "")
}

output "ecs_cluster_name" {
  description = "ECS cluster name (ecs only)"
  value       = try(module.ecs[0].ecs_cluster_name, "")
}

output "ecs_service_name" {
  description = "ECS API service name (ecs only)"
  value       = try(module.ecs[0].ecs_service_name, "")
}

output "worker_service_name" {
  description = "ECS worker service name (ecs only)"
  value       = try(module.ecs[0].worker_service_name, "")
}

# Shared outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "app_secrets_arn" {
  description = "Secrets Manager ARN"
  value       = try(module.ec2[0].app_secrets_arn, try(module.ecs[0].app_secrets_arn, ""))
  sensitive   = true
}

output "s3_media_bucket" {
  description = "S3 media bucket name"
  value       = try(module.ec2[0].s3_media_bucket, try(module.ecs[0].s3_media_bucket, ""))
}

output "database_endpoint" {
  description = "Aurora write endpoint (ecs only)"
  value       = try(module.ecs[0].database_endpoint, "")
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint (ecs only)"
  value       = try(module.ecs[0].redis_endpoint, "")
  sensitive   = true
}

output "route53_nameservers" {
  description = "Nameservers to configure at your domain registrar"
  value       = aws_route53_zone.main.name_servers
}

output "vercel_landing_project_id" {
  description = "Vercel project ID for the landing page"
  value       = module.vercel_landing.project_id
}

output "vercel_web_project_id" {
  description = "Vercel project ID for the web app"
  value       = module.vercel_web.project_id
}
