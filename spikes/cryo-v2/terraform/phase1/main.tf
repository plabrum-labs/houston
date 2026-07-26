locals {
  foundation   = data.terraform_remote_state.foundation.outputs
  runner_image = "${local.foundation.ecr_repository_urls["runner"]}:latest"
  common_env = [
    { name = "SOCKET_DIR", value = "/run/spike" },
  ]
}

# --- Fargate task definition ---
# No added Linux capabilities: Fargate's supported add-capability list does
# not include SYS_ADMIN, so this task definition tests cgroup delegation
# under whatever the platform grants by default (this is itself part of what
# spike 2 needs to find out).
resource "aws_ecs_task_definition" "runner_fargate" {
  family                   = "cryo-v2-spike-runner-fargate"
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
      name      = "runner"
      image     = local.runner_image
      essential = true
      command   = ["latency"]
      environment = concat(local.common_env, [
        { name = "ITERATIONS", value = "50" },
      ])
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "runner-fargate"
        }
      }
    }
  ])
}

# --- EC2-backed task definition ---
# SYS_ADMIN added: EC2 launch type supports arbitrary capability additions,
# giving nested cgroup delegation its best chance here for comparison against
# the Fargate result.
resource "aws_ecs_task_definition" "runner_ec2" {
  family                   = "cryo-v2-spike-runner-ec2"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "256"
  execution_role_arn       = local.foundation.task_execution_role_arn
  task_role_arn            = local.foundation.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "runner"
      image     = local.runner_image
      essential = true
      command   = ["latency"]
      environment = concat(local.common_env, [
        { name = "ITERATIONS", value = "50" },
      ])
      linuxParameters = {
        initProcessEnabled = true
        capabilities = {
          add = ["SYS_ADMIN"]
        }
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "runner-ec2"
        }
      }
    }
  ])
}

# Same two task defs, but invoking the cgroup enforcement check instead of
# the latency loop (spike 2's second half).
resource "aws_ecs_task_definition" "enforce_fargate" {
  family                   = "cryo-v2-spike-enforce-fargate"
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
      name      = "runner"
      image     = local.runner_image
      essential = true
      command   = ["cgroup-enforce"]
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "enforce-fargate"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "enforce_ec2" {
  family                   = "cryo-v2-spike-enforce-ec2"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "256"
  execution_role_arn       = local.foundation.task_execution_role_arn
  task_role_arn            = local.foundation.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "runner"
      image     = local.runner_image
      essential = true
      command   = ["cgroup-enforce"]
      linuxParameters = {
        initProcessEnabled = true
        capabilities = {
          add = ["SYS_ADMIN"]
        }
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "enforce-ec2"
        }
      }
    }
  ])
}
