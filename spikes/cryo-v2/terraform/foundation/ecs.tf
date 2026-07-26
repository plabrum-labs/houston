resource "aws_ecs_cluster" "spike" {
  name = "cryo-v2-spike"

  setting {
    name  = "containerInsights"
    value = "disabled" # avoid the extra CloudWatch metrics cost for a throwaway spike
  }
}

# --- EC2-backed capacity, for the EC2-task-type half of spikes 1 and 2 ---
# Scales 0 -> 1 only when a task actually needs EC2 capacity, and back to 0
# once idle, so the instance isn't billed between test runs.

data "aws_ssm_parameter" "ecs_optimized_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/arm64/recommended/image_id"
}

resource "aws_launch_template" "ec2_capacity" {
  name_prefix   = "cryo-v2-spike-"
  image_id      = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = var.ec2_instance_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.ec2_instance.arn
  }

  vpc_security_group_ids = [aws_security_group.spike.id]

  instance_market_options {
    market_type = "spot"
    spot_options {
      spot_instance_type = "one-time"
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo ECS_CLUSTER=${aws_ecs_cluster.spike.name} >> /etc/ecs/ecs.config
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "cryo-v2-spike"
    }
  }
}

resource "aws_autoscaling_group" "ec2_capacity" {
  name                  = "cryo-v2-spike"
  vpc_zone_identifier   = [aws_subnet.public.id]
  min_size              = 0
  max_size              = 1
  desired_capacity      = 0
  protect_from_scale_in = true

  launch_template {
    id      = aws_launch_template.ec2_capacity.id
    version = "$Latest"
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }
}

resource "aws_ecs_capacity_provider" "ec2" {
  name = "cryo-v2-spike-ec2"

  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.ec2_capacity.arn

    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 100
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 1
    }

    managed_termination_protection = "ENABLED"
  }
}

resource "aws_ecs_cluster_capacity_providers" "spike" {
  cluster_name = aws_ecs_cluster.spike.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT", aws_ecs_capacity_provider.ec2.name]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}
