locals {
  foundation = data.terraform_remote_state.foundation.outputs

  # Public image, mirrored through ECR public gateway to dodge Docker Hub
  # rate limits from inside AWS.
  redis_image = "public.ecr.aws/docker/library/redis:7-alpine"
}

resource "aws_ecs_task_definition" "redis" {
  family                   = "cryo-v2-spike-redis"
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
      name      = "redis"
      image     = local.redis_image
      essential = true
      portMappings = [
        { containerPort = 6379, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "redis"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "control_plane" {
  family                   = "cryo-v2-spike-control-plane"
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
      name      = "control-plane"
      image     = "${local.foundation.ecr_repository_urls["control-plane"]}:latest"
      essential = true
      # REDIS_ADDR is a placeholder; the actual redis task IP is only known
      # after it starts, so run-task overrides this at invocation time.
      environment = [
        { name = "REDIS_ADDR", value = "127.0.0.1:6379" },
        { name = "REDIS_KEY", value = "spike:endpoints" },
        { name = "GRPC_PORT", value = "18000" },
      ]
      portMappings = [
        { containerPort = 18000, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "control-plane"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "echo_backend" {
  family                   = "cryo-v2-spike-echo-backend"
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
      name      = "echo-backend"
      image     = "${local.foundation.ecr_repository_urls["echo-backend"]}:latest"
      essential = true
      # INSTANCE_ID is a placeholder; run-task overrides it per instance (A/B).
      environment = [
        { name = "PORT", value = "8080" },
        { name = "INSTANCE_ID", value = "unset" },
      ]
      portMappings = [
        { containerPort = 8080, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "echo-backend"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "envoy" {
  family                   = "cryo-v2-spike-envoy"
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
      name      = "envoy"
      image     = "${local.foundation.ecr_repository_urls["envoy"]}:latest"
      essential = true
      # XDS_SERVER_IP is a placeholder; run-task overrides it once the
      # control-plane task's IP is known.
      environment = [
        { name = "XDS_SERVER_IP", value = "127.0.0.1" },
      ]
      portMappings = [
        { containerPort = 10000, protocol = "tcp" },
        { containerPort = 9901, protocol = "tcp" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = local.foundation.log_group_name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "envoy"
        }
      }
    }
  ])
}
