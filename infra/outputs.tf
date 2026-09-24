output "app_url" {
  description = "Public HTTPS URL of the application"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service" {
  value = aws_ecs_service.app.name
}

output "db_endpoint" {
  value = aws_db_instance.main.address
}

output "media_bucket" {
  value = local.media_bucket
}

output "app_secret_name" {
  description = "Secrets Manager secret holding SECRET_KEY, DB_PASSWORD and ADMIN_PASSWORD"
  value       = aws_secretsmanager_secret.app.name
}

output "dashboard_url" {
  value = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards/dashboard/${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "log_group" {
  value = aws_cloudwatch_log_group.app.name
}
