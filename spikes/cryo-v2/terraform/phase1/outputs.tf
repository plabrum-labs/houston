output "run_commands" {
  description = "aws ecs run-task commands for each spike variant. EC2 variants trigger the capacity provider to scale the Spot instance 0->1 automatically; expect it to take 1-2 min longer than Fargate on first run."
  value = {
    latency_fargate = join(" ", [
      "aws ecs run-task --cluster ${local.foundation.cluster_name}",
      "--task-definition ${aws_ecs_task_definition.runner_fargate.family}",
      "--launch-type FARGATE",
      "--network-configuration 'awsvpcConfiguration={subnets=[${local.foundation.subnet_id}],securityGroups=[${local.foundation.security_group_id}],assignPublicIp=ENABLED}'",
    ])
    latency_ec2 = join(" ", [
      "aws ecs run-task --cluster ${local.foundation.cluster_name}",
      "--task-definition ${aws_ecs_task_definition.runner_ec2.family}",
      "--capacity-provider-strategy capacityProvider=${local.foundation.ec2_capacity_provider_name}",
      "--network-configuration 'awsvpcConfiguration={subnets=[${local.foundation.subnet_id}],securityGroups=[${local.foundation.security_group_id}],assignPublicIp=DISABLED}'",
    ])
    enforce_fargate = join(" ", [
      "aws ecs run-task --cluster ${local.foundation.cluster_name}",
      "--task-definition ${aws_ecs_task_definition.enforce_fargate.family}",
      "--launch-type FARGATE",
      "--network-configuration 'awsvpcConfiguration={subnets=[${local.foundation.subnet_id}],securityGroups=[${local.foundation.security_group_id}],assignPublicIp=ENABLED}'",
    ])
    enforce_ec2 = join(" ", [
      "aws ecs run-task --cluster ${local.foundation.cluster_name}",
      "--task-definition ${aws_ecs_task_definition.enforce_ec2.family}",
      "--capacity-provider-strategy capacityProvider=${local.foundation.ec2_capacity_provider_name}",
      "--network-configuration 'awsvpcConfiguration={subnets=[${local.foundation.subnet_id}],securityGroups=[${local.foundation.security_group_id}],assignPublicIp=DISABLED}'",
    ])
  }
}
