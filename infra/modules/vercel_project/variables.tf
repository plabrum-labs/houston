variable "name" { type = string }
variable "framework" { type = string }
variable "root_directory" { type = string }
variable "github_repo" { type = string }
variable "production_branch" { type = string }
variable "team_id" {
  type    = string
  default = ""
}

variable "domains" {
  description = "List of custom domains to attach to this project"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables. Use target to scope to production/preview/development."
  type = list(object({
    key    = string
    value  = string
    target = list(string)
  }))
  default = []
}
