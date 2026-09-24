# ---------------------------------------------------------------------------
# Monitoring: CloudWatch only (logs, metrics, alarms, one dashboard)
#
# The application writes one JSON object per log line (core/logging.py,
# docker/gunicorn.conf.py), so security events become metrics through log
# metric filters without any agent or extra service.
# ---------------------------------------------------------------------------
locals {
  metric_namespace = "EPIConnect"
  alarm_actions    = [aws_sns_topic.alarms.arn]
}

resource "aws_sns_topic" "alarms" {
  #checkov:skip=CKV_AWS_26:CloudWatch alarms cannot publish to a topic encrypted with the AWS-managed SNS key; a CMK is out of budget
  name = "${var.project}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# --- Log-based metrics ------------------------------------------------------
resource "aws_cloudwatch_log_metric_filter" "failed_logins" {
  name           = "failed-logins"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "{ $.event = \"audit\" && $.action = \"login_failed\" }"
  metric_transformation {
    name          = "FailedLogins"
    namespace     = local.metric_namespace
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "lockouts" {
  name           = "account-lockouts"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "{ $.logger = \"axes*\" && $.message = \"*Locking out*\" }"
  metric_transformation {
    name          = "AccountLockouts"
    namespace     = local.metric_namespace
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "app_errors" {
  name           = "application-errors"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "{ $.level = \"ERROR\" }"
  metric_transformation {
    name          = "ApplicationErrors"
    namespace     = local.metric_namespace
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "rate_limited" {
  name           = "rate-limited-requests"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "{ $.event = \"access\" && $.status = 429 }"
  metric_transformation {
    name          = "RateLimitedRequests"
    namespace     = local.metric_namespace
    value         = "1"
    default_value = "0"
  }
}

# --- Alarms -----------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "failed_logins" {
  alarm_name          = "${var.project}-failed-logins-spike"
  alarm_description   = "Possible brute-force / credential stuffing: 20+ failed logins in 5 minutes"
  namespace           = local.metric_namespace
  metric_name         = "FailedLogins"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 20
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "app_errors" {
  alarm_name          = "${var.project}-application-errors"
  alarm_description   = "5+ unhandled application errors in 5 minutes"
  namespace           = local.metric_namespace
  metric_name         = "ApplicationErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "no_healthy_targets" {
  alarm_name          = "${var.project}-no-healthy-targets"
  alarm_description   = "The load balancer has no healthy application task"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HealthyHostCount"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.app.arn_suffix
  }
  alarm_actions = local.alarm_actions
  ok_actions    = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${var.project}-target-5xx"
  alarm_description   = "10+ HTTP 5xx responses from the application in 5 minutes"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { LoadBalancer = aws_lb.main.arn_suffix }
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  alarm_name          = "${var.project}-ecs-memory-high"
  alarm_description   = "Application tasks above 85% memory for 10 minutes"
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
  alarm_actions = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "db_cpu" {
  alarm_name          = "${var.project}-db-cpu-high"
  alarm_description   = "Database CPU above 80% for 10 minutes"
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "db_storage" {
  alarm_name          = "${var.project}-db-storage-low"
  alarm_description   = "Less than 2 GB of database storage left"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 2147483648
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
  alarm_actions       = local.alarm_actions
}

# --- Dashboard --------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = var.project
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Traffic and errors (ALB)"
          region = var.aws_region
          stat   = "Sum"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            [".", "HTTPCode_Target_4XX_Count", ".", "."],
            [".", "HTTPCode_Target_5XX_Count", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "Response time p50 / p95 (s)"
          region = var.aws_region
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "p50" }],
            ["...", { stat = "p95" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 8, height = 6
        properties = {
          title  = "ECS service CPU / memory (%)"
          region = var.aws_region
          stat   = "Average"
          period = 60
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.app.name],
            [".", "MemoryUtilization", ".", ".", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 8, y = 6, width = 8, height = 6
        properties = {
          title  = "Database"
          region = var.aws_region
          stat   = "Average"
          period = 60
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.identifier],
            [".", "DatabaseConnections", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 16, y = 6, width = 8, height = 6
        properties = {
          title  = "Healthy targets"
          region = var.aws_region
          stat   = "Minimum"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", aws_lb_target_group.app.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 12, width = 12, height = 6
        properties = {
          title  = "Security events (from application logs)"
          region = var.aws_region
          stat   = "Sum"
          period = 300
          metrics = [
            [local.metric_namespace, "FailedLogins"],
            [".", "AccountLockouts"],
            [".", "RateLimitedRequests"],
            [".", "ApplicationErrors"],
          ]
        }
      },
      {
        type = "log", x = 12, y = 12, width = 12, height = 6
        properties = {
          title  = "Latest audit events"
          region = var.aws_region
          query  = "SOURCE '${aws_cloudwatch_log_group.app.name}' | fields @timestamp, action, client_ip, details | filter event = 'audit' | sort @timestamp desc | limit 20"
          view   = "table"
        }
      },
    ]
  })
}
