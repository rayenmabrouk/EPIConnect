# Two public subnets (ALB + Fargate tasks) and two private subnets (RDS only).
# No NAT gateway (~$32/month): tasks get a public IP for outbound calls to
# ECR / S3 / CloudWatch / Secrets Manager, and their security group only
# accepts inbound traffic from the load balancer.

data "aws_availability_zones" "available" {
  #checkov:skip=CKV_AWS_394:Only the first two AZs are used (slice), new AZs do not change the result
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  #checkov:skip=CKV2_AWS_11:Flow logs cost money per GB; security groups are the enforced control. Production: enable flow logs
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project}-vpc" }
}

# Remove all rules from the default security group so nothing can use it by accident
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-igw" }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = local.azs[count.index]
  tags              = { Name = "${var.project}-public-${local.azs[count.index]}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  availability_zone = local.azs[count.index]
  tags              = { Name = "${var.project}-private-${local.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.project}-public" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private subnets keep the VPC's implicit local-only route: no path to the internet.

# ---------------------------------------------------------------------------
# Security groups: internet -> ALB -> tasks -> database, nothing else
# ---------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${var.project}-alb"
  description = "ALB: public HTTP entry point"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  #checkov:skip=CKV_AWS_260:Public web application; the ALB is the only internet-facing component
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from the internet"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_tasks" {
  security_group_id            = aws_security_group.alb.id
  description                  = "To application containers"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.tasks.id
}

resource "aws_security_group" "tasks" {
  name        = "${var.project}-tasks"
  description = "Fargate tasks: inbound from ALB only"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "tasks_from_alb" {
  security_group_id            = aws_security_group.tasks.id
  description                  = "Gunicorn from the ALB"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "tasks_https" {
  security_group_id = aws_security_group.tasks.id
  description       = "HTTPS to AWS APIs (ECR, S3, CloudWatch Logs, Secrets Manager)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "tasks_to_db" {
  security_group_id            = aws_security_group.tasks.id
  description                  = "PostgreSQL"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.db.id
}

resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "RDS: PostgreSQL from application tasks only"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "db_from_tasks" {
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL from application tasks"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.tasks.id
}
