output "cluster_name" {
  value = aws_ecs_cluster.spike.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.spike.arn
}

output "vpc_id" {
  value = aws_vpc.spike.id
}

output "subnet_id" {
  value = aws_subnet.public.id
}

output "security_group_id" {
  value = aws_security_group.spike.id
}

output "task_execution_role_arn" {
  value = aws_iam_role.task_execution.arn
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.spike.name
}

output "ecr_repository_urls" {
  value = { for k, r in aws_ecr_repository.images : k => r.repository_url }
}

output "binaries_bucket" {
  value = aws_s3_bucket.binaries.bucket
}

output "ec2_capacity_provider_name" {
  value = aws_ecs_capacity_provider.ec2.name
}
