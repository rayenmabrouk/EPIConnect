# ---------------------------------------------------------------------------
# Request path:  browser --HTTPS--> CloudFront --HTTP--> ALB --> Fargate task
#                                   CloudFront --OAC---> S3 (/media/*)
#
# CloudFront provides HTTPS on its default *.cloudfront.net certificate (no
# domain needed), caches /static/ and /media/, and serves uploads straight
# from S3. The ALB is only reachable from CloudFront: its security group
# admits the CloudFront origin-facing prefix list, and its listener forwards
# only requests carrying a secret header that CloudFront adds.
# ---------------------------------------------------------------------------
resource "random_password" "origin_verify" {
  length  = 32
  special = false
}

resource "aws_lb" "main" {
  #checkov:skip=CKV_AWS_150:Demo environment must be destroyable in one command
  #checkov:skip=CKV_AWS_91:ALB access logs are replaced by per-request JSON access logs from the application in CloudWatch
  #checkov:skip=CKV2_AWS_28:WAF adds ~$6+/month; the ALB only accepts CloudFront traffic carrying the origin secret. Production: WAF on CloudFront
  #checkov:skip=CKV2_AWS_20:TLS terminates at CloudFront (viewer redirect-to-https); the ALB is not reachable directly
  name                       = "${var.project}-alb"
  load_balancer_type         = "application"
  internal                   = false
  subnets                    = aws_subnet.public[*].id
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
  idle_timeout               = 60
  enable_deletion_protection = false
}

resource "aws_lb_target_group" "app" {
  #checkov:skip=CKV_AWS_378:ALB to task traffic stays inside the VPC between two security groups
  name                 = "${var.project}-app"
  port                 = 8000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 20

  health_check {
    path                = "/healthz/"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  #checkov:skip=CKV_AWS_2:Origin listener behind CloudFront; HTTPS on the ALB needs an ACM cert for a custom domain (none in this project)
  #checkov:skip=CKV_AWS_103:No TLS on this internal origin hop; see CKV_AWS_2
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Anything that did not come through our CloudFront distribution
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "from_cloudfront" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 1

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [random_password.origin_verify.result]
    }
  }
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# --- CloudFront -------------------------------------------------------------
# AWS-managed policies, referenced by their fixed public IDs. (Looking them up
# with data sources needs cloudfront:List*Policies, which AWS Academy denies.)
locals {
  cf_policy = {
    # Managed-CachingDisabled
    caching_disabled = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    # Managed-CachingOptimized
    caching_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    # Managed-AllViewerAndCloudFrontHeaders-2022-06
    all_viewer_and_cf = "33f36d7e-f396-46d9-90e0-52428a34d9dc"
    # Managed-SecurityHeadersPolicy
    security_headers = "67f7725c-6f97-4210-82d7-5512b31e9d03"
  }
}

resource "aws_cloudfront_origin_access_control" "media" {
  name                              = "${var.project}-media"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  #checkov:skip=CKV_AWS_174:Default *.cloudfront.net certificate; a minimum TLS version can only be set with a custom certificate
  #checkov:skip=CKV2_AWS_42:No custom domain in this project; production would use Route 53 + ACM
  #checkov:skip=CKV_AWS_68:WAF is a paid add-on; listed as the first production improvement
  #checkov:skip=CKV2_AWS_47:See CKV_AWS_68 (no WAF)
  #checkov:skip=CKV_AWS_86:Access logs to S3 not needed for a demo; app-side JSON access logs exist
  #checkov:skip=CKV_AWS_374:Campus application, no geographic restriction required
  #checkov:skip=CKV_AWS_310:Single origin region by design; failover is out of scope for the demo
  #checkov:skip=CKV_AWS_305:Dynamic application; "/" is served by Django, no root object
  #checkov:skip=CKV2_AWS_32:Managed security-headers policy is attached to /media/* (Checkov cannot resolve the ID local); Django sets them on app responses
  enabled         = true
  comment         = "${var.project} - app + media"
  is_ipv6_enabled = true
  http_version    = "http2and3"
  price_class     = "PriceClass_100" # North America + Europe edges: cheapest

  origin {
    origin_id   = "alb"
    domain_name = aws_lb.main.dns_name
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 30
    }
    custom_header {
      name  = "X-Origin-Verify"
      value = random_password.origin_verify.result
    }
  }

  origin {
    origin_id                = "media"
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.media.id
  }

  default_cache_behavior {
    target_origin_id         = "alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = local.cf_policy.caching_disabled
    origin_request_policy_id = local.cf_policy.all_viewer_and_cf
    compress                 = true
  }

  # Static files: cache key is the path only; the origin still receives Host
  # and CloudFront-Forwarded-Proto, which Django needs to answer the request.
  ordered_cache_behavior {
    path_pattern             = "/static/*"
    target_origin_id         = "alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = local.cf_policy.caching_optimized
    origin_request_policy_id = local.cf_policy.all_viewer_and_cf
    compress                 = true
  }

  ordered_cache_behavior {
    path_pattern               = "/media/*"
    target_origin_id           = "media"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = local.cf_policy.caching_optimized
    response_headers_policy_id = local.cf_policy.security_headers
    compress                   = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
