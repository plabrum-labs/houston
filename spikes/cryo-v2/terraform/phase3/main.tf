locals {
  foundation = data.terraform_remote_state.foundation.outputs
}

resource "aws_ecs_task_definition" "scheduler_harness" {
  family                   = "cryo-v2-spike-scheduler-harness"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = local.foundation.task_execution_role_arn
  task_role_arn            = local.foundation.task_role_arn

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "scheduler-harness"
      image     = "${local.foundation.ecr_repository_urls["scheduler-harness"]}:latest"
      essential = true
      # REDIS_ADDR is a placeholder; run-task overrides it with the already
      # running phase2 redis task's private IP.
      environment = [
        { name = "REDIS_ADDR", value = "127.0.0.1:6379" },
        { name = "PORT", value = "9000" },
      ]
      portMappings = [
        { containerPort = 9000, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "scheduler-harness"
        }
      }
    }
  ])
}
