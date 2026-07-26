variable "aws_region" {
  description = "AWS region for the spike stack"
  type        = string
  default     = "us-east-1"
}

variable "operator_cidr" {
  description = "CIDR allowed to reach spike tasks directly (your current public IP, /32)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR for the dedicated spike VPC"
  type        = string
  default     = "10.90.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR for the spike's single public subnet"
  type        = string
  default     = "10.90.0.0/24"
}

variable "ec2_instance_type" {
  description = "Instance type for the EC2-backed ECS capacity (Spot). Graviton for cost."
  type        = string
  default     = "t4g.small"
}

variable "log_retention_days" {
  description = "CloudWatch log retention for all spike log groups"
  type        = number
  default     = 3
}

variable "billing_alarm_threshold_usd" {
  description = "Threshold in USD for the estimated-charges billing alarm"
  type        = number
  default     = 20
}
