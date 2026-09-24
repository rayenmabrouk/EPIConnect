# ---------------------------------------------------------------------------
# ECS on Fargate: one service, one container, no servers to patch
# ---------------------------------------------------------------------------
locals {
  app_domain = aws_cloudfront_distribution.main.domain_name
  image      = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
}

resource "aws_ecs_cluster" "main" {
  #checkov:skip=CKV_AWS_65:Container Insights is billed per metric; free service-level CPU/memory metrics are used instead
  name = var.project

  setting {
    name  = "containerInsights"
    value = "disabled" # service-level CPU/memory metrics are free; Insights is billed per metric
  }
}

resource "aws_cloudwatch_log_group" "app" {
  #checkov:skip=CKV_AWS_158:AWS-managed encryption at rest is on by default; a CMK costs $1/month and adds key-policy work for a demo
  #checkov:skip=CKV_AWS_338:14-day retention keeps cost near zero for a student demo; production would keep 1 year
  name              = "/ecs/${var.project}"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.project
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = local.execution_role_arn
  task_role_arn            = local.task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64" # matches the CI runners that build and scan the image
  }

  # Writable scratch space; the rest of the container filesystem is read-only
  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "web"
    image                  = local.image
    essential              = true
    readonlyRootFilesystem = true
    stopTimeout            = 30
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters        = { initProcessEnabled = true }

    environment = [
      { name = "ALLOWED_HOSTS", value = local.app_domain },
      { name = "CSRF_TRUSTED_ORIGINS", value = "https://${local.app_domain}" },
      { name = "SECURE_PROXY_SSL_HEADER", value = "HTTP_CLOUDFRONT_FORWARDED_PROTO" },
      { name = "TRUSTED_PROXY_COUNT", value = "2" }, # CloudFront + ALB
      { name = "DB_HOST", value = aws_db_instance.main.address },
      { name = "DB_NAME", value = aws_db_instance.main.db_name },
      { name = "DB_USER", value = aws_db_instance.main.username },
      { name = "DB_SSLMODE", value = "require" },
      { name = "AWS_STORAGE_BUCKET_NAME", value = aws_s3_bucket.media.bucket },
      { name = "MEDIA_DOMAIN", value = local.app_domain },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "APP_SECRET_ARN", value = aws_secretsmanager_secret.app.arn },
      { name = "LOG_LEVEL", value = "INFO" },
    ]

    # Resolved by the ECS agent at task start; values never stored in the task definition
    secrets = [
      { name = "SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:SECRET_KEY::" },
      { name = "DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.app.arn}:DB_PASSWORD::" },
    ]

    healthCheck = {
      command     = ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4).status == 200 else 1)"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "web"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  #checkov:skip=CKV_AWS_333:No NAT gateway (cost); public IP only for outbound AWS API calls, inbound limited to the ALB security group
  name                               = "${var.project}-web"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.app.arn
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  desired_count                      = 0 # the pipeline scales to 1 after pushing the first image
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60
  enable_execute_command             = false
  propagate_tags                     = "SERVICE"

  # A deployment whose tasks never become healthy is stopped and rolled back
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = true # outbound to AWS APIs without a NAT gateway
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "web"
    container_port   = 8000
  }

  # The pipeline owns image rollouts (new task definition revisions) and scaling
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener_rule.from_cloudfront]
}

# Values the delivery pipeline reads at deploy time (no hard-coded ARNs in CI)
resource "aws_ssm_parameter" "deploy" {
  #checkov:skip=CKV2_AWS_34:Non-secret deployment metadata (names/IDs/URL); secrets live in Secrets Manager
  for_each = {
    app_url         = "https://${local.app_domain}"
    cluster         = aws_ecs_cluster.main.name
    service         = aws_ecs_service.app.name
    task_family     = aws_ecs_task_definition.app.family
    ecr_repository  = aws_ecr_repository.app.name
    subnets         = join(",", aws_subnet.public[*].id)
    security_group  = aws_security_group.tasks.id
    distribution_id = aws_cloudfront_distribution.main.id
  }
  name  = "/${var.project}/deploy/${each.key}"
  type  = "String"
  value = each.value
}
