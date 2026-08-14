terraform {
  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 2.0"
    }
  }
}

resource "vercel_project" "main" {
  name           = var.name
  framework      = var.framework
  root_directory = var.root_directory
  ignore_command = "git diff --quiet HEAD^ HEAD ./"

  git_repository = {
    type              = "github"
    repo              = var.github_repo
    production_branch = var.production_branch
  }

  team_id = var.team_id != "" ? var.team_id : null
}

resource "vercel_project_domain" "main" {
  for_each   = toset(var.domains)
  project_id = vercel_project.main.id
  domain     = each.value
  team_id    = var.team_id != "" ? var.team_id : null
}

# Keyed by "{key}-{targets}" so the same env var key can exist for multiple targets
resource "vercel_project_environment_variable" "main" {
  for_each   = { for ev in var.environment_variables : "${ev.key}-${join(",", ev.target)}" => ev }
  project_id = vercel_project.main.id
  team_id    = var.team_id != "" ? var.team_id : null
  key        = each.value.key
  value      = each.value.value
  target     = each.value.target
}
