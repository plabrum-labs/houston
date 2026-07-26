resource "aws_ecr_repository" "images" {
  for_each = toset(["runner", "control-plane", "scheduler-harness", "echo-backend", "envoy"])

  name         = "cryo-v2-spike/${each.key}"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }
}
