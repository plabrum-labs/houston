resource "aws_cloudwatch_log_group" "spike" {
  name              = "/ecs/cryo-v2-spike"
  retention_in_days = var.log_retention_days
}
