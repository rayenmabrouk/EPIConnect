# ---------------------------------------------------------------------------
# IAM for the ECS tasks
#
# AWS Academy: IAM role creation is denied, so both roles are the pre-created
# LabRole (var.lab_role_name). This is the deployed configuration.
#
# Any other account (lab_role_name = ""): two least-privilege roles are
# created instead:
#   execution role - used by the ECS agent: pull from ECR, write logs,
#                    read the app secret to inject it as env vars
#   task role      - used by the Django code: read/write objects under
#                    media/ in the uploads bucket (+ read the app secret for
#                    the one-off bootstrap_admin command)
# ---------------------------------------------------------------------------
# The LabRole ARN is built from its name instead of an IAM lookup: the Academy
# lab user cannot always read IAM.
locals {
  create_roles       = var.lab_role_name == ""
  lab_role_arn       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.lab_role_name}"
  execution_role_arn = local.create_roles ? aws_iam_role.execution[0].arn : local.lab_role_arn
  task_role_arn      = local.create_roles ? aws_iam_role.task[0].arn : local.lab_role_arn
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "execution" {
  count              = local.create_roles ? 1 : 0
  name               = "${var.project}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  count      = local.create_roles ? 1 : 0
  role       = aws_iam_role.execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secret" {
  count = local.create_roles ? 1 : 0
  name  = "read-app-secret"
  role  = aws_iam_role.execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.app.arn
    }]
  })
}

resource "aws_iam_role" "task" {
  count              = local.create_roles ? 1 : 0
  name               = "${var.project}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "task_app" {
  count = local.create_roles ? 1 : 0
  name  = "app-runtime"
  role  = aws_iam_role.task[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "MediaObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${local.media_bucket_arn}/media/*"
      },
      {
        # HeadObject on a missing key returns 403 instead of 404 without ListBucket
        Sid       = "MediaList"
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = local.media_bucket_arn
        Condition = { StringLike = { "s3:prefix" = ["media/*"] } }
      },
      {
        Sid      = "BootstrapAdmin"
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.app.arn
      },
    ]
  })
}
