# ---------------------------------------------------------------------------
# PostgreSQL (RDS) - private subnets, encrypted, TLS enforced
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_parameter_group" "postgres" {
  name   = "${var.project}-pg17"
  family = "postgres17"

  parameter {
    name  = "rds.force_ssl" # reject unencrypted client connections
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement" # log queries slower than 1 s
    value = "1000"
  }
}

resource "aws_db_instance" "main" {
  #checkov:skip=CKV_AWS_293:Demo environment must be destroyable; production: deletion protection on
  #checkov:skip=CKV_AWS_157:Multi-AZ is not allowed in AWS Academy and doubles cost; production: Multi-AZ
  #checkov:skip=CKV_AWS_353:Performance Insights not available in AWS Academy
  #checkov:skip=CKV_AWS_118:Enhanced monitoring not available in AWS Academy
  #checkov:skip=CKV_AWS_161:Password auth via Secrets Manager; IAM DB auth would need token refresh in Django
  identifier     = "${var.project}-db"
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp2" # the Academy lab only allows gp2
  storage_encrypted = true

  db_name  = "epiconnect"
  username = "epiconnect"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.postgres.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false # not allowed in the Academy lab; see docs for production

  backup_retention_period         = 1
  copy_tags_to_snapshot           = true
  auto_minor_version_upgrade      = true
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Demo environment: destroyable in one command. Production: deletion
  # protection on and a final snapshot (see docs/ARCHITECTURE.md).
  deletion_protection = false
  skip_final_snapshot = true
  apply_immediately   = true
}

# ---------------------------------------------------------------------------
# Application secrets (one Secrets Manager secret, JSON)
# The ECS agent injects SECRET_KEY and DB_PASSWORD into the container at start;
# they never appear in the task definition, the image or the pipeline.
# ---------------------------------------------------------------------------
resource "random_password" "django_secret_key" {
  length  = 64
  special = false
}

resource "random_password" "admin" {
  length  = 24
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  #checkov:skip=CKV_AWS_149:AWS-managed key; CMK costs $1/month
  #checkov:skip=CKV2_AWS_57:Rotation needs a Lambda and a restart of running tasks; documented as a production step
  name                    = "${var.project}/app"
  description             = "EPIConnect runtime secrets (Django key, DB password, initial admin password)"
  recovery_window_in_days = 0 # demo: allow destroy/re-create with the same name
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SECRET_KEY     = random_password.django_secret_key.result
    DB_PASSWORD    = random_password.db.result
    ADMIN_PASSWORD = random_password.admin.result
  })
}

# ---------------------------------------------------------------------------
# Container registry
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "app" {
  #checkov:skip=CKV_AWS_136:AES256 encryption at rest is enabled; KMS CMK not required for public-source images
  name                 = var.project
  image_tag_mutability = "IMMUTABLE" # a tag (= commit SHA) always means the same image
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 15 most recent images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 15 }
      action       = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------------------
# User uploads (profile pictures, item / listing / chat photos)
# Private bucket; only CloudFront (Origin Access Control) can read it and only
# the application can write to it.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "media" {
  #checkov:skip=CKV_AWS_18:Server access logging not needed for a demo; CloudFront is the only reader
  #checkov:skip=CKV2_AWS_62:No event-driven processing of uploads
  #checkov:skip=CKV_AWS_144:Single-region demo; versioning protects against deletion
  #checkov:skip=CKV_AWS_145:SSE-S3 with bucket key is enabled; KMS adds per-request cost
  bucket        = "${var.project}-media-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration {
    status = "Enabled" # accidental overwrite/delete can be undone
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_s3_bucket_policy" "media" {
  bucket     = aws_s3_bucket.media.id
  depends_on = [aws_s3_bucket_public_access_block.media]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontReadViaOAC"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.media.arn}/media/*"
        Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.main.arn } }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.media.arn, "${aws_s3_bucket.media.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })
}
