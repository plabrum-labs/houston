# Dedicated VPC, isolated from any other infra in this account. Single public
# subnet, no NAT gateway — tasks get public IPs directly, kept safe by the
# security group rather than network isolation, since a NAT gateway's fixed
# hourly cost isn't worth it for a throwaway spike.

resource "aws_vpc" "spike" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "cryo-v2-spike"
  }
}

resource "aws_internet_gateway" "spike" {
  vpc_id = aws_vpc.spike.id

  tags = {
    Name = "cryo-v2-spike"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.spike.id
  cidr_block              = var.subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "cryo-v2-spike-public"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.spike.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.spike.id
  }

  tags = {
    Name = "cryo-v2-spike-public"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "spike" {
  name        = "cryo-v2-spike"
  description = "Cryo v2 spike: locked to operator IP, open between spike tasks"
  vpc_id      = aws_vpc.spike.id

  ingress {
    description = "Operator direct access (debugging, ad-hoc test traffic)"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.operator_cidr]
  }

  ingress {
    description = "Intra-spike traffic (runner, envoy, control-plane, redis)"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "Unrestricted egress (S3 binary fetch, ECR pulls, etc.)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
